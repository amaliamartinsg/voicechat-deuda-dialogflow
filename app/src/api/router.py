
from datetime import datetime

from src.api.schema import RAGRequest, QueryResponse, SourceInfo
from src.agent.chain import rag_chain

from config.project_config import SETTINGS


collection_name = SETTINGS.qdrant_collection
qdrant_client = SETTINGS.qdrant_client


async def rag_invoke(request: RAGRequest) -> QueryResponse:
    """
    Endpoint para la consulta RAG utilizando LangChain.
    """
    k = request.k_docs if request.k_docs is not None else SETTINGS.k_docs
    threshold = request.threshold if request.threshold is not None else SETTINGS.threshold

    result = await rag_chain.ainvoke({
        "question": request.question,
        "k_docs": k,
        "threshold": threshold
    })

    sources = [
        SourceInfo(source=result["source"].selection, reason=result["source"].reason)
    ] if result.get('source') else []


    return QueryResponse(
        question=result["question"],
        answer=result["answer"],
        sources=sources,
        timestamp=datetime.now()
    )


# Bloque de prueba para ejecución directa
if __name__ == "__main__":
    import asyncio
    from src.api.schema import RAGRequest

    async def test_rag_invoke():
        request = RAGRequest(
            question="¿Cómo me cambio a Energix?",
            k_docs=3,
            threshold=0.5
        )
        response = await rag_invoke(request)
        print(response)
        print("Pregunta:", response.question)
        print("Respuesta:", response.answer)
        print("Sources:", response.sources)
        print("Timestamp:", response.timestamp)

    asyncio.run(test_rag_invoke())
    
    
