import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.api.dependencies import get_current_user, get_document_indexer
from digital_wallet_rqm.api.main import app
from digital_wallet_rqm.models.current_user import CurrentUser


class FakeIndexer:
    """Indexador falso: registra qué operación se llamó"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def sync(self) -> int:
        self.calls.append("sync")
        return 10

    def rebuild(self) -> int:
        self.calls.append("rebuild")
        return 20


@pytest.fixture
def fake_indexer():
    indexer = FakeIndexer()
    app.dependency_overrides[get_document_indexer] = lambda: indexer
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="1", nickname="ruddy")
    yield indexer
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_indexer):
    # Sin "with": no se ejecuta el lifespan, así no se abre la base ni Chroma
    return TestClient(app)


def test_index_runs_sync_by_default(client, fake_indexer):
    response = client.post("/admin/index")

    assert response.status_code == 200
    assert response.json() == {"chunks": 10}
    assert fake_indexer.calls == ["sync"]


def test_index_with_rebuild_runs_rebuild(client, fake_indexer):
    response = client.post("/admin/index", params={"rebuild": True})

    assert response.status_code == 200
    assert response.json() == {"chunks": 20}
    assert fake_indexer.calls == ["rebuild"]
