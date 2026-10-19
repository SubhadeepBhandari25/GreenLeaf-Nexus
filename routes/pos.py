from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from database import db
from models.product import Product
from services.billing_service import BillingService

pos_bp = Blueprint("pos", __name__, url_prefix="/pos")


@pos_bp.route("")
@pos_bp.route("/")
@login_required
def index():
    # Fetch active categories
    categories = [
        c[0] for c in db.session.query(Product.category)
        .filter(Product.is_active == True)
        .distinct()
        .order_by(Product.category.asc())
        .all()
    ]

    # Preload initial product catalog
    products = Product.query.filter_by(is_active=True).order_by(Product.name.asc()).all()

    tax_rate = current_app.config.get("TAX_RATE", 0.05)
    max_discount = current_app.config.get("MAX_DISCOUNT_PERCENT", 30.0)

    return render_template(
        "pos/index.html",
        categories=categories,
        products=products,
        tax_rate=tax_rate,
        tax_rate_percent=round(tax_rate * 100, 1),
        max_discount=max_discount,
    )


@pos_bp.route("/api/products")
@login_required
def products_api():
    query_str = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip()

    q = Product.query.filter_by(is_active=True)
    if category and category.lower() != "all":
        q = q.filter(Product.category == category)

    if query_str:
        q = q.filter(
            (Product.name.ilike(f"%{query_str}%")) |
            (Product.sku.ilike(f"%{query_str}%")) |
            (Product.barcode.ilike(f"%{query_str}%"))
        )

    products = q.order_by(Product.name.asc()).limit(60).all()
    return jsonify([p.to_dict() for p in products])


@pos_bp.route("/api/checkout", methods=["POST"])
@login_required
def checkout_api():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid request payload."}), 400

    cart_items = data.get("cart", [])
    if not cart_items:
        return jsonify({"success": False, "error": "Your shopping cart is empty."}), 400

    try:
        discount_pct = float(data.get("discount_percent", 0.0))
    except (ValueError, TypeError):
        discount_pct = 0.0

    try:
        discount_amt = float(data.get("discount_amount", 0.0))
    except (ValueError, TypeError):
        discount_amt = 0.0

    payment_method = data.get("payment_method", "Cash")
    customer_name = data.get("customer_name")
    customer_phone = data.get("customer_phone")
    notes = data.get("notes")

    try:
        sale = BillingService.process_checkout(
            cashier_id=current_user.user_id,
            cart_items_data=cart_items,
            discount_percent=discount_pct,
            discount_amount=discount_amt,
            payment_method=payment_method,
            customer_name=customer_name,
            customer_phone=customer_phone,
            notes=notes,
        )

        return jsonify({
            "success": True,
            "sale_id": sale.sale_id,
            "invoice_number": sale.invoice_number,
            "total_amount": round(sale.total_amount, 2),
            "receipt_url": url_for("sales.receipt", sale_id=sale.sale_id),
            "message": f"Sale completed successfully! Invoice #{sale.invoice_number}",
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal checkout error: {str(e)}"}), 500
