import pytest
from database import db
from models.product import Product
from services.food_api_service import FoodApiService
from populate_indian_snacks import INDIAN_SNACKS


def seed_test_indian_snacks(app):
    """Seed sample Indian snacks into the test database context."""
    with app.app_context():
        for sku, name, category, unit_price, cost_price, reorder_lvl, barcode, img_url, desc in INDIAN_SNACKS[:5]:
            if not Product.query.filter_by(sku=sku).first():
                prod = Product(
                    sku=sku,
                    barcode=barcode,
                    name=name,
                    description=desc,
                    category=category,
                    unit_price=unit_price,
                    cost_price=cost_price,
                    stock_qty=50,
                    reorder_level=reorder_lvl,
                    image_path=img_url,
                    is_active=True,
                )
                db.session.add(prod)
        db.session.commit()


def test_indian_snacks_exist_and_seed(admin_client, app):
    """Verify that the iconic Indian snacks can be seeded, queried, and verified."""
    seed_test_indian_snacks(app)
    with app.app_context():
        bhujia = Product.query.filter(Product.name.ilike("%Bhujia Sev%")).first()
        assert bhujia is not None, "Expected Haldiram's Bhujia Sev to exist"
        assert bhujia.category == "Snacks"
        assert bhujia.unit_price == 55.0
        assert bhujia.stock_qty == 50
        assert bhujia.image_path is not None and (bhujia.image_path.startswith("http") or bhujia.image_path.startswith("/static"))


def test_food_api_service_indian_snacks_cache():
    """Verify that Open Food Facts service has popular Indian snacks indexed."""
    # Test Bhujia Sev barcode
    res = FoodApiService.lookup_by_barcode("8904004400210")
    assert res is not None
    assert "Bhujia Sev" in res["name"]
    assert res["brand"] == "Haldiram's"
    assert res["category"] == "Snacks"

    # Test Kurkure barcode
    res_k = FoodApiService.lookup_by_barcode("8901491102148")
    assert res_k is not None
    assert "Kurkure" in res_k["name"]

    # Test Lay's Magic Masala
    res_l = FoodApiService.lookup_by_barcode("8901491101851")
    assert res_l is not None
    assert "Magic Masala" in res_l["name"]

    # Test Parle-G Gold
    res_p = FoodApiService.lookup_by_barcode("8901719101014")
    assert res_p is not None
    assert "Parle-G" in res_p["name"]


def test_express_storefront_displays_indian_snacks(admin_client, app):
    """Verify that the 10-minute Express Store renders the Indian Snacks corner and items."""
    seed_test_indian_snacks(app)
    res = admin_client.get("/express/")
    assert res.status_code == 200
    html = res.text
    assert "Indian Snacks & Namkeen Corner" in html
    assert "Bhujia & Namkeen" in html
    assert "Masala Chips & Kurkure" in html
    assert "Chai Biscuits & Cookies" in html
    assert "Haldiram" in html


def test_express_checkout_with_indian_snack(admin_client, app):
    """Verify that an express quick-commerce order containing an Indian snack can be placed."""
    seed_test_indian_snacks(app)
    with app.app_context():
        bhujia = Product.query.filter(Product.name.ilike("%Bhujia Sev%")).first()
        assert bhujia is not None
        prod_id = bhujia.product_id
        initial_stock = bhujia.stock_qty

    order_data = {
        "items": [{"product_id": prod_id, "quantity": 2}],
        "address": "Indiranagar 100ft Rd, Bengaluru",
        "customer_name": "Snack Lover",
        "customer_phone": "9876543210",
        "payment_method": "UPI Instant",
        "tip_amount": 20.0,
    }

    res = admin_client.post("/express/checkout", json=order_data)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "invoice_number" in data

    # Verify inventory was decremented
    with app.app_context():
        updated_bhujia = db.session.get(Product, prod_id)
        assert updated_bhujia.stock_qty == initial_stock - 2
