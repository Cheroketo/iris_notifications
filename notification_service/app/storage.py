"""Постоянное хранилище идентификаторов и файлов уведомлений."""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID


class MessageConflict(Exception):
    """Идентификатор уже сохранён с другим содержимым."""


class NotificationStorage:
    def __init__(self, root: Path):
        self.root = root

    def save(self, message_id: UUID, text: str, recipient: str | None) -> tuple[bool, str]:
        self.root.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.root / "processed_ids.sqlite3")) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY, text TEXT NOT NULL,
                        recipient TEXT, created_at TEXT NOT NULL
                    )
                """)
                key = str(message_id)
                existing = db.execute(
                    "SELECT text, recipient, created_at FROM messages WHERE message_id = ?",
                    (key,),
                ).fetchone()
                if existing is None:
                    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    db.execute(
                        "INSERT INTO messages VALUES (?, ?, ?, ?)",
                        (key, text, recipient, created_at),
                    )
                else:
                    saved_text, saved_recipient, created_at = existing
                    if (saved_text, saved_recipient) != (text, recipient):
                        raise MessageConflict("Этот message_id уже связан с другим содержимым.")

        # Состояние фиксируется перед публикацией файла. Если запись файла прервётся,
        # идентичный повтор восстановит тот же файл с исходным временем создания.
        path = self.root / "messages" / f"{message_id}.txt"
        if not path.is_file():
            path.parent.mkdir(exist_ok=True)
            lines = [f"Идентификатор: {message_id}", f"Время создания: {created_at}"]
            if recipient is not None:
                lines.append(f"Получатель: {recipient}")
            lines.append(f"Сообщение: {text}")
            self._publish_file(path, "\n".join(lines) + "\n")
        return existing is None, path.name

    @staticmethod
    def _publish_file(path: Path, content: str) -> None:
        temp_path = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, delete=False
            ) as temp:
                temp_path = Path(temp.name)
                temp.write(content)
            try:
                os.link(temp_path, path)
            except FileExistsError:
                # Параллельный повтор уже опубликовал файл с теми же данными.
                pass
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
