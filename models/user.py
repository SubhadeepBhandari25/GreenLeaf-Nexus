from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="cashier")  # 'admin' or 'cashier'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sales = db.relationship("Sale", back_populates="cashier", lazy="dynamic")
    movements = db.relationship("InventoryMovement", back_populates="user", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
