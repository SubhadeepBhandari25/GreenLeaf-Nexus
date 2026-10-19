import random
import uuid
from datetime import datetime, date
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from database import db
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from services.billing_service import BillingService

express_bp = Blueprint("express", __name__, url_prefix="/express")

# Simulated active express delivery fleet & dark stores
DARK_STORES = [
    {
        "id": "DS-04",
        "name": "GreenLeaf Indiranagar Dark Store #04",
        "area": "Indiranagar, Bengaluru",
        "sla_mins": 10,
        "active_riders": 14,
        "fulfillment_rate": "99.2%",
        "avg_pack_time": "1m 45s",
    },
    {
        "id": "DS-07",
        "name": "GreenLeaf Koramangala Hub #07",
        "area": "Koramangala 4th Block, Bengaluru",
        "sla_mins": 12,
        "active_riders": 18,
        "fulfillment_rate": "98.9%",
        "avg_pack_time": "1m 58s",
    },
    {
        "id": "DS-12",
        "name": "GreenLeaf Whitefield Express #12",
        "area": "ITPL Main Road, Whitefield",
        "sla_mins": 15,
        "active_riders": 22,
        "fulfillment_rate": "99.5%",
        "avg_pack_time": "2m 04s",
    },
]

DELIVERY_PARTNERS = [
    {"name": "Vikram Singh", "phone": "+91 98451 22390", "vehicle": "Hero Vida V1 (EV)", "rating": 4.9, "trips": 2840},
    {"name": "Aman Preet", "phone": "+91 97410 88312", "vehicle": "Ather 450X (EV)", "rating": 4.95, "trips": 3410},
    {"name": "Rohan Deshmukh", "phone": "+91 98862 33491", "vehicle": "Ola S1 Pro (EV)", "rating": 4.88, "trips": 1920},
    {"name": "Mohammed Farhan", "phone": "+91 99002 44719", "vehicle": "TVS iQube (EV)", "rating": 4.92, "trips": 2150},
]

DARK_STORE_PACKERS = [
    {"name": "Rajesh Kumar", "station": "Pack Station #02", "speed": "1m 32s avg"},
    {"name": "Sunil Verma", "station": "Pack Station #04", "speed": "1m 41s avg"},
    {"name": "Pooja Hegde", "station": "Cold Storage Bay #01", "speed": "1m 28s avg"},
]


@express_bp.route("/")
def store():
    """Blinkit-style 10-minute quick-commerce storefront."""
    query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()

    # Fetch active products with stock > 0 prioritised
    prod_query = Product.query.filter_by(is_active=True)

    if query:
        search_filter = f"%{query}%"
        prod_query = prod_query.filter(
            (Product.name.ilike(search_filter))
            | (Product.category.ilike(search_filter))
            | (Product.sku.ilike(search_filter))
        )

    if selected_category and selected_category != "All":
        prod_query = prod_query.filter(Product.category == selected_category)

    products = prod_query.order_by(Product.stock_qty.desc(), Product.name.asc()).all()

    # Get distinct categories with counts
    all_active = Product.query.filter_by(is_active=True).all()
    categories_dict = {}
    for p in all_active:
        categories_dict[p.category] = categories_dict.get(p.category, 0) + 1

    category_list = [{"name": cat, "count": count} for cat, count in sorted(categories_dict.items())]

    # Pre-select dark store
    store_id = request.args.get("store_id", "DS-04")
    active_store = next((s for s in DARK_STORES if s["id"] == store_id), DARK_STORES[0])

    return render_template(
        "express/store.html",
        products=products,
        categories=category_list,
        selected_category=selected_category,
        query=query,
        dark_stores=DARK_STORES,
        active_store=active_store,
    )


