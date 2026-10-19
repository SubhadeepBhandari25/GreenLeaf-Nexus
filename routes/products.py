from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import db
from models.product import Product
from models.supplier import Supplier
from models.inventory_movement import InventoryMovement
from routes.auth import admin_required
from services.csv_service import CsvService
from services.food_api_service import FoodApiService

products_bp = Blueprint("products", __name__, url_prefix="/products")


@products_bp.route("/")
@login_required
@admin_required
def index():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    stock_filter = request.args.get("stock_status", "").strip()
    status_filter = request.args.get("status", "active").strip()
    sort_by = request.args.get("sort", "name").strip()
    order = request.args.get("order", "asc").strip()

    query = Product.query

    # Status filter (active/inactive/all)
    if status_filter == "active":
        query = query.filter(Product.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(Product.is_active == False)

    # Search filter
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.sku.ilike(f"%{search}%")) |
            (Product.barcode.ilike(f"%{search}%"))
        )

    # Category filter
    if category and category.lower() != "all":
        query = query.filter(Product.category == category)

    # Stock status filter
    if stock_filter == "low_stock":
        query = query.filter(Product.stock_qty <= Product.reorder_level, Product.stock_qty > 0)
    elif stock_filter == "out_of_stock":
        query = query.filter(Product.stock_qty == 0)
    elif stock_filter == "in_stock":
        query = query.filter(Product.stock_qty > Product.reorder_level)

    # Sorting
    sort_column = Product.name
    if sort_by == "sku":
        sort_column = Product.sku
    elif sort_by == "price":
        sort_column = Product.unit_price
    elif sort_by == "stock":
        sort_column = Product.stock_qty
    elif sort_by == "expiry":
        sort_column = Product.expiry_date

    if order == "desc":
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    products = pagination.items

    # Distinct categories for filter dropdown
    categories = [
        c[0] for c in db.session.query(Product.category).distinct().order_by(Product.category.asc()).all()
    ]

    return render_template(
        "products/index.html",
        products=products,
        pagination=pagination,
        categories=categories,
        search=search,
        selected_category=category,
        stock_filter=stock_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        order=order,
    )


