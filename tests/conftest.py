import pytest
from app import create_app
from database import db
from models.user import User
from models.supplier import Supplier
from models.product import Product


@pytest.fixture
def app():
    """Create and configure a clean testing application with in-memory SQLite database."""
    application = create_app("testing")

    with application.app_context():
        db.create_all()

        # Seed standard test users
        admin = User(
            username="testadmin",
            full_name="Test Administrator",
            role="admin",
            is_active=True,
        )
        admin.set_password("adminpass123")

        cashier = User(
            username="testcashier",
            full_name="Test Cashier",
            role="cashier",
            is_active=True,
        )
        cashier.set_password("cashierpass123")

        inactive_user = User(
            username="inactiveuser",
            full_name="Inactive User",
            role="cashier",
            is_active=False,
        )
        inactive_user.set_password("inactive123")

        # Seed supplier & test product
        supplier = Supplier(name="Organic Farms Co.", phone="9998887770", email="contact@organic.com")
        db.session.add_all([admin, cashier, inactive_user, supplier])
        db.session.flush()

        prod1 = Product(
            sku="TEST-SKU-001",
            name="Organic Apples",
            category="Fruits",
            unit_price=100.0,
            cost_price=70.0,
            stock_qty=50,
            reorder_level=10,
            supplier_id=supplier.supplier_id,
            is_active=True,
        )
        prod2 = Product(
            sku="TEST-SKU-002",
            name="Fresh Milk",
            category="Dairy",
            unit_price=50.0,
            cost_price=35.0,
            stock_qty=5,  # Low stock
            reorder_level=10,
            supplier_id=supplier.supplier_id,
            is_active=True,
        )
        db.session.add_all([prod1, prod2])
        db.session.commit()

        yield application

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """A test client logged in as an administrator."""
    client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def cashier_client(client):
    """A test client logged in as a cashier."""
    client.post(
        "/auth/login",
        data={"username": "testcashier", "password": "cashierpass123"},
        follow_redirects=True,
    )
    return client
