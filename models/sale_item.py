from database import db


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    sale_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.sale_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, index=True)
    product_name_snapshot = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    unit_cost_snapshot = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    line_total = db.Column(db.Float, nullable=False)

    # Relationships
    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product", back_populates="sale_items")

    def to_dict(self):
        return {
            "sale_item_id": self.sale_item_id,
            "sale_id": self.sale_id,
            "product_id": self.product_id,
            "product_name": self.product_name_snapshot,
            "quantity": self.quantity,
            "unit_price": round(self.unit_price, 2),
            "unit_cost": round(self.unit_cost_snapshot, 2),
            "discount_amount": round(self.discount_amount, 2),
            "line_total": round(self.line_total, 2),
        }

    def __repr__(self):
        return f"<SaleItem {self.product_name_snapshot} x {self.quantity} = {self.line_total}>"