@products_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()

    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        barcode = request.form.get("barcode", "").strip()
        image_path = request.form.get("image_path", "").strip()

        unit_price_str = request.form.get("unit_price", "0")
        cost_price_str = request.form.get("cost_price", "0")
        stock_qty_str = request.form.get("stock_qty", "0")
        reorder_level_str = request.form.get("reorder_level", "10")
        expiry_date_str = request.form.get("expiry_date", "").strip()
        supplier_id_str = request.form.get("supplier_id", "").strip()

        errors = []
        if not sku:
            errors.append("SKU is required.")
        elif Product.query.filter_by(sku=sku).first():
            errors.append(f"SKU '{sku}' already exists.")

        if not name:
            errors.append("Product name is required.")
        if not category:
            errors.append("Category is required.")

        try:
            unit_price = float(unit_price_str)
            if unit_price < 0:
                errors.append("Unit price cannot be negative.")
        except ValueError:
            errors.append("Invalid unit price format.")

        try:
            cost_price = float(cost_price_str) if cost_price_str else 0.0
            if cost_price < 0:
                errors.append("Cost price cannot be negative.")
        except ValueError:
            errors.append("Invalid cost price format.")

        try:
            stock_qty = int(stock_qty_str)
            if stock_qty < 0:
                errors.append("Stock quantity cannot be negative.")
        except ValueError:
            errors.append("Invalid stock quantity.")

        try:
            reorder_level = int(reorder_level_str)
            if reorder_level < 0:
                errors.append("Reorder level cannot be negative.")
        except ValueError:
            errors.append("Invalid reorder level.")

        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Invalid expiry date format. Expected YYYY-MM-DD.")

        supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "products/form.html",
                is_edit=False,
                product=request.form,
                suppliers=suppliers,
            )

        # Create Product
        product = Product(
            sku=sku,
            barcode=barcode or None,
            name=name,
            description=description or None,
            category=category,
            unit_price=unit_price,
            cost_price=cost_price,
            stock_qty=stock_qty,
            reorder_level=reorder_level,
            expiry_date=expiry_date,
            supplier_id=supplier_id,
            image_path=image_path or None,
            is_active=True,
        )
        db.session.add(product)
        db.session.flush()

        # Log initial movement
        if stock_qty > 0:
            movement = InventoryMovement(
                product_id=product.product_id,
                user_id=current_user.user_id,
                movement_type="initial",
                quantity_change=stock_qty,
                previous_stock=0,
                resulting_stock=stock_qty,
                reference="Opening Stock",
                notes="Initial stock recorded at product creation",
            )
            db.session.add(movement)

        db.session.commit()
        flash(f"Product '{product.name}' created successfully!", "success")
        return redirect(url_for("products.index"))

    return render_template("products/form.html", is_edit=False, product={}, suppliers=suppliers)


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(product_id):
    product = Product.query.get_or_404(product_id)
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()

    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        barcode = request.form.get("barcode", "").strip()
        image_path = request.form.get("image_path", "").strip()

        unit_price_str = request.form.get("unit_price", "0")
        cost_price_str = request.form.get("cost_price", "0")
        reorder_level_str = request.form.get("reorder_level", "10")
        expiry_date_str = request.form.get("expiry_date", "").strip()
        supplier_id_str = request.form.get("supplier_id", "").strip()

        errors = []
        if not sku:
            errors.append("SKU is required.")
        else:
            existing = Product.query.filter(Product.sku == sku, Product.product_id != product_id).first()
            if existing:
                errors.append(f"SKU '{sku}' is already in use by another product.")

        if not name:
            errors.append("Product name is required.")
        if not category:
            errors.append("Category is required.")

        try:
            unit_price = float(unit_price_str)
            if unit_price < 0:
                errors.append("Unit price cannot be negative.")
        except ValueError:
            errors.append("Invalid unit price format.")

        try:
            cost_price = float(cost_price_str) if cost_price_str else 0.0
            if cost_price < 0:
                errors.append("Cost price cannot be negative.")
        except ValueError:
            errors.append("Invalid cost price format.")

        try:
            reorder_level = int(reorder_level_str)
            if reorder_level < 0:
                errors.append("Reorder level cannot be negative.")
        except ValueError:
            errors.append("Invalid reorder level.")

        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Invalid expiry date format. Expected YYYY-MM-DD.")

        supplier_id = int(supplier_id_str) if supplier_id_str and supplier_id_str.isdigit() else None

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "products/form.html",
                is_edit=True,
                product=product,
                suppliers=suppliers,
            )

        product.sku = sku
        product.barcode = barcode or None
        product.name = name
        product.description = description or None
        product.category = category
        product.unit_price = unit_price
        product.cost_price = cost_price
        product.reorder_level = reorder_level
        product.expiry_date = expiry_date
        product.supplier_id = supplier_id
        product.image_path = image_path or None

        db.session.commit()
        flash(f"Product '{product.name}' updated successfully!", "success")
        return redirect(url_for("products.index"))

    return render_template("products/form.html", is_edit=True, product=product, suppliers=suppliers)


@products_bp.route("/<int:product_id>")
@login_required
@admin_required
def details(product_id):
    product = Product.query.get_or_404(product_id)
    recent_movements = product.movements.order_by(InventoryMovement.created_at.desc()).limit(10).all()
    return render_template("products/details.html", product=product, movements=recent_movements)


