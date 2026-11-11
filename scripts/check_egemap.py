import sys
sys.path.insert(0, '/app')
from sqlalchemy import select
from app.database import SessionLocal
from app.models import SurveySession, Direction
db = SessionLocal()
all_directions = db.scalars(select(Direction).where(Direction.is_active)).all()
skill_map = {d.name: [f.code for f in d.features] for d in all_directions}
EGE_FOR_SKILL = {
    'experimental_physics': ['ege_physics'],
    'chemical_analysis': ['ege_chemistry'],
    'math_modeling': ['ege_math'],
    'computer_systems': ['ege_informatics'],
    'business_analytics': ['ege_social'],
}
for dname, skills in skill_map.items():
    extra_ege = set()
    for skill in skills:
        ege_subjects = EGE_FOR_SKILL.get(skill, [])
        extra_ege.update(ege_subjects)
    if extra_ege:
        skill_map[dname] = skills + list(extra_ege)
for name in ['Физическая химия', 'Физика', '1С технологии для бизнеса']:
    if name in skill_map:
        print(name + ': ' + str(skill_map[name]))
db.close()
