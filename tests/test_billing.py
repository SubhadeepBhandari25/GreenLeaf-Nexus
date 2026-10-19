import pytest
from database import db
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from models.inventory_movement import InventoryMovement
from services.billing_service import BillingService


def test_correct_total_calculation(app):
    """Test authoritative price and tax calculation without discount."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()  # unit_price = 100
        p2 = Product.query.filter_by(sku="TEST-SKU-002").first()  # unit_price = 50

        cart_data = [
            {"product_id": p1.product_id, "quantity": 2},  # 200
            {"product_id": p2.product_id, "quantity": 1},  # 50
        ]
        calc = BillingService.calculate_bill(cart_data, discount_percent=0.0)

        assert calc["subtotal"] == 250.0
        assert calc["discount_amount"] == 0.0
        assert calc["taxable_amount"] == 250.0
        assert calc["tax_amount"] == round(250.0 * 0.05, 2)  # 12.50
        assert calc["grand_total"] == 262.50


def test_calculation_with_discount(app):
    """Test calculations with 10% discount."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()  # 100
        cart_data = [{"product_id": p1.product_id, "quantity": 2}]  # 200
        calc = BillingService.calculate_bill(cart_data, discount_percent=10.0)

        assert calc["subtotal"] == 200.0
        assert calc["discount_amount"] == 20.0
        assert calc["taxable_amount"] == 180.0
        assert calc["tax_amount"] == round(180.0 * 0.05, 2)  # 9.00
        assert calc["grand_total"] == 189.00


def test_successful_checkout_and_stock_deduction(app):
    """Test checkout creates sale, sale_items, deducts stock, and logs inventory movements."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()
        initial_stock = p1.stock_qty  # 50

        cart_data = [{"product_id": p1.product_id, "quantity": 5}]
        sale = BillingService.process_checkout(
            cashier_id=1,
            cart_items_data=cart_data,
            discount_percent=0.0,
            payment_method="Cash",
        )

        assert sale is not None
        assert sale.invoice_number.startswith("GLN-")
        assert len(sale.items) == 1
        assert sale.items[0].product_name_snapshot == "Organic Apples"
        assert sale.items[0].quantity == 5

        # Verify stock deducted
        db.session.refresh(p1)
        assert p1.stock_qty == initial_stock - 5  # 45

        # Verify inventory movement record
        mov = InventoryMovement.query.filter_by(reference=sale.invoice_number).first()
        assert mov is not None
        assert mov.movement_type == "sale"
        assert mov.quantity_change == -5
        assert mov.resulting_stock == 45


def test_insufficient_stock_rejection_and_rollback(app):
    """Test checkout fails and rolls back when requested quantity exceeds available stock."""
    with app.app_context():
        p2 = Product.query.filter_by(sku="TEST-SKU-002").first()  # stock = 5
        initial_stock = p2.stock_qty

        cart_data = [{"product_id": p2.product_id, "quantity": 10}]  # 10 > 5

        with pytest.raises(ValueError) as exc:
            BillingService.process_checkout(cashier_id=1, cart_items_data=cart_data)

        assert "Insufficient stock" in str(exc.value)

        # Ensure no sale was created and stock remains untouched
        db.session.refresh(p2)
        assert p2.stock_qty == initial_stock


def test_empty_cart_rejection(app):
    """Test checkout rejects empty cart."""
    with app.app_context():
        with pytest.raises(ValueError) as exc:
            BillingService.process_checkout(cashier_id=1, cart_items_data=[])
        assert "empty cart" in str(exc.value).lower()


def test_invalid_discount_rejection(app):
    """Test discount exceeding maximum allowed percentage is rejected."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()
        cart_data = [{"product_id": p1.product_id, "quantity": 1}]

        with pytest.raises(ValueError) as exc:
            BillingService.calculate_bill(cart_data, discount_percent=50.0)  # Max is 30%
        assert "cannot exceed" in str(exc.value)
