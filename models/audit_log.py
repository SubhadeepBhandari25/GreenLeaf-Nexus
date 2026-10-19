from datetime import datetime
from database import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "System",
            "action": self.action,
            "entity_type": self.entity_type or "",
            "entity_id": self.entity_id,
            "details": self.details or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<AuditLog {self.action} by User {self.user_id}>"
