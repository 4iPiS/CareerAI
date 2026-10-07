"""Админ-API: загрузка, список и удаление медиафайлов."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import get_current_admin
from app.config import get_settings
from app.models import AdminUser
from app.services.media import save_upload

router = APIRouter(tags=['admin-media'])

VALID_KINDS = ('image', 'video', 'audio')


@router.post('/media/upload/{kind}')
async def upload_media(
    kind: str,
    file: UploadFile,
    _: AdminUser = Depends(get_current_admin),
):
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f'Недопустимый тип: {kind}')
    path = save_upload(kind, file)
    return {'ok': True, 'path': path, 'url': f'/media/{path}'}


@router.get('/media')
def list_media(_: AdminUser = Depends(get_current_admin)):
    """Список файлов в хранилище (для выбора кнопкой)."""
    settings = get_settings()
    base = Path(settings.media_dir)
    files = []
    for kind in VALID_KINDS:
        kind_dir = base / kind
        if not kind_dir.exists():
            continue
        for f in sorted(kind_dir.iterdir()):
            if not f.is_file():
                continue
            rel = f'{kind}/{f.name}'
            files.append({
                'path': rel,
                'url': f'/media/{rel}',
                'kind': kind,
                'name': f.name,
                'size': f.stat().st_size,
            })
    return {'files': files}


@router.delete('/media/{kind}/{filename}')
def delete_media(
    kind: str,
    filename: str,
    _: AdminUser = Depends(get_current_admin),
):
    """Удаление файла из хранилища (защита от обхода каталогов)."""
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail='Недопустимый тип')
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name:
        raise HTTPException(status_code=400, detail='Недопустимое имя файла')
    settings = get_settings()
    target = Path(settings.media_dir) / kind / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail='Файл не найден')
    target.unlink()
    return {'ok': True, 'path': f'{kind}/{safe_name}'}