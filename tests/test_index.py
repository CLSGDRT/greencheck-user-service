import pytest
from app.api.app import app
from app.models.db import db
from app.models.user import User
from flask_jwt_extended import create_access_token

# === FIXTURES ===

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()
        # Création d’un admin et d’un user de test
        admin = User(email='admin@test.com', role='admin', quota=100)
        user = User(email='user@test.com', role='user', quota=50)
        db.session.add_all([admin, user])
        db.session.commit()

        with app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()

@pytest.fixture
def app_context():
    """Contexte Flask pour les accès directs à la DB après une requête client."""
    with app.app_context():
        yield

# === UTILS ===

def get_jwt_for_user(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        return create_access_token(
            identity=user.email,
            additional_claims={'role': user.role, 'quota': user.quota}
        )

# === TESTS ===

def test_index(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b"user-service" in rv.data or b"Hello" in rv.data

def test_list_users_unauthorized(client):
    rv = client.get('/users')
    assert rv.status_code == 401  # JWT missing

def test_list_users_as_admin(client):
    token = get_jwt_for_user('admin@test.com')
    rv = client.get('/users', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert any(u['email'] == 'admin@test.com' for u in data)

def test_create_user_as_admin(client):
    token = get_jwt_for_user('admin@test.com')
    new_user = {
        "email": "newuser@test.com",
        "role": "user",
        "quota": 10
    }
    rv = client.post('/users', json=new_user, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 201
    data = rv.get_json()
    assert data['email'] == "newuser@test.com"

def test_create_user_as_non_admin(client):
    token = get_jwt_for_user('user@test.com')
    new_user = {
        "email": "failuser@test.com"
    }
    rv = client.post('/users', json=new_user, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 403  # Forbidden

def test_update_user_role_as_admin(client, app_context):
    token = get_jwt_for_user('admin@test.com')
    user = User.query.filter_by(email='user@test.com').first()

    rv = client.patch(f'/users/{user.id}/role', json={'role': 'admin'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200

    updated_user = db.session.get(User, user.id)
    assert updated_user.role == 'admin'

def test_update_user_quota_invalid(client, app_context):
    token = get_jwt_for_user('admin@test.com')
    admin = User.query.filter_by(email='admin@test.com').first()

    rv = client.patch(f'/users/{admin.id}/quota', json={'quota': -5}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 400
