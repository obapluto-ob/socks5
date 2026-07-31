from app import create_app, db
from app.models import Admin

app = create_app()

with app.app_context():
    db.create_all()
    username = input("Admin username: ")
    password = input("Admin password: ")
    if Admin.query.filter_by(username=username).first():
        print("Admin already exists.")
    else:
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin '{username}' created.")
