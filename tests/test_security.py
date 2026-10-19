def test_unauthenticated_redirect(client):
    """Test unauthenticated requests are redirected to login."""
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_cashier_cannot_access_admin_dashboard(cashier_client):
    """Test cashier role receives 403 Forbidden when requesting admin dashboard."""
    resp = cashier_client.get("/dashboard")
    assert resp.status_code == 403
    assert b"Access Denied" in resp.data


def test_cashier_cannot_access_product_management(cashier_client):
    """Test cashier cannot create products."""
    resp = cashier_client.get("/products/new")
    assert resp.status_code == 403


def test_cashier_cannot_access_user_management(cashier_client):
    """Test cashier cannot view or modify user accounts."""
    resp = cashier_client.get("/users/")
    assert resp.status_code == 403


def test_cashier_cannot_access_reports_or_exports(cashier_client):
    """Test cashier cannot trigger administrative CSV exports."""
    resp = cashier_client.get("/reports/export/sales")
    assert resp.status_code == 403
