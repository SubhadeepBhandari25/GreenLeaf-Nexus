import re
import pytest
from app import create_app
from database import db
from models.product import Product
from models.sale import Sale

def test_framer_scene_two_welcome_animation(admin_client):
    """Verify Framer Scene-Two multi-panel curtain split animation overlay is rendered."""
    res = admin_client.get("/dashboard?welcome=true")
    assert res.status_code == 200
    html = res.text

    # Scene-Two elements & typography
    assert 'id="nexusSceneTwoOverlay"' in html
    assert "nexus-shutter-curtains" in html
    assert "nexus-strip" in html
    assert "SCENE 02 // NEXUS ACTIVATION" in html
    assert "WELCOME TO" in html
    assert "GREENLEAF NEXUS" in html
    assert "btnEnterNexus" in html
    assert "btnReplayIntro" in html


def test_login_redirects_with_welcome_param(client):
    """Verify successful login appends welcome=true to initiate the opening page transition."""
    res = client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "welcome=true" in res.location


def test_blinkit_express_storefront(admin_client):
    """Verify Blinkit-style 10-minute quick-commerce storefront renders properly."""
    res = admin_client.get("/express/")
    assert res.status_code == 200
    html = res.text

    # Blinkit elements
    assert "10 MINS DELIVERY" in html
    assert "Indiranagar 100ft Rd" in html
    assert "blinkitCartPill" in html
    assert "blinkitCartDrawer" in html
    assert "btn-blinkit-add" in html
    assert "btnPlaceExpressOrder" in html


def test_blinkit_express_checkout_and_tracking(admin_client, app):
    """Verify instant 10-minute checkout processes stock deduction and loads tracking screen."""
    with app.app_context():
        prod = Product.query.filter_by(sku="TEST-SKU-001").first()
        initial_stock = prod.stock_qty

    # Perform express checkout
    payload = {
        "items": [{"product_id": prod.product_id, "quantity": 2}],
        "address": "Flat 402, Green Glen Layout, Indiranagar",
        "customer_name": "Test Express Shopper",
        "customer_phone": "9845012345",
        "payment_method": "UPI Instant",
        "tip_amount": 20.0,
    }

    res = admin_client.post("/express/checkout", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    inv = data["invoice_number"]
    assert inv.startswith("GLN-")

    # Verify stock deduction
    with app.app_context():
        prod_after = db.session.get(Product, prod.product_id)
        assert prod_after.stock_qty == initial_stock - 2

    # Verify Live 10-minute Tracking Screen
    track_res = admin_client.get(f"/express/track/{inv}")
    assert track_res.status_code == 200
    track_html = track_res.text
    assert "GREENLEAF 10-MIN EXPRESS" in track_html
    assert "etaCountdown" in track_html
    assert "routeProgress" in track_html
    assert "scooterMarker" in track_html
    assert "Delivery Lifecycle Stages" in track_html
    assert "Your Delivery Hero" in track_html


def test_dark_store_picker_console_and_dispatch(admin_client, app):
    """Verify dark store picker queue renders with 2-minute SLA and allows dispatch."""
    res = admin_client.get("/express/picker")
    assert res.status_code == 200
    html = res.text

    assert "Packing SLA Target" in html
    assert "02:00" in html
    assert "Station Pickers" in html

    # Dispatch an order if any exists
    with app.app_context():
        sale = Sale.query.first()
        if sale:
            disp_res = admin_client.post(
                f"/express/api/picker/dispatch/{sale.sale_id}",
                json={"packer": "Rajesh Kumar", "rider": "Vikram Singh"},
            )
            assert disp_res.status_code == 200
            assert disp_res.get_json()["success"] is True
