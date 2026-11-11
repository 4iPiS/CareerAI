import sys
sys.path.insert(0, '/app')
from app.database import SessionLocal
from app.models import SurveySession, Direction
from app.services.api_recommender import _calculate_probabilities
db = SessionLocal()
session = db.query(SurveySession).order_by(SurveySession.id.desc()).first()
profile = session.profile
skill_map = {}
for d in db.query(Direction).all():
    skill_map[d.name] = [f.code for f in d.features]
results = _calculate_probabilities(profile, list(skill_map.keys()), skill_map, {})
for r in results[:15]:
    print(str(r['probability']) + '% - ' + r['field'])
db.close()
