from datetime import datetime, date
from database import db


class Product(db.Model):
    __tablename__ = "products"

    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(50), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, default=0.0, nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=10)
    expiry_date = db.Column(db.Date, nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.supplier_id"), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    supplier = db.relationship("Supplier", back_populates="products")
    sale_items = db.relationship("SaleItem", back_populates="product", lazy="dynamic")
    movements = db.relationship("InventoryMovement", back_populates="product", lazy="dynamic")

    @property
    def is_low_stock(self):
        return self.stock_qty <= self.reorder_level

    @property
    def stock_status(self):
        if self.stock_qty <= 0:
            return "out_of_stock"
        if self.stock_qty <= self.reorder_level:
            return "low_stock"
        return "in_stock"

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        today = date.today()
        return (self.expiry_date - today).days

    @property
    def expiry_status(self):
        if not self.expiry_date:
            return "no_expiry"
        days = self.days_to_expiry
        if days < 0:
            return "expired"
        elif days == 0:
            return "today"
        elif days <= 7:
            return "within_7"
        elif days <= 15:
            return "within_15"
        else:
            return "safe"

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "barcode": self.barcode or "",
            "name": self.name,
            "description": self.description or "",
            "category": self.category,
            "unit_price": round(self.unit_price, 2),
            "cost_price": round(self.cost_price, 2),
            "stock_qty": self.stock_qty,
            "reorder_level": self.reorder_level,
            "expiry_date": self.expiry_date.strftime("%Y-%m-%d") if self.expiry_date else None,
            "days_to_expiry": self.days_to_expiry,
            "expiry_status": self.expiry_status,
            "stock_status": self.stock_status,
            "is_low_stock": self.is_low_stock,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "image_path": self.image_path or "",
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<Product {self.sku} - {self.name} (Stock: {self.stock_qty})>"
