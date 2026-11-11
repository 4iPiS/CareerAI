from __future__ import annotations

"""Админ-API: обучающие выборки и запуск обучения модели."""
import csv as _csv
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.models import AdminUser, ModelRun, ModelRunStatus
from app.services.trainer import (
    generate_dataset_csv,
    generate_dataset_csv_progressive,
    load_real_responses,
    run_training,
)

router = APIRouter(tags=['admin-train'])


class TrainRequest(BaseModel):
    dataset: str = Field('synthetic', description="'synthetic' — только синтетика, 'all' — синтетика+реальные, 'real_only' — только реальные")
    model_id: int | None = Field(None, description='ID модели для fine-tuning')


def _run_out(r: ModelRun) -> dict:
    snapshot = r.config_snapshot or {}
    # Безопасная десериализация метрик (на случай если пришли как строка)
    metrics = r.metrics
    if isinstance(metrics, str):
        try:
            import json as _json
            metrics = _json.loads(metrics)
        except Exception:  # noqa: BLE001
            metrics = {}
    if metrics is None:
        metrics = {}
    dataset_raw = snapshot.get('dataset')
    dataset_info = snapshot.get('dataset_info')
    dataset_type = snapshot.get('dataset_type')
    # Fine-tuning: базовая модель сохраняется в config_snapshot
    ft_run = snapshot.get('fine_tuned_from_run') or snapshot.get('fine_tuned_from_run_id')
    is_finetune = bool(ft_run) or bool(snapshot.get('fine_tuned_from'))

    # Формируем читаемую строку для данных
    dataset_label = '—'
    if is_finetune:
        dataset_label = (
            f'Fine-tuning от модели #{ft_run}' if ft_run else 'Fine-tuning'
        )
    elif isinstance(dataset_info, dict) and dataset_info:
        parts = []
        for k, v in dataset_info.items():
            label = {'synthetic': 'синтетика', 'real': 'реальные'}.get(k, k)
            parts.append(f'{label}: {v}')
        dataset_label = ', '.join(parts)
    elif isinstance(dataset_raw, str):
        dataset_label = dataset_raw
    elif dataset_type:
        labels = {'synthetic': 'только синтетика', 'all': 'синтетика + реал.', 'real_only': 'только реальные'}
        dataset_label = labels.get(dataset_type, dataset_type)

    return {
        'id': r.id,
        'status': r.status.value,
        'metrics': metrics,
        'artifact_dir': r.artifact_dir,
        'error_message': r.error_message,
        'triggered_by': r.triggered_by,
        'dataset': dataset_label,
        'model_id': ft_run,
        'fine_tuned_from': snapshot.get('fine_tuned_from'),
        'current_epoch': r.current_epoch,
        'total_epochs': r.total_epochs,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'finished_at': r.finished_at.isoformat() if r.finished_at else None,
    }


