import pytest


@pytest.fixture
def anyio_backend() -> str:
    # Async tests run with @pytest.mark.anyio (plugin shipped with anyio); only asyncio is used
    return "asyncio"
