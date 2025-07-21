from app.models.db import db

class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user'),
    )  

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    provider = db.Column(db.String)
    provider_user_id = db.Column(db.String)
    role = db.Column(db.String, default='user')
    quota = db.Column(db.Integer, default=100)

    @classmethod
    def find_by_provider(cls, provider, provider_user_id):
        return cls.query.filter_by(provider=provider, provider_user_id=provider_user_id).first()

    @classmethod
    def create_from_oauth(cls, email, provider, provider_user_id, role='user', quota=100):
        user = cls(
            email=email,
            provider=provider,
            provider_user_id=provider_user_id,
            role=role,
            quota=quota
        )
        db.session.add(user)
        db.session.commit()
        return user