@router.get('/train/dataset')
def dataset_status(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    settings = get_settings()
    synthetic_path = Path(settings.data_dir) / 'training_synthetic.csv'
    real_path = Path(settings.data_dir) / 'real' / 'responses.csv'

    import json as _json

    def _read_meta(path: Path) -> dict:
        if path.exists():
            try:
                return _json.loads(path.read_text())
            except Exception:
                pass
        return {}

    syn_meta = _read_meta(synthetic_path.with_suffix('.meta.json'))
    real_meta = _read_meta(real_path.with_suffix('.meta.json'))

    def _get_rows(csv_path: Path, meta: dict, key: str) -> int | None:
        rows = meta.get(key)
        if rows is not None:
            return rows
        # Лениво считаем
        if csv_path.exists():
            try:
                with open(csv_path, encoding='utf-8-sig') as f:
                    count = max(0, len(f.readlines()) - 1)
                meta_path = csv_path.with_suffix('.meta.json')
                meta[key] = count
                meta['updated_at'] = datetime.now().isoformat()
                meta_path.write_text(_json.dumps(meta, ensure_ascii=False))
                return count
            except Exception:
                pass
        return None

    synthetic_rows = _get_rows(synthetic_path, syn_meta, 'synthetic_rows')
    real_rows = _get_rows(real_path, real_meta, 'real_rows')

    result = {
        'synthetic': {
            'exists': synthetic_path.exists(),
            'path': str(synthetic_path),
            'rows': synthetic_rows,
        },
        'real': {
            'exists': real_path.exists(),
            'path': str(real_path),
            'rows': real_rows,
        },
        'active_features': 0,
        'active_directions': 0,
    }

    from app.models import Direction, Feature

    result['active_features'] = db.scalar(
        select(func.count()).select_from(Feature).where(Feature.is_active),
    ) or 0
    result['active_directions'] = db.scalar(
        select(func.count()).select_from(Direction).where(Direction.is_active),
    ) or 0
    return result


@router.post('/train/dataset/generate')
def generate_dataset(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    settings = get_settings()
    output = Path(settings.data_dir) / 'training_synthetic.csv'
    progress_file = Path(settings.data_dir) / 'progress.json'
    try:
        info = generate_dataset_csv_progressive(db, output, progress_file)
    except Exception as exc:  # noqa: BLE001
        import logging, traceback as _tb
        logging.getLogger(__name__).error(f'generate_dataset FAILED:\n{_tb.format_exc()}')
        raise HTTPException(status_code=400, detail=f'Не удалось сгенерировать: {exc}')
    return {'ok': True, 'rows': info['rows'], 'features': info['features'], 'directions': info['directions']}


@router.get('/train/dataset/progress')
def dataset_progress(
    _: AdminUser = Depends(get_current_admin),
):
    settings = get_settings()
    progress_file = Path(settings.data_dir) / 'progress.json'
    if progress_file.exists():
        import json as _json
        try:
            data = _json.loads(progress_file.read_text())
            # Добавляем progress, если его нет (старый формат step/total)
            if 'progress' not in data:
                step = data.get('step', 0)
                total = data.get('total', 10) or 10
                data['progress'] = min(100, round((step / total) * 100))
            data.setdefault('step', data['progress'])
            data.setdefault('total', 100)
            data.setdefault('rows', 0)
            data.setdefault('done', data['progress'] >= 100)
            return data
        except Exception:
            pass
    return {'step': 0, 'total': 100, 'rows': 0, 'progress': 0, 'done': False}


@router.get('/train/dataset/download')
def download_dataset(
    _: AdminUser = Depends(get_current_admin),
):
    """Скачивает сгенерированную синтетическую выборку как CSV."""
    from fastapi.responses import FileResponse

    settings = get_settings()
    path = Path(settings.data_dir) / 'training_synthetic.csv'
    if not path.exists():
        raise HTTPException(status_code=404, detail='Выборка ещё не сгенерирована')
    return FileResponse(
        path,
        media_type='text/csv; charset=utf-8',
        filename='training_synthetic.csv',
    )


@router.get('/train/dataset/download-real')
def download_real_dataset(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Скачивает реальные ответы: файл АКТУАЛИЗИРУЕТСЯ из БД перед отдачей,
    поэтому свежие прохождения всегда попадают в CSV. Если файл ни разу
    не загружался вручную — создаётся из ответов в БД."""
    from fastapi.responses import FileResponse

    from app.services.responses import export_responses_csv

    settings = get_settings()
    path = Path(settings.data_dir) / 'real' / 'responses.csv'

    fresh = export_responses_csv(db)
    if not fresh:
        raise HTTPException(status_code=404, detail='В БД нет завершённых сессий')
    if path.exists():
        # Сохраняем ручные дополнения: мержим — новые строки из БД
        # добавляются в конец существующего файла без дублей по session id.
        existing = path.read_text(encoding='utf-8-sig', errors='replace')
        fresh_lines = [ln for ln in fresh.splitlines() if ln]
        header, *fresh_rows = fresh_lines
        id_col = header.split(',')[0]
        existing_lines = [ln for ln in existing.splitlines() if ln]
        existing_header, *existing_rows = existing_lines
        known = {ln.split(',')[0] for ln in existing_rows}
        merged = existing_lines + [
            ln for ln in fresh_rows if ln.split(',')[0] not in known
        ]
        path.write_text('\n'.join([existing_header] + merged) + '\n', encoding='utf-8-sig')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fresh, encoding='utf-8-sig')

    return FileResponse(
        path,
        media_type='text/csv; charset=utf-8',
        filename='responses.csv',
    )


@router.post('/train/dataset/upload')
async def upload_real_csv(
    file: UploadFile = File(...),
    _: AdminUser = Depends(get_current_admin),
):
    """Загружает экспортированный responses.csv для дообучения."""
    settings = get_settings()
    dest_dir = Path(settings.data_dir) / 'real'
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / 'responses.csv'

    filename = (file.filename or '').lower()
    if not filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail='Файл должен быть CSV')

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='Файл больше 50 МБ')
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail='CSV должен быть в кодировке UTF-8')

    reader = _csv.DictReader(text.splitlines())
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail='Файл пуст или не содержит строк')

    dest.write_bytes(content)
    
    # Сохраняем количество строк в meta.json для отображения в админке
    import json as _json
    from datetime import datetime
    
    meta_path = dest.with_suffix('.meta.json')
    meta = {}
    if meta_path.exists():
        try:
            meta = _json.loads(meta_path.read_text())
        except Exception:
            pass
    meta['real_rows'] = len(rows)
    meta['updated_at'] = datetime.now().isoformat()
    meta_path.write_text(_json.dumps(meta, ensure_ascii=False))
    
    return {
        'ok': True,
        'rows': len(rows),
        'path': str(dest),
        'columns': list(reader.fieldnames or []),
    }


@router.post('/train')
def start_training(
    background_tasks: BackgroundTasks,
    req: TrainRequest = Body(default=TrainRequest()),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    if req.dataset not in ('synthetic', 'all', 'real_only'):
        raise HTTPException(status_code=400, detail='dataset: synthetic|all|real_only')

    active = db.scalar(
        select(ModelRun).where(ModelRun.status == ModelRunStatus.running),
    )
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail=f'Обучение уже идёт (запуск #{active.id})',
        )

    settings = get_settings()
    real_path = None
    if req.dataset in ('all', 'real_only'):
        real_path = str(Path(settings.data_dir) / 'real' / 'responses.csv')
    run = ModelRun(
        status=ModelRunStatus.pending,
        triggered_by=admin.id,
        config_snapshot={
            'dataset_type': req.dataset,
            'fine_tuned_from_run': req.model_id,
        },
        total_epochs=80,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(
        run_training,
        run.id,
        admin.id,
        dataset=req.dataset,
        real_data_path=real_path,
        model_id=req.model_id,
    )
    return {'run_id': run.id, 'status': ModelRunStatus.pending.value, 'dataset': req.dataset}


@router.get('/train/models')
def list_models(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Список завершённых моделей для fine-tuning."""
    runs = db.scalars(
        select(ModelRun)
        .where(
            ModelRun.status == ModelRunStatus.completed,
            ModelRun.artifact_dir != '',
        )
        .order_by(ModelRun.id.desc())
        .limit(10),
    ).all()
    return {
        'models': [
            {
                'id': r.id,
                'metrics': r.metrics or {},
                'dataset': r.config_snapshot or {},
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    }


@router.get('/train/status')
def training_status(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    runs = db.scalars(
        select(ModelRun).order_by(ModelRun.id.desc()).limit(10),
    ).all()
    return {'runs': [_run_out(r) for r in runs]}


@router.post('/train/{run_id}/cancel')
def cancel_training(
    run_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Останавливает запущенное обучение."""
    run = db.get(ModelRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='Запуск не найден')
    if run.status not in (ModelRunStatus.running, ModelRunStatus.pending):
        raise HTTPException(
            status_code=400,
            detail=f'Нельзя остановить: статус {run.status.value}',
        )
    run.status = ModelRunStatus.failed
    run.error_message = 'Остановлено пользователем'
    db.commit()
    return {'ok': True, 'message': 'Обучение остановлено'}