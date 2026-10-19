from datetime import datetime
from database import db


class Supplier(db.Model):
    __tablename__ = "suppliers"

    supplier_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    products = db.relationship("Product", back_populates="supplier", lazy="dynamic")

    def to_dict(self):
        return {
            "supplier_id": self.supplier_id,
            "name": self.name,
            "phone": self.phone or "",
            "email": self.email or "",
            "address": self.address or "",
            "product_count": self.products.count() if hasattr(self, "products") else 0,
            "created_at": self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
        }

    def __repr__(self):
        return f"<Supplier {self.name}>"
