from datetime import date, timedelta
from database import db
from models.product import Product
from models.inventory_movement import InventoryMovement


class InventoryService:
    @staticmethod
    def restock_product(product_id, quantity_added, user_id=None, reference=None, notes=None):
        """
        Safely adds new stock to an existing product and records an inventory movement.
        """
        if quantity_added <= 0:
            raise ValueError(f"Restock quantity must be positive. Got {quantity_added}.")

        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product ID {product_id} not found.")

        prev_stock = product.stock_qty
        new_stock = prev_stock + quantity_added
        product.stock_qty = new_stock

        movement = InventoryMovement(
            product_id=product.product_id,
            user_id=user_id,
            movement_type="restock",
            quantity_change=quantity_added,
            previous_stock=prev_stock,
            resulting_stock=new_stock,
            reference=reference or "Manual Restock",
            notes=notes or f"Restocked {quantity_added} units",
        )
        db.session.add(movement)
        db.session.commit()
        return product

    @staticmethod
    def adjust_stock(product_id, new_quantity, user_id=None, reason="Stock Adjustment", notes=None):
        """
        Adjusts product stock to an exact physical count and records an inventory movement.
        """
        if new_quantity < 0:
            raise ValueError("Stock quantity cannot be negative.")

        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product ID {product_id} not found.")

        prev_stock = product.stock_qty
        diff = new_quantity - prev_stock
        if diff == 0:
            return product

        product.stock_qty = new_quantity

        movement = InventoryMovement(
            product_id=product.product_id,
            user_id=user_id,
            movement_type="adjustment",
            quantity_change=diff,
            previous_stock=prev_stock,
            resulting_stock=new_quantity,
            reference=reason,
            notes=notes or f"Adjusted stock from {prev_stock} to {new_quantity}",
        )
        db.session.add(movement)
        db.session.commit()
        return product

    @staticmethod
    def get_low_stock_products(limit=None):
        """Returns active products at or below their reorder level."""
        query = Product.query.filter(
            Product.is_active == True,
            Product.stock_qty <= Product.reorder_level,
        ).order_by(Product.stock_qty.asc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def get_expiry_alerts(days=15):
        """
        Returns active products that are expired or expiring within the specified days threshold.
        """
        today = date.today()
        target_date = today + timedelta(days=days)

        products = Product.query.filter(
            Product.is_active == True,
            Product.expiry_date.isnot(None),
            Product.expiry_date <= target_date,
        ).order_by(Product.expiry_date.asc()).all()

        return products

    @staticmethod
    def get_inventory_summary():
        """Computes comprehensive inventory valuation and health KPIs."""
        products = Product.query.filter_by(is_active=True).all()
        total_items = len(products)
        total_units = sum(p.stock_qty for p in products)
        retail_value = sum(p.stock_qty * p.unit_price for p in products)
        cost_value = sum(p.stock_qty * p.cost_price for p in products)
        low_stock_count = sum(1 for p in products if p.is_low_stock)

        today = date.today()
        expired_count = sum(
            1 for p in products if p.expiry_date and p.expiry_date < today
        )
        near_expiry_count = sum(
            1 for p in products if p.expiry_date and today <= p.expiry_date <= today + timedelta(days=15)
        )

        return {
            "total_products": total_items,
            "total_units": total_units,
            "retail_value": round(retail_value, 2),
            "cost_value": round(cost_value, 2),
            "potential_profit": round(retail_value - cost_value, 2),
            "low_stock_count": low_stock_count,
            "expired_count": expired_count,
            "near_expiry_count": near_expiry_count,
        }
