from datetime import datetime
from database import db


class InventoryMovement(db.Model):
    __tablename__ = "inventory_movements"

    movement_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True, index=True)
    movement_type = db.Column(db.String(30), nullable=False, index=True)  # 'sale', 'restock', 'adjustment', 'return', 'initial'
    quantity_change = db.Column(db.Integer, nullable=False)  # +ve or -ve
    previous_stock = db.Column(db.Integer, nullable=False)
    resulting_stock = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100), nullable=True)  # e.g., Invoice # or PO #
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    product = db.relationship("Product", back_populates="movements")
    user = db.relationship("User", back_populates="movements")

    def to_dict(self):
        return {
            "movement_id": self.movement_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "Unknown",
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "System",
            "movement_type": self.movement_type,
            "quantity_change": self.quantity_change,
            "previous_stock": self.previous_stock,
            "resulting_stock": self.resulting_stock,
            "reference": self.reference or "",
            "notes": self.notes or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<InventoryMovement {self.movement_type} {self.quantity_change} on Prod {self.product_id}>"