@products_bp.route("/<int:product_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_status(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    status_str = "activated" if product.is_active else "deactivated"
    flash(f"Product '{product.name}' has been {status_str}.", "info")
    return redirect(request.referrer or url_for("products.index"))


@products_bp.route("/import", methods=["POST"])
@login_required
@admin_required
def import_csv():
    if "file" not in request.files:
        flash("No file part in the request.", "warning")
        return redirect(url_for("products.index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "warning")
        return redirect(url_for("products.index"))

    if not file.filename.endswith(".csv"):
        flash("Please upload a valid CSV file (.csv).", "danger")
        return redirect(url_for("products.index"))

    result = CsvService.import_products_csv(file.stream, user_id=current_user.user_id)
    if result["imported"] > 0:
        flash(f"Successfully imported {result['imported']} products!", "success")
    if result["errors"]:
        for err in result["errors"][:5]:  # show top 5 errors to avoid UI overflow
            flash(f"Row {err['row']}: {err['error']}", "warning")
        if len(result["errors"]) > 5:
            flash(f"...and {len(result['errors']) - 5} more errors.", "warning")

    return redirect(url_for("products.index"))


@products_bp.route("/api/openfoodfacts/<barcode>")
@login_required
def api_food_lookup(barcode):
    """Live API proxy to Open Food Facts database with pre-indexed cache."""
    data = FoodApiService.lookup_by_barcode(barcode)
    if not data:
        return jsonify({"found": False, "message": "Product not found in Open Food Facts database."}), 404
    return jsonify(data)


@products_bp.route("/api/openfoodfacts/popular")
@login_required
def api_food_popular():
    """Returns curated verified popular items from Open Food Facts API."""
    return jsonify({"items": FoodApiService.POPULAR_API_ITEMS})


@products_bp.route("/import-food-item", methods=["POST"])
@login_required
@admin_required
def import_food_item():
    """One-click import from Open Food Facts into GreenLeaf Grocers catalog."""
    barcode = request.form.get("barcode", "").strip()
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Snacks").strip()
    image_url = request.form.get("image_url", "").strip()
    
    try:
        unit_price = float(request.form.get("unit_price", "49.0"))
    except ValueError:
        unit_price = 49.0

    try:
        cost_price = float(request.form.get("cost_price", "35.0"))
    except ValueError:
        cost_price = 35.0

    try:
        stock_qty = int(request.form.get("stock_qty", "25"))
    except ValueError:
        stock_qty = 25

    if not name or not barcode:
        flash("Barcode and product name are required to import.", "danger")
        return redirect(url_for("products.index"))

    # Check if barcode already exists
    existing = Product.query.filter_by(barcode=barcode).first()
    if existing:
        flash(f"Product with barcode '{barcode}' already exists in catalog: {existing.name}", "info")
        return redirect(url_for("products.details", product_id=existing.product_id))

    # Generate unique SKU
    cat_prefix = category[:3].upper() if len(category) >= 3 else "GEN"
    sku = f"OFF-{cat_prefix}-{barcode[-6:] if len(barcode) >= 6 else barcode}"
    if Product.query.filter_by(sku=sku).first():
        sku = f"OFF-{cat_prefix}-{barcode[-4:]}-{int(datetime.utcnow().timestamp()) % 1000}"

    first_supplier = Supplier.query.first()
    supplier_id = first_supplier.supplier_id if first_supplier else None

    product = Product(
        sku=sku,
        barcode=barcode,
        name=name,
        description=f"Authentic grocery product imported directly from global Open Food Facts API Database.",
        category=category,
        unit_price=unit_price,
        cost_price=cost_price,
        stock_qty=stock_qty,
        reorder_level=10,
        supplier_id=supplier_id,
        image_path=image_url or None,
        is_active=True,
    )
    db.session.add(product)
    db.session.flush()

    if stock_qty > 0:
        movement = InventoryMovement(
            product_id=product.product_id,
            user_id=current_user.user_id,
            movement_type="initial",
            quantity_change=stock_qty,
            previous_stock=0,
            resulting_stock=stock_qty,
            reference="Open Food Facts Import",
            notes=f"Auto-imported product from Open Food Facts DB with barcode {barcode}",
        )
        db.session.add(movement)

    db.session.commit()
    flash(f"Successfully imported '{product.name}' with real product image from Open Food Facts!", "success")
    return redirect(url_for("products.details", product_id=product.product_id))

