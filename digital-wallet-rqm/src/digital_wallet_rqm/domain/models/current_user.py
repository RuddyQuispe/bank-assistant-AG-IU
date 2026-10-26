from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    """Usuario autenticado, leído del JWT"""

    user_id: str
    nickname: str
