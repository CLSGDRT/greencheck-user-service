# GreenCheck - User Service

Ce microservice fait partie du projet **GreenCheck by AgroNovaTech**. Il est dédié à la **gestion des utilisateurs** avec une authentification sécurisée via **OAuth2 (Google)**, des **tokens JWT**, des **rôles** (admin/user), et une gestion des **quotas**.

## 🛠 Stack technique

- Python 3.12
- Flask
- Flask-SQLAlchemy
- Flask-Migrate (Alembic)
- Flask-JWT-Extended
- Authlib (OAuth2 avec Google)
- SQLite (dev) / PostgreSQL (prod possible)
- Pytest

## ⚙️ Configuration (.env)

```dotenv
FLASK_ENV=development
DATABASE_URL=sqlite:////user-service.db

# Superutilisateur créé au premier démarrage
FIRST_ADMIN_EMAIL=mail@mail.com
FIRST_ADMIN_ROLE=admin
FIRST_ADMIN_QUOTA=10000

# Clé secrète JWT (à changer en production)
JWT_SECRET_KEY=JWT_secret

# OAuth Google (remplace par tes vraies valeurs)
GOOGLE_CLIENT_ID=ton_client_id_google
GOOGLE_CLIENT_SECRET=ton_client_secret_google
