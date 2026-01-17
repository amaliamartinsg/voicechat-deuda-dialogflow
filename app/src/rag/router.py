
from datetime import datetime

from src.rag.schema import RAGRequest, QueryResponse, SourceInfo
from src.agent.chain import rag_chain

from config.project_config import SETTINGS


async def rag_invoke(request: RAGRequest) -> QueryResponse:
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



if __name__ == "__main__":
    import asyncio

    test_request = RAGRequest(
        question="¿Cuál es el importe de mi última factura?",
        k_docs=3,
        threshold=0.8
    )

    response = asyncio.run(rag_invoke(test_request))
    print(response)