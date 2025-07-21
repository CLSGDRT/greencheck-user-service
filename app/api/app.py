from flask import Flask, request, redirect, url_for, jsonify
from authlib.integrations.flask_client import OAuth
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity, get_jwt
)
from app.models.db import db
from app.models.user import User
from functools import wraps
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config.from_object("app.config.Config")

# Initialisation de la base de données (SQLAlchemy)
db.init_app(app)

# Configuration et initialisation de JWTManager pour gérer les JWT
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
jwt = JWTManager(app)

# Configuration du client OAuth2 avec Google via Authlib
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v2/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            jwt_required()(lambda: None)()
            claims = get_jwt()
            if claims.get('role') != required_role:
                return jsonify(msg="Forbidden: insufficient privileges"), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# --- Routes OAuth2 ---

@app.route('/auth/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token)
    if not user_info:
        return jsonify({"error": "Failed to fetch user info"}), 400

    email = user_info.get('email')
    provider_user_id = user_info.get('sub')

    user = User.find_by_provider('google', provider_user_id)
    if not user:
        user = User.create_from_oauth(email, 'google', provider_user_id)

    additional_claims = {
        'role': user.role,
        'quota': user.quota,
    }
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)

    return jsonify(access_token=access_token, token_type='bearer')

# --- Routes CRUD utilisateurs ---

@app.route('/users', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_user():
    data = request.json
    if not data or 'email' not in data:
        return jsonify({"error": "Missing email"}), 400

    user = User(
        email=data['email'],
        provider=data.get('provider', 'local'),
        provider_user_id=data.get('provider_user_id'),
        role=data.get('role', 'user'),
        quota=data.get('quota', 100),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(id=user.id, email=user.email, role=user.role), 201

@app.route('/users', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_users():
    users = User.query.all()
    result = [
        {"id": u.id, "email": u.email, "role": u.role}
        for u in users
    ]
    return jsonify(result)

@app.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    claims = get_jwt()
    current_user_id = get_jwt_identity()

    if claims.get('role') != 'admin' and str(current_user_id) != str(user_id):
        return jsonify({"msg": "Forbidden"}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    return jsonify(id=user.id, email=user.email, role=user.role, quota=user.quota)

@app.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    claims = get_jwt()
    current_user_id = get_jwt_identity()

    if claims.get('role') != 'admin' and str(current_user_id) != str(user_id):
        return jsonify({"msg": "Forbidden"}), 403

    data = request.json
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    if 'email' in data:
        user.email = data['email']
    if 'quota' in data and claims.get('role') == 'admin':
        user.quota = data['quota']
    if 'role' in data and claims.get('role') == 'admin':
        user.role = data['role']

    db.session.commit()
    return jsonify(id=user.id, email=user.email, role=user.role, quota=user.quota)

@app.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "User deleted"}), 200

@app.route('/users/me', methods=['GET'])
@jwt_required()
def me():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    return jsonify(id=user.id, email=user.email, role=user.role, quota=user.quota)

@app.route("/users/<int:user_id>/role", methods=["PATCH"])
@jwt_required()
@role_required("admin")
def update_user_role(user_id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify(msg="Only admins can update roles"), 403

    data = request.get_json()
    new_role = data.get("role")

    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg="User not found"), 404

    user.role = new_role
    db.session.commit()
    return jsonify(msg="Role updated successfully"), 200

@app.route("/users/<int:user_id>/quota", methods=["PATCH"])
@jwt_required()
@role_required("admin")
def update_user_quota(user_id):
    data = request.get_json()
    try:
        new_quota = int(data.get("quota"))
        if new_quota < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid quota value"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.quota = new_quota
    db.session.commit()
    return jsonify({"message": f"Quota updated to {new_quota} for user {user_id}"}), 200

@app.route('/')
def index():
    return "Hello from user-service!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
