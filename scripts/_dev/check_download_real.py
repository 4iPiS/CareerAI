"""Проверка: download_real_dataset актуализирует responses.csv из БД с BOM."""
import sys

sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.api.admin_train import download_real_dataset

db = SessionLocal()
try:
    # Вызываем функцию endpoint напрямую (Depends разрешатся вручную)
    resp = download_real_dataset(db=db, _=None)
    print('RESPONSE:', type(resp).__name__, resp.status_code if hasattr(resp, 'status_code') else '')
    path = resp.path if hasattr(resp, 'path') else None
    print('FILE:', path)
    if path:
        raw = open(path, 'rb').read()
        print('BOM present:', raw[:3] == b'\xef\xbb\xbf')
        print('rows (bytes):', len(raw))
        head = raw[:200].decode('utf-8-sig', errors='replace')
        print('HEAD:', head[:150])
finally:
    db.close()
