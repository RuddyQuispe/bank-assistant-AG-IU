from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    chunks: int = Field(description="Cantidad de chunks en la colección", examples=[384])
