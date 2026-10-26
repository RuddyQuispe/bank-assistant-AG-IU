from datetime import UTC, datetime, timedelta

import jwt

from digital_wallet_rqm.application.ports.outbound.token_service import TokenService
from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.domain.errors import InvalidTokenError
from digital_wallet_rqm.domain.models import CurrentUser


class JwtTokenService(TokenService):
    """Adaptador del puerto TokenService con JWT (pyjwt): todo el manejo de JWT vive aquí"""

    def __init__(
        self,
        secret: str,
        issuer: str = settings.JWT_ISSUER,
        expire_minutes: int = settings.JWT_EXPIRE_MINUTES,
    ) -> None:
        if not secret:
            raise ValueError("JWT_SECRET es obligatorio para firmar los tokens")
        self.secret = secret
        self.issuer = issuer
        self.expire_minutes = expire_minutes

    def issue(self, user: CurrentUser) -> str:
        now = datetime.now(UTC)
        claims = {
            "iss": self.issuer,  # quién emitió el token: esta API
            "sub": user.user_id,  # de quién es el token: el id del usuario
            "nickname": user.nickname,
            "iat": now,
            "exp": now + timedelta(minutes=self.expire_minutes),
        }
        return jwt.encode(claims, self.secret, algorithm=settings.JWT_ALGORITHM)

    def read(self, token: str) -> CurrentUser:
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=[settings.JWT_ALGORITHM],  # se fija el algoritmo: no se acepta el que diga el token
                issuer=self.issuer,
                options={"require": ["exp", "iss", "sub"]},
            )
        except jwt.InvalidTokenError as error:
            raise InvalidTokenError(str(error)) from error

        nickname = claims.get("nickname")
        if not isinstance(nickname, str):
            raise InvalidTokenError("el token no tiene nickname")
        return CurrentUser(user_id=claims["sub"], nickname=nickname)
