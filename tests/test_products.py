from database import db
from models.product import Product


def test_create_product_success(admin_client):
    """Test creating a valid product."""
    resp = admin_client.post(
        "/products/new",
        data={
            "sku": "NEW-PROD-001",
            "name": "Fresh Oranges",
            "category": "Fruits",
            "unit_price": "80.0",
            "cost_price": "55.0",
            "stock_qty": "40",
            "reorder_level": "10",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"created successfully" in resp.data

    prod = Product.query.filter_by(sku="NEW-PROD-001").first()
    assert prod is not None
    assert prod.name == "Fresh Oranges"
    assert prod.stock_qty == 40


def test_reject_duplicate_sku(admin_client):
    """Test duplicate SKU rejection."""
    resp = admin_client.post(
        "/products/new",
        data={
            "sku": "TEST-SKU-001",  # Already exists in fixture
            "name": "Another Apple",
            "category": "Fruits",
            "unit_price": "90.0",
            "cost_price": "60.0",
            "stock_qty": "10",
            "reorder_level": "5",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data


def test_reject_negative_price(admin_client):
    """Test negative unit price rejection."""
    resp = admin_client.post(
        "/products/new",
        data={
            "sku": "NEG-PRICE-001",
            "name": "Invalid Price Item",
            "category": "Fruits",
            "unit_price": "-15.0",
            "stock_qty": "10",
            "reorder_level": "5",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Unit price cannot be negative" in resp.data


def test_reject_negative_stock(admin_client):
    """Test negative stock quantity rejection."""
    resp = admin_client.post(
        "/products/new",
        data={
            "sku": "NEG-STOCK-001",
            "name": "Invalid Stock Item",
            "category": "Fruits",
            "unit_price": "50.0",
            "stock_qty": "-5",
            "reorder_level": "5",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Stock quantity cannot be negative" in resp.data


def test_create_product_with_image(admin_client):
    """Test product creation with authentic image URL and barcode."""
    img_url = "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=400&q=80"
    resp = admin_client.post(
        "/products/new",
        data={
            "sku": "IMG-PROD-001",
            "name": "Fuji Apples Premium",
            "category": "Fruits",
            "barcode": "8909999001",
            "image_path": img_url,
            "unit_price": "140.0",
            "cost_price": "95.0",
            "stock_qty": "30",
            "reorder_level": "10",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    prod = Product.query.filter_by(sku="IMG-PROD-001").first()
    assert prod is not None
    assert prod.image_path == img_url
    assert prod.barcode == "8909999001"


def test_open_food_facts_api_lookup(admin_client):
    """Test Open Food Facts live lookup proxy endpoint with verified barcode."""
    resp = admin_client.get("/products/api/openfoodfacts/3017620422003")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["found"] is True
    assert "Nutella" in data["name"]
    assert "image_url" in data
    assert data["image_url"].startswith("http")


def test_open_food_facts_popular_items(admin_client):
    """Test retrieving popular Open Food Facts verified grocery products."""
    resp = admin_client.get("/products/api/openfoodfacts/popular")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert len(data["items"]) >= 5
    assert any("Coca-Cola" in item["name"] for item in data["items"])


def test_import_food_item_one_click(admin_client):
    """Test 1-click import from Open Food Facts into inventory."""
    resp = admin_client.post(
        "/products/import-food-item",
        data={
            "barcode": "999888777666",
            "name": "Artisan Olive Oil Crackers",
            "category": "Snacks",
            "image_url": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80",
            "unit_price": "120.0",
            "cost_price": "85.0",
            "stock_qty": "20",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    prod = Product.query.filter_by(barcode="999888777666").first()
    assert prod is not None
    assert prod.name == "Artisan Olive Oil Crackers"
    assert prod.stock_qty == 20
    assert prod.image_path.startswith("http")

