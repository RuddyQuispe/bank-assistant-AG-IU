from pydantic import BaseModel, Field


class DemoQrsResponse(BaseModel):
    """QR de prueba: solo sus tokens; los datos del cobro se obtienen al escanearlos"""

    codes: list[str] = Field(examples=[["qr_af9bd6ff81dc2525a2fba110bf390946"]])
