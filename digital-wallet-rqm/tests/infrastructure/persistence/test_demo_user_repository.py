from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.persistence.repositories import DemoUserRepository


def test_only_the_demo_user_exists() -> None:
    users = DemoUserRepository()

    assert users.find_by_nickname("ruddy") == CurrentUser(user_id="1", nickname="ruddy")
    assert users.find_by_nickname("juan") is None
