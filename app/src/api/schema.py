from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SourceInfo(BaseModel):
    source: str
    reason: str

class QueryResponse(BaseModel):
    """Modelo para la respuesta del agente"""
    answer: str = Field(..., description="Respuesta generada por el agente")
    sources: List[SourceInfo] = Field(..., description="Fuentes consultadas")
    timestamp: datetime = Field(default_factory=datetime.now)
    question: str = Field(..., description="Pregunta original")

class RAGRequest(BaseModel):
    """Modelo para la petición de consulta"""
    question: str = Field(..., description="Pregunta para el agente RAG")
    k_docs: Optional[int] = Field(default=None, description="Número de documentos a recuperar", ge=1)
    threshold: Optional[float] = Field(default=None, description="Umbral de puntuación para filtrar documentos", ge=0.0, le=1.0)