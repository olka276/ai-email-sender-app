import logging

from exceptions import EmailDeliveryError, LLMUnavailableError
from schemas.send_email_request import MESSAGE_MAX_LENGTH

VALID = {"email": "jan.nowak@example.com", "message": "Nie działa mi komputer"}


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_docs_available(client):
    assert client.get("/api/v1/docs").status_code == 200


def test_send_returns_202_and_runs_in_background(client, fake_service):
    response = client.post("/api/v1/send", json=VALID)

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    fake_service.forward_email.assert_awaited_once_with(
        VALID["email"], VALID["message"]
    )


def test_send_rejects_invalid_email(client, fake_service):
    response = client.post("/api/v1/send", json={**VALID, "email": "not-email"})

    assert response.status_code == 422
    fake_service.forward_email.assert_not_called()


def test_send_rejects_missing_message(client, fake_service):
    response = client.post("/api/v1/send", json={"email": VALID["email"]})

    assert response.status_code == 422
    fake_service.forward_email.assert_not_called()


def test_background_failure_is_logged_and_not_leaked(client, fake_service, caplog):
    fake_service.forward_email.side_effect = RuntimeError("ollama down")

    with caplog.at_level(logging.ERROR):
        response = client.post("/api/v1/send", json=VALID)

    assert response.status_code == 202
    assert "ollama down" not in response.text
    assert "Unexpected error processing message" in caplog.text


def test_domain_errors_are_logged_with_type_and_not_leaked(client, fake_service, caplog):
    fake_service.forward_email.side_effect = LLMUnavailableError("ollama down")

    with caplog.at_level(logging.ERROR):
        response = client.post("/api/v1/send", json=VALID)

    assert response.status_code == 202
    assert "ollama down" not in response.text
    assert "LLMUnavailableError" in caplog.text
    assert VALID["email"] in caplog.text


def test_delivery_error_does_not_break_subsequent_requests(client, fake_service):
    fake_service.forward_email.side_effect = [EmailDeliveryError("smtp down"), "ok"]

    assert client.post("/api/v1/send", json=VALID).status_code == 202
    assert client.post("/api/v1/send", json=VALID).status_code == 202
    assert fake_service.forward_email.await_count == 2


def test_send_accepts_message_at_max_length(client, fake_service):
    message = "a" * MESSAGE_MAX_LENGTH

    response = client.post("/api/v1/send", json={**VALID, "message": message})

    assert response.status_code == 202
    fake_service.forward_email.assert_awaited_once_with(VALID["email"], message)


def test_send_rejects_message_over_max_length(client, fake_service):
    response = client.post(
        "/api/v1/send", json={**VALID, "message": "a" * (MESSAGE_MAX_LENGTH + 1)}
    )

    assert response.status_code == 422
    fake_service.forward_email.assert_not_called()


def test_send_rejects_empty_message(client, fake_service):
    response = client.post("/api/v1/send", json={**VALID, "message": ""})

    assert response.status_code == 422
    fake_service.forward_email.assert_not_called()
