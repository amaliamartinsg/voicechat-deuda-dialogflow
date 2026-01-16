from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.services.llms import llm_langchain
from src.services.vector_store import qdrant_langchain

from src.agent.prompts import rag_prompt

answer_generation_chain = rag_prompt | llm_langchain | StrOutputParser()

def format_docs(input_dict) -> str:
    """Formatea los documentos recuperados en una sola cadena de contexto."""
    docs = input_dict["source_context"]
    if isinstance(docs, str):
        return docs
    if isinstance(docs, list):
        if all(isinstance(d, dict) and "section" in d for d in docs):
            return "\n\n".join(d["section"] for d in docs if d.get("section"))
        if all(hasattr(d, "page_content") for d in docs):
            return "\n\n".join(d.page_content for d in docs)
        return "\n\n".join(str(d) for d in docs)
    return "No se pudo procesar el formato de los documentos."

def get_sources_info(question: str, k: int = None, threshold: float = None) -> list:
    results = qdrant_langchain.similarity_search_with_score(question, k=k)
    results = sorted(results, key=lambda x: x[1], reverse=True)
    if threshold is not None:
        filtered_results = [(doc, score) for doc, score in results if score >= threshold]
    else:
        filtered_results = results
    docs_filtered = []
    for doc, score in filtered_results:
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        docs_filtered.append({
            "score": score,
            "chunk_id": metadata.get("_id"),
            "page": None,
            "section": doc.page_content[:300] if hasattr(doc, "page_content") else "",
            "source": metadata.get("source"),
            "filename": metadata.get("filename"),
            "collection_name": metadata.get("_collection_name"),
        })
    return docs_filtered

# Cadena principal para una única intención
rag_chain = (
    RunnablePassthrough.assign(
        source_context=RunnableLambda(
            lambda input_dict: get_sources_info(
                input_dict['question'],
                k=input_dict.get('k_docs'),
                threshold=input_dict.get('threshold')
            )
        )
    )
    .assign(context=RunnableLambda(format_docs))
    .assign(answer=RunnableLambda(
        lambda input_dict: answer_generation_chain.invoke(input_dict)
    ))
).with_types(input_type=dict, output_type=dict)