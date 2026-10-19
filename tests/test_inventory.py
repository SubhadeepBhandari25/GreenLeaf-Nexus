from datetime import date, timedelta
from database import db
from models.product import Product
from models.inventory_movement import InventoryMovement
from services.inventory_service import InventoryService


def test_low_stock_detection(app):
    """Test detection of products at or below their reorder level."""
    with app.app_context():
        # TEST-SKU-002 has stock_qty=5 and reorder_level=10 -> Low Stock
        low_items = InventoryService.get_low_stock_products()
        assert len(low_items) == 1
        assert low_items[0].sku == "TEST-SKU-002"
        assert low_items[0].is_low_stock is True


def test_expiry_alerts_detection(app):
    """Test expiry surveillance for expired and near-expiry dates."""
    with app.app_context():
        today = date.today()
        # Add expired product
        p_exp = Product(
            sku="EXP-001",
            name="Expired Yoghurt",
            category="Dairy",
            unit_price=40.0,
            stock_qty=10,
            reorder_level=5,
            expiry_date=today - timedelta(days=3),
            is_active=True,
        )
        # Add near-expiry product (expiring in 5 days)
        p_near = Product(
            sku="NEAR-002",
            name="Near Expiry Bread",
            category="Bakery",
            unit_price=35.0,
            stock_qty=8,
            reorder_level=5,
            expiry_date=today + timedelta(days=5),
            is_active=True,
        )
        db.session.add_all([p_exp, p_near])
        db.session.commit()

        alerts = InventoryService.get_expiry_alerts(days=15)
        skus = [p.sku for p in alerts]
        assert "EXP-001" in skus
        assert "NEAR-002" in skus
        assert p_exp.expiry_status == "expired"
        assert p_near.expiry_status == "within_7"


def test_stock_restocking_movement(app):
    """Test restocking increases product stock and records InventoryMovement."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()  # stock = 50
        updated = InventoryService.restock_product(
            product_id=p1.product_id,
            quantity_added=25,
            user_id=1,
            reference="PO-TEST-100",
            notes="Vendor shipment intake",
        )

        assert updated.stock_qty == 75

        # Check movement record
        mov = InventoryMovement.query.filter_by(reference="PO-TEST-100").first()
        assert mov is not None
        assert mov.movement_type == "restock"
        assert mov.quantity_change == 25
        assert mov.previous_stock == 50
        assert mov.resulting_stock == 75


def test_stock_adjustment_movement(app):
    """Test physical count adjustment updates stock and logs delta movement."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()  # stock = 50
        updated = InventoryService.adjust_stock(
            product_id=p1.product_id,
            new_quantity=48,  # -2 discrepancy
            user_id=1,
            reason="Audit Discrepancy",
        )

        assert updated.stock_qty == 48

        mov = InventoryMovement.query.filter_by(reference="Audit Discrepancy").first()
        assert mov is not None
        assert mov.movement_type == "adjustment"
        assert mov.quantity_change == -2
        assert mov.previous_stock == 50
        assert mov.resulting_stock == 48