@express_bp.route("/checkout", methods=["POST"])
def express_checkout():
    """
    Process instant 10-minute quick commerce checkout.
    Uses authoritative BillingService.process_checkout to deduct stock and create sale.
    """
    data = request.get_json()
    if not data or not data.get("items"):
        return jsonify({"success": False, "error": "Cart is empty."}), 400

    items_data = data.get("items")
    customer_name = data.get("customer_name", "Valued Shopper").strip() or "Valued Shopper"
    customer_phone = data.get("customer_phone", "").strip() or "9876543210"
    delivery_address = data.get("address", "Flat 402, Green Glen Layout, Indiranagar").strip()
    payment_method = data.get("payment_method", "UPI").strip()
    tip_amount = float(data.get("tip_amount", 0.0) or 0.0)

    # Resolve cashier/user id
    user_id = current_user.user_id if current_user.is_authenticated else 1

    partner = random.choice(DELIVERY_PARTNERS)
    packer = random.choice(DARK_STORE_PACKERS)

    notes = (
        f"[Blinkit 10-Min Express] Address: {delivery_address} | "
        f"Packer: {packer['name']} ({packer['station']}) | "
        f"Rider: {partner['name']} ({partner['vehicle']}) | "
        f"Tip: ₹{tip_amount:.2f}"
    )

    try:
        sale = BillingService.process_checkout(
            cashier_id=user_id,
            cart_items_data=items_data,
            payment_method=payment_method,
            customer_name=customer_name,
            customer_phone=customer_phone,
            discount_percent=0.0,
            discount_amount=0.0,
            notes=notes,
        )

        return jsonify({
            "success": True,
            "invoice_number": sale.invoice_number,
            "sale_id": sale.sale_id,
            "total_amount": sale.total_amount,
            "rider": partner,
            "packer": packer,
            "eta_minutes": 10,
            "redirect_url": url_for("express.track_order", invoice_number=sale.invoice_number),
        })

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Checkout failed: {str(e)}"}), 500


@express_bp.route("/track/<invoice_number>")
def track_order(invoice_number):
    """Blinkit real-time 10-minute order tracking and live delivery progression screen."""
    sale = Sale.query.filter_by(invoice_number=invoice_number).first_or_404()

    # Parse rider and packer from notes if available
    rider_info = DELIVERY_PARTNERS[0]
    packer_info = DARK_STORE_PACKERS[0]
    for p in DELIVERY_PARTNERS:
        if p["name"] in (sale.notes or ""):
            rider_info = p
            break
    for pk in DARK_STORE_PACKERS:
        if pk["name"] in (sale.notes or ""):
            packer_info = pk
            break

    return render_template(
        "express/track.html",
        sale=sale,
        rider=rider_info,
        packer=packer_info,
        dark_store=DARK_STORES[0],
    )


@express_bp.route("/picker")
def picker_console():
    """Dark Store Picker Console: Live order queue with 2-minute SLA packing clock."""
    # Fetch recent express sales or today's completed sales
    recent_orders = Sale.query.filter(
        Sale.notes.ilike("%Blinkit%") | Sale.notes.ilike("%Express%")
    ).order_by(Sale.created_at.desc()).limit(15).all()

    # If few express orders, fetch general recent sales
    if len(recent_orders) < 5:
        recent_orders = Sale.query.order_by(Sale.created_at.desc()).limit(10).all()

    return render_template(
        "express/picker.html",
        orders=recent_orders,
        dark_store=DARK_STORES[0],
        packers=DARK_STORE_PACKERS,
    )


@express_bp.route("/api/picker/dispatch/<int:sale_id>", methods=["POST"])
def dispatch_order(sale_id):
    """Mark an order as packed and dispatched to rider in dark store."""
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify({"success": False, "error": "Order not found."}), 404

    packer_name = request.json.get("packer", DARK_STORE_PACKERS[0]["name"]) if request.is_json else DARK_STORE_PACKERS[0]["name"]
    rider_name = request.json.get("rider", DELIVERY_PARTNERS[0]["name"]) if request.is_json else DELIVERY_PARTNERS[0]["name"]

    time_str = datetime.now().strftime("%H:%M:%S")
    sale.notes = (sale.notes or "") + f" | [DISPATCHED {time_str} by {packer_name} to {rider_name}]"
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Order #{sale.invoice_number} dispatched to {rider_name} successfully!",
        "invoice_number": sale.invoice_number,
    })
