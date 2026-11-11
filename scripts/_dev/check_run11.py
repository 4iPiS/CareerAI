import sys

sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import ModelRun

db = SessionLocal()
r = db.get(ModelRun, 11)
print('RUN11:', r.status.value if r else None, 'epochs:', r.current_epoch if r else None)
db.close()
