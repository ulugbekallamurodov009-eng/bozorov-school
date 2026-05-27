"""
Boshlang'ich ma'lumotlarni yuklash:
python seed.py
"""
import sys
sys.path.insert(0, '.')

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.school import Teacher, Student, Group
from app.models.finance import Payment, PaymentStatus
from datetime import datetime

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("📦 Ma'lumotlar yuklanmoqda...")

# Admin yaratish
admin = db.query(User).filter(User.login == "admin").first()
if not admin:
    admin = User(
        login="admin",
        password=hash_password("admin123"),
        first_name="Bozorov",
        last_name="Admin",
        phone="+998951464040",
        role=UserRole.admin
    )
    db.add(admin)
    db.flush()
    print("✅ Admin: login=admin | parol=admin123")

# O'qituvchilar
teachers_data = [
    {"login":"akbar.teacher", "pass":"akbar123", "first":"Akbar", "last":"Axmadov", "subject":"Matematika", "pct":30},
    {"login":"sardor.teacher","pass":"sardor123","first":"Sardor","last":"Yusupov", "subject":"Kimyo",       "pct":28},
    {"login":"nargiza.teacher","pass":"nargiza123","first":"Nargiza","last":"Xolova","subject":"Ingliz tili","pct":32},
    {"login":"botir.teacher",  "pass":"botir123",  "first":"Botir", "last":"Karimov","subject":"Fizika",    "pct":25},
]

teacher_objs = []
for td in teachers_data:
    u = db.query(User).filter(User.login == td["login"]).first()
    if not u:
        u = User(login=td["login"], password=hash_password(td["pass"]),
                 first_name=td["first"], last_name=td["last"],
                 role=UserRole.teacher)
        db.add(u)
        db.flush()
        t = Teacher(user_id=u.id, subject=td["subject"], salary_pct=td["pct"])
        db.add(t)
        db.flush()
        teacher_objs.append(t)
        print(f"✅ O'qituvchi: {td['login']} | parol={td['pass']}")

# Guruhlar
db.flush()
all_teachers = db.query(Teacher).all()
groups_data = [
    {"name":"Matematika A", "subject":"Matematika", "tid":0, "fee":300000},
    {"name":"Matematika B", "subject":"Matematika", "tid":0, "fee":300000},
    {"name":"Kimyo guruh",  "subject":"Kimyo",       "tid":1, "fee":250000},
    {"name":"Ingliz tili A","subject":"Ingliz tili", "tid":2, "fee":280000},
]
group_objs = []
for gd in groups_data:
    g = db.query(Group).filter(Group.name == gd["name"]).first()
    if not g:
        tid = all_teachers[gd["tid"]].id if len(all_teachers) > gd["tid"] else None
        g = Group(name=gd["name"], subject=gd["subject"],
                  teacher_id=tid, monthly_fee=gd["fee"])
        db.add(g)
    group_objs.append(g)
db.flush()

# O'quvchilar
students_data = [
    {"login":"sherzod01","pass":"sherzod123","first":"Sherzod","last":"Zoirov"},
    {"login":"pokiza02", "pass":"pokiza123", "first":"Pokiza", "last":"Eshbo'riyeva"},
    {"login":"umida06",  "pass":"umida123",  "first":"Umida",  "last":"Mustafoyeva"},
    {"login":"azamat04", "pass":"azamat123", "first":"Azamat", "last":"Axrorov"},
    {"login":"gulnigor05","pass":"gulnigor123","first":"Gulnigor","last":"Sattorova"},
]
all_groups = db.query(Group).all()
for i, sd in enumerate(students_data):
    u = db.query(User).filter(User.login == sd["login"]).first()
    if not u:
        u = User(login=sd["login"], password=hash_password(sd["pass"]),
                 first_name=sd["first"], last_name=sd["last"],
                 role=UserRole.student)
        db.add(u)
        db.flush()
        s = Student(user_id=u.id)
        db.add(s)
        db.flush()
        # Guruhga qo'shish
        if all_groups:
            group = all_groups[i % len(all_groups)]
            group.students.append(s)
        print(f"✅ O'quvchi: {sd['login']} | parol={sd['pass']}")

# Resepshn yaratish
r = db.query(User).filter(User.login == "resepshn").first()
if not r:
    r = User(login="resepshn", password=hash_password("resepshn123"),
             first_name="Malika", last_name="Holiqova",
             role=UserRole.receptionist)
    db.add(r)
    print("✅ Resepshn: resepshn / resepshn123")

db.commit()
print("\n🎉 Barcha ma'lumotlar yuklandi!")
print("\n📋 Kirish ma'lumotlari:")
print("  Admin:      admin / admin123")
print("  O'qituvchi: akbar.teacher / akbar123")
print("  O'quvchi:   sherzod01 / sherzod123")
print("\n🚀 Serverni ishga tushirish: cd bs && uvicorn main:app --reload")
print("📚 API docs: http://localhost:8000/docs")
db.close()
