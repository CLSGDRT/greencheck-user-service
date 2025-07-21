import pytest
import os
import tempfile
from app.api.app import app
from app.models.db import db
from app.models.user import User
from flask_jwt_extended import create_access_token


@pytest.fixture(scope='function')
def test_app():
    """Create a test application with isolated configuration"""
    # Créer un fichier temporaire pour la base de données de test
    db_fd, db_path = tempfile.mkstemp()
    
    # Configuration de test
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'JWT_SECRET_KEY': 'test-secret-key-for-testing',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret'
    }
    
    # Appliquer la configuration de test
    app.config.update(test_config)
    
    with app.app_context():
        # Créer les tables
        db.create_all()
        
        # Créer les utilisateurs de test
        admin = User(email='admin@test.com', role='admin', quota=100)
        user = User(email='user@test.com', role='user', quota=50)
        db.session.add_all([admin, user])
        db.session.commit()
        
        yield app
        
        # Nettoyage
        db.session.remove()
        db.drop_all()
    
    # Fermer et supprimer le fichier temporaire
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(test_app):
    """Create a test client"""
    return test_app.test_client()


def get_jwt_for_user(user):
    """Helper function to generate JWT token for a user"""
    return create_access_token(
        identity=user.email, 
        additional_claims={
            'role': user.role, 
            'quota': user.quota,
            'user_id': user.id
        }
    )


def test_index(client):
    """Test de la route index"""
    rv = client.get('/')
    assert rv.status_code == 200
    response_data = rv.data.decode('utf-8').lower()
    assert "user-service" in response_data or "hello" in response_data


def test_list_users_unauthorized(client):
    """Test d'accès non autorisé à la liste des utilisateurs"""
    rv = client.get('/users')
    assert rv.status_code == 401


def test_list_users_as_admin(client):
    """Test d'accès à la liste des utilisateurs en tant qu'admin"""
    admin = User.query.filter_by(email='admin@test.com').first()
    assert admin is not None, "Admin user not found in database"
    
    token = get_jwt_for_user(admin)
    
    rv = client.get('/users', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    
    data = rv.get_json()
    assert data is not None, "Response should contain JSON data"
    assert isinstance(data, list), "Response should be a list of users"
    assert any(u['email'] == 'admin@test.com' for u in data)


def test_create_user_as_admin(client):
    """Test de création d'utilisateur en tant qu'admin"""
    admin = User.query.filter_by(email='admin@test.com').first()
    assert admin is not None, "Admin user not found in database"
    
    token = get_jwt_for_user(admin)
    
    new_user = {
        "email": "newuser@test.com",
        "role": "user",
        "quota": 10
    }
    
    rv = client.post('/users', json=new_user, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 201
    
    data = rv.get_json()
    assert data is not None, "Response should contain JSON data"
    assert data['email'] == "newuser@test.com"
    
    # Vérification en base
    created_user = User.query.filter_by(email='newuser@test.com').first()
    assert created_user is not None, "User should be created in database"


def test_create_user_as_non_admin(client):
    """Test de création d'utilisateur en tant qu'utilisateur normal (doit échouer)"""
    user = User.query.filter_by(email='user@test.com').first()
    assert user is not None, "User not found in database"
    
    token = get_jwt_for_user(user)
    
    new_user = {
        "email": "failuser@test.com",
        "role": "user",
        "quota": 10
    }
    
    rv = client.post('/users', json=new_user, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 403


def test_update_user_role_as_admin(client):
    """Test de modification du rôle d'un utilisateur en tant qu'admin"""
    admin = User.query.filter_by(email='admin@test.com').first()
    user = User.query.filter_by(email='user@test.com').first()
    assert admin is not None, "Admin user not found in database"
    assert user is not None, "User not found in database"
    
    token = get_jwt_for_user(admin)
    user_id = user.id
    
    rv = client.patch(f'/users/{user_id}/role', 
                     json={'role': 'admin'}, 
                     headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    
    # Vérification de la modification
    updated_user = db.session.get(User, user_id)
    assert updated_user is not None, "User should still exist after update"
    assert updated_user.role == 'admin', "User role should be updated to admin"


def test_update_user_quota_invalid(client):
    """Test de modification de quota avec une valeur invalide"""
    admin = User.query.filter_by(email='admin@test.com').first()
    assert admin is not None, "Admin user not found in database"
    
    token = get_jwt_for_user(admin)
    admin_id = admin.id
    
    rv = client.patch(f'/users/{admin_id}/quota', 
                     json={'quota': -5}, 
                     headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 400


def test_update_user_quota_valid(client):
    """Test de modification de quota avec une valeur valide"""
    admin = User.query.filter_by(email='admin@test.com').first()
    user = User.query.filter_by(email='user@test.com').first()
    assert admin is not None, "Admin user not found in database"
    assert user is not None, "User not found in database"
    
    token = get_jwt_for_user(admin)
    user_id = user.id
    
    rv = client.patch(f'/users/{user_id}/quota', 
                     json={'quota': 75}, 
                     headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    
    # Vérification de la modification
    updated_user = db.session.get(User, user_id)
    assert updated_user is not None, "User should still exist after update"
    assert updated_user.quota == 75, "User quota should be updated to 75"


# Test pour vérifier que la base de données est bien isolée
def test_database_isolation(client):
    """Test que chaque test a une base de données fraîche"""
    # Ce test ne devrait pas voir l'utilisateur créé dans test_create_user_as_admin
    users = User.query.all()
    emails = [u.email for u in users]
    assert "newuser@test.com" not in emails, "Database should be isolated between tests"
    
    # On devrait seulement voir les utilisateurs de base (admin et user)
    assert len(users) == 2
    assert "admin@test.com" in emails
    assert "user@test.com" in emails