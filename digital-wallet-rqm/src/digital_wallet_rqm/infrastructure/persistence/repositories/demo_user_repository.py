from digital_wallet_rqm.application.ports.outbound.user_repository import UserRepository
from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.domain.models import CurrentUser


class DemoUserRepository(UserRepository):
    """Adaptador del puerto UserRepository con un único usuario demo (settings).

    Cuando exista una tabla de usuarios se reemplaza por un repositorio SQL, sin tocar el caso de uso.
    """

    def find_by_nickname(self, nickname: str) -> CurrentUser | None:
        if nickname == settings.DEMO_USER_NICKNAME:
            return CurrentUser(user_id=settings.DEMO_USER_ID, nickname=settings.DEMO_USER_NICKNAME)
        return None
