"""HTTP API уведомлений."""

import os
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from .storage import MessageConflict, NotificationStorage


class NotificationRequest(BaseModel):
    message_id: UUID
    text: str = Field(min_length=1, max_length=10_000)
    recipient: str | None = Field(default=None, min_length=1, max_length=300)


class NotificationResponse(BaseModel):
    status: Literal["created", "duplicate"]
    filename: str


def create_app(data_dir: Path) -> FastAPI:
    service = FastAPI(title="Iris Notification Service")
    storage = NotificationStorage(data_dir)

    @service.post(
        "/notifications",
        response_model=NotificationResponse,
        status_code=201,
        responses={
            200: {"model": NotificationResponse, "description": "Повтор того же запроса"},
            409: {"description": "У идентификатора уже есть другое содержимое"},
        },
    )
    def post_notification(request: NotificationRequest, response: Response):
        try:
            created, filename = storage.save(request.message_id, request.text, request.recipient)
        except MessageConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response.status_code = 201 if created else 200
        return NotificationResponse(
            status="created" if created else "duplicate",
            filename=filename,
        )

    return service


default_dir = Path(__file__).resolve().parents[2] / "var"
app = create_app(Path(os.getenv("NOTIFICATIONS_DATA_DIR") or default_dir))
