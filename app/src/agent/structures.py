from typing import Literal
from pydantic import BaseModel, Field

# Definimos categorías posibles relacionadas con Bitcoin
possible_categories = ["precio_actual", "informacion_conceptos"]

class SourceModel(BaseModel):
    selection: Literal["precio_actual", "informacion_conceptos"] = Field(
            ...,
            description="Categoriza la pregunta del usuario en una de las siguientes categorías: precio_actual, informacion_conceptos.",
        )
    reason: str = Field(
            ...,
            description="Razones por las que eliges la selección.",
        )
