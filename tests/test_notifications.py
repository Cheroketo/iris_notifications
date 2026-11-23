from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from notification_service.app.main import create_app


MESSAGE_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"
PAYLOAD = {"message_id": MESSAGE_ID, "text": "Предсказание готово", "recipient": "Студент"}
FILENAME = f"{MESSAGE_ID}.txt"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as test_client:
        yield test_client


def test_first_request_creates_file(client, tmp_path):
    response = client.post("/notifications", json=PAYLOAD)

    assert response.status_code == 201
    assert response.json() == {"status": "created", "filename": FILENAME}
    assert (tmp_path / "processed_ids.sqlite3").is_file()
    files = list((tmp_path / "messages").iterdir())
    assert [path.name for path in files] == [FILENAME]
    text = files[0].read_text(encoding="utf-8")
    assert f"Идентификатор: {MESSAGE_ID}" in text
    assert "Время создания: " in text
    assert "Получатель: Студент" in text
    assert "Сообщение: Предсказание готово" in text


def test_duplicate_returns_original_file_after_restart(client, tmp_path):
    assert client.post("/notifications", json=PAYLOAD).status_code == 201
    path = tmp_path / "messages" / FILENAME
    original = path.read_bytes()
    original_mtime = path.stat().st_mtime_ns

    with TestClient(create_app(tmp_path)) as restarted:
        response = restarted.post("/notifications", json=PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"status": "duplicate", "filename": FILENAME}
    assert list(path.parent.iterdir()) == [path]
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == original_mtime


@pytest.mark.parametrize("change", [{"text": "Другой текст"}, {"recipient": "Другой получатель"}])
def test_conflict_keeps_original_file(client, tmp_path, change):
    assert client.post("/notifications", json=PAYLOAD).status_code == 201
    path = tmp_path / "messages" / FILENAME
    original = path.read_bytes()

    response = client.post("/notifications", json={**PAYLOAD, **change})

    assert response.status_code == 409
    assert "message_id" in response.json()["detail"]
    assert list(path.parent.iterdir()) == [path]
    assert path.read_bytes() == original


def test_invalid_id_is_rejected(client, tmp_path):
    response = client.post("/notifications", json={**PAYLOAD, "message_id": "../outside"})
    assert response.status_code == 422
    assert not (tmp_path / "messages").exists()


def test_concurrent_duplicates_create_one_file(client, tmp_path):
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(
            lambda _: client.post("/notifications", json=PAYLOAD).status_code, range(4)
        ))

    assert sorted(statuses) == [200, 200, 200, 201]
    assert [p.name for p in (tmp_path / "messages").iterdir()] == [FILENAME]
