def test_valid_admin_login(client):
    """Test successful login for an active admin user."""
    resp = client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Welcome back, Test Administrator!" in resp.data
    assert b"Store Analytics Dashboard" in resp.data


def test_valid_cashier_login(client):
    """Test successful login for an active cashier redirects to POS."""
    resp = client.post(
        "/auth/login",
        data={"username": "testcashier", "password": "cashierpass123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Welcome back, Test Cashier!" in resp.data
    assert b"Point of Sale (POS)" in resp.data


def test_invalid_login_wrong_password(client):
    """Test login rejection when incorrect password provided."""
    resp = client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_inactive_account_rejected(client):
    """Test login rejection for deactivated user accounts."""
    resp = client.post(
        "/auth/login",
        data={"username": "inactiveuser", "password": "inactive123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Your account has been deactivated" in resp.data


def test_logout(admin_client):
    """Test session termination on logout."""
    resp = admin_client.get("/auth/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert b"successfully logged out" in resp.data
