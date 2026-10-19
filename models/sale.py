from datetime import datetime, date, time
from database import db


class Sale(db.Model):
    __tablename__ = "sales"

    sale_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sale_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    sale_time = db.Column(db.Time, nullable=False, default=lambda: datetime.now().time())
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(30), nullable=False, default="Cash")
    transaction_status = db.Column(db.String(20), nullable=False, default="completed", index=True)
    customer_name = db.Column(db.String(100), nullable=True)
    customer_phone = db.Column(db.String(30), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    cashier = db.relationship("User", back_populates="sales")
    items = db.relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan", lazy="joined")

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items) if self.items else 0

    def to_dict(self):
        return {
            "sale_id": self.sale_id,
            "invoice_number": self.invoice_number,
            "sale_date": self.sale_date.strftime("%Y-%m-%d"),
            "sale_time": self.sale_time.strftime("%H:%M:%S") if self.sale_time else "",
            "cashier_id": self.user_id,
            "cashier_name": self.cashier.full_name if self.cashier else "Unknown",
            "subtotal": round(self.subtotal, 2),
            "discount_amount": round(self.discount_amount, 2),
            "tax_amount": round(self.tax_amount, 2),
            "total_amount": round(self.total_amount, 2),
            "payment_method": self.payment_method,
            "transaction_status": self.transaction_status,
            "customer_name": self.customer_name or "",
            "customer_phone": self.customer_phone or "",
            "total_items": len(self.items) if self.items else 0,
            "total_quantity": self.total_quantity,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<Sale {self.invoice_number} - Total: {self.total_amount}>"
