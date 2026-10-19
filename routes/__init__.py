from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.pos import pos_bp
from routes.products import products_bp
from routes.inventory import inventory_bp
from routes.suppliers import suppliers_bp
from routes.sales import sales_bp
from routes.analytics import analytics_bp
from routes.reports import reports_bp
from routes.users import users_bp
from routes.express import express_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "pos_bp",
    "products_bp",
    "inventory_bp",
    "suppliers_bp",
    "sales_bp",
    "analytics_bp",
    "reports_bp",
    "users_bp",
    "express_bp",
]

