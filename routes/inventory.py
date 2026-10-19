from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database import db
from models.product import Product
from models.inventory_movement import InventoryMovement
from routes.auth import admin_required
from services.inventory_service import InventoryService

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/")
@login_required
@admin_required
def index():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("filter", "all").strip()  # all, low_stock, expiring_soon, expired

    query = Product.query.filter_by(is_active=True)

    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.sku.ilike(f"%{search}%"))
        )

    today = date.today()
    if status_filter == "low_stock":
        query = query.filter(Product.stock_qty <= Product.reorder_level)
    elif status_filter == "expiring_soon":
        query = query.filter(
            Product.expiry_date.isnot(None),
            Product.expiry_date >= today,
            Product.expiry_date <= today + timedelta(days=15),
        )
    elif status_filter == "expired":
        query = query.filter(
            Product.expiry_date.isnot(None),
            Product.expiry_date < today,
        )

    pagination = query.order_by(Product.stock_qty.asc()).paginate(page=page, per_page=15, error_out=False)
    products = pagination.items

    summary = InventoryService.get_inventory_summary()

    return render_template(
        "inventory/index.html",
        products=products,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        summary=summary,
    )


@inventory_bp.route("/restock", methods=["POST"])
@login_required
@admin_required
def restock():
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", type=int)
    reference = request.form.get("reference", "").strip()
    notes = request.form.get("notes", "").strip()

    if not product_id or not quantity or quantity <= 0:
        flash("Invalid restock quantity. Must be at least 1 unit.", "danger")
        return redirect(url_for("inventory.index"))

    try:
        product = InventoryService.restock_product(
            product_id=product_id,
            quantity_added=quantity,
            user_id=current_user.user_id,
            reference=reference,
            notes=notes,
        )
        flash(f"Successfully added {quantity} units to '{product.name}'. New stock: {product.stock_qty}.", "success")
    except Exception as e:
        flash(f"Restock error: {str(e)}", "danger")

    return redirect(request.referrer or url_for("inventory.index"))


@inventory_bp.route("/adjust", methods=["POST"])
@login_required
@admin_required
def adjust():
    product_id = request.form.get("product_id", type=int)
    new_quantity = request.form.get("new_quantity", type=int)
    reason = request.form.get("reason", "Physical Stock Count").strip()
    notes = request.form.get("notes", "").strip()

    if product_id is None or new_quantity is None or new_quantity < 0:
        flash("Invalid stock adjustment count. Must be 0 or greater.", "danger")
        return redirect(url_for("inventory.index"))

    try:
        product = InventoryService.adjust_stock(
            product_id=product_id,
            new_quantity=new_quantity,
            user_id=current_user.user_id,
            reason=reason,
            notes=notes,
        )
        flash(f"Stock for '{product.name}' adjusted to {product.stock_qty} units.", "success")
    except Exception as e:
        flash(f"Adjustment error: {str(e)}", "danger")

    return redirect(request.referrer or url_for("inventory.index"))


@inventory_bp.route("/movements")
@login_required
@admin_required
def movements():
    page = request.args.get("page", 1, type=int)
    movement_type = request.args.get("type", "").strip()
    search = request.args.get("search", "").strip()

    query = InventoryMovement.query.join(Product, InventoryMovement.product_id == Product.product_id)

    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)

    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.sku.ilike(f"%{search}%")) |
            (InventoryMovement.reference.ilike(f"%{search}%"))
        )

    pagination = query.order_by(InventoryMovement.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    movements_list = pagination.items

    return render_template(
        "inventory/movements.html",
        movements=movements_list,
        pagination=pagination,
        movement_type=movement_type,
        search=search,
    )
