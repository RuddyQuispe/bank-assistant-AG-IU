from pydantic import BaseModel, Field

from digital_wallet_rqm.models.types import Route


class RouteDecision(BaseModel):
    route: Route = Field(description="Ruta elegida para el mensaje")
    reason: str = Field(description="Justificación breve de la ruta")
