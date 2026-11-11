from app.database import SessionLocal
from app.models import Question, Feature, QuestionGroup, SurveySession

db = SessionLocal()

# Screening вопросы
screening = db.query(Question).join(QuestionGroup).filter(QuestionGroup.code.value=='screening').order_by(Question.sort_order).all()
print('=== Screening ===')
for q in screening:
    fc = q.feature.code if q.feature else 'NONE'
    print('  %s -> %s' % (fc, q.text[:50]))

print()

# Detailed вопросы (первые 10 цепочек)
detailed = db.query(Question).join(QuestionGroup).filter(QuestionGroup.code.value=='detailed').order_by(Question.sort_order).all()
print('=== Detailed (первые 10) ===')
for q in detailed[:10]:
    fc = q.feature.code if q.feature else 'NONE'
    print('  [%s] %s -> %s' % (q.feature_id, fc, q.text[:50]))

print()

# Personal вопросы
personal = db.query(Question).join(QuestionGroup).filter(QuestionGroup.code.value=='personal').order_by(Question.sort_order).all()
print('=== Personal ===')
for q in personal:
    fc = q.feature.code if q.feature else 'NONE'
    print('  %s -> %s' % (fc, q.text[:50]))

print()

# Пример профиля
s = db.query(SurveySession).filter(SurveySession.status=='completed').first()
profile = s.profile or {}
print('=== Profile (значения > 1) ===')
for k, v in sorted(profile.items(), key=lambda x: -x[1] if isinstance(x[1], (int,float)) else 0):
    if isinstance(v, (int,float)) and v > 1:
        print('  %s: %s' % (k, v))

print()

# Key skills направления
dirs = db.query(Direction).filter(Direction.is_active).limit(3).all()
from app.models import Direction
for d in dirs:
    feats = [f.code for f in d.features]
    print('Direction %s: key_skills=%s' % (d.name, feats))

db.close()
