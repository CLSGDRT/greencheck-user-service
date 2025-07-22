import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.app import app
from app.models.db import db
from app.models.user import User

def create_first_admin():
    first_admin_email = os.getenv("FIRST_ADMIN_EMAIL")
    first_admin_role = os.getenv("FIRST_ADMIN_ROLE", "admin")
    first_admin_quota = int(os.getenv("FIRST_ADMIN_QUOTA", 1000))
    
    if not first_admin_email:
        print("⚠️ FIRST_ADMIN_EMAIL non défini, pas de création du superuser.")
        return
    
    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()
        
        existing = User.query.filter_by(email=first_admin_email, role=first_admin_role).first()
        if existing:
            print(f"✅ Superuser déjà existant : {first_admin_email}")
        else:
            admin = User(
                email=first_admin_email,
                provider="local",
                provider_user_id=None,
                role=first_admin_role,
                quota=first_admin_quota,
            )
            db.session.add(admin)
            db.session.commit()
            print(f"🚀 Premier superuser créé : {first_admin_email}")

if __name__ == "__main__":
    create_first_admin()