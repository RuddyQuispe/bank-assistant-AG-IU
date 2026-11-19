from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    nickname: str = Field(min_length=1, examples=["ruddy"])


class TokenResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = "bearer"
