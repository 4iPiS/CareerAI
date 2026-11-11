from app.database import SessionLocal
from app.models import SurveySession, Direction
db = SessionLocal()
session = db.query(SurveySession).order_by(SurveySession.id.desc()).first()
profile = session.profile
for d in db.query(Direction).all():
    if 'информ' in d.name.lower() or 'систем' in d.name.lower() or '1с' in d.name.lower():
        skills = [f.code for f in d.features]
        scores = []
        for s in skills:
            val = profile.get(s, 0)
            if val is None or val == 0:
                continue
            val = float(val)
            if s.startswith('ege_'):
                val = max(1.0, min(5.0, (val / 100.0) * 5.0))
            scores.append((s, val))
        if scores:
            avg = sum(v for _, v in scores) / len(scores)
            pct = round((avg / 5.0) * 100)
        else:
            pct = 0
        print(str(pct) + '% - ' + d.name)
        for code, val in scores:
            print('  ' + code + ' = ' + str(val))
db.close()
