"""Загрузка и хранение медиафайлов вуза (логотипы, картинки, видео, аудио)."""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings

ALLOWED_EXTENSIONS = {
    'image': {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'},
    'video': {'.mp4', '.webm'},
    'audio': {'.mp3', '.wav', '.ogg'},
}
MAX_SIZES = {
    'image': 10 * 1024 * 1024,
    'video': 200 * 1024 * 1024,
    'audio': 50 * 1024 * 1024,
}


def save_upload(kind: str, file: UploadFile) -> str:
    """Сохраняет файл в media/{kind}/ и возвращает относительный путь."""
    if kind not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Недопустимый тип: {kind}')

    original = file.filename or ''
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS[kind]:
        raise HTTPException(
            status_code=400,
            detail=f'Недопустимое расширение файла: {ext or "нет"}',
        )

    settings = get_settings()
    dest_dir = Path(settings.media_dir) / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f'{uuid.uuid4().hex}{ext}'
    dest = dest_dir / name

    size = 0
    with dest.open('wb') as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_SIZES[kind]:
                file.file.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail='Файл слишком большой')
            out.write(chunk)

    return f'{kind}/{name}'