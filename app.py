import os
from pathlib import Path
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import config
from database import db
from models.user import User
from models.product import Product
from routes import (
    auth_bp,
    dashboard_bp,
    pos_bp,
    products_bp,
    inventory_bp,
    suppliers_bp,
    sales_bp,
    analytics_bp,
    reports_bp,
    users_bp,
    express_bp,
)

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config["default"]))

    # Ensure required runtime folders exist
    base_dir = Path(app.root_path)
    (base_dir / "instance").mkdir(parents=True, exist_ok=True)
    (base_dir / "exports").mkdir(parents=True, exist_ok=True)
    (base_dir / "static" / "uploads").mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Exempt POS checkout JSON API from CSRF header requirement if needed or support CSRF header
    # We will pass CSRF token in POS page and header, so standard CSRF protection remains active!

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Jinja context processor for global navigation indicators & store branding
    @app.context_processor
    def inject_global_vars():
        low_stock_count = 0
        try:
            low_stock_count = Product.query.filter(
                Product.is_active == True,
                Product.stock_qty <= Product.reorder_level,
            ).count()
        except Exception:
            pass

        return {
            "STORE_NAME": app.config.get("STORE_NAME", "GreenLeaf Grocers"),
            "STORE_TAGLINE": app.config.get("STORE_TAGLINE", "Fresh Stock. Smart Decisions."),
            "CURRENCY": app.config.get("CURRENCY_SYMBOL", "₹"),
            "LOW_STOCK_GLOBAL_COUNT": low_stock_count,
        }

    # Custom Jinja filters
    @app.template_filter("currency")
    def currency_filter(val):
        try:
            return f"₹{float(val):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(express_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # Auto-create tables if database not initialized
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    # If launched within Streamlit Cloud or via 'streamlit run app.py'
    try:
        import streamlit.runtime as _rt
        if _rt.exists():
            import streamlit as _st
            import streamlit_app
            if hasattr(streamlit_app, "main"):
                streamlit_app.main()
            _st.stop()
    except (ImportError, Exception):
        pass

    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)
