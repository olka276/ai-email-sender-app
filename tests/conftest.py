from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dependencies import get_llm_service
from main import app


@pytest.fixture
def fake_service():
    service = AsyncMock()
    service.forward_email.return_value = "Mail forwarded to: it"
    return service


@pytest.fixture
def client(fake_service):
    app.dependency_overrides[get_llm_service] = lambda: fake_service
    yield TestClient(app)
    app.dependency_overrides.clear()
