import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from database import db
from models.supplier import Supplier
from routes.auth import admin_required

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


@suppliers_bp.route("/")
@login_required
@admin_required
def index():
    search = request.args.get("search", "").strip()
    query = Supplier.query
    if search:
        query = query.filter(
            (Supplier.name.ilike(f"%{search}%")) |
            (Supplier.email.ilike(f"%{search}%")) |
            (Supplier.phone.ilike(f"%{search}%"))
        )
    suppliers = query.order_by(Supplier.name.asc()).all()
    return render_template("suppliers/index.html", suppliers=suppliers, search=search)


@suppliers_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not name:
            errors.append("Supplier name is required.")
        if email and not EMAIL_REGEX.match(email):
            errors.append("Invalid email format.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("suppliers/form.html", is_edit=False, supplier=request.form)

        supplier = Supplier(
            name=name,
            phone=phone or None,
            email=email or None,
            address=address or None,
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f"Supplier '{supplier.name}' created successfully!", "success")
        return redirect(url_for("suppliers.index"))

    return render_template("suppliers/form.html", is_edit=False, supplier={})


@suppliers_bp.route("/<int:supplier_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not name:
            errors.append("Supplier name is required.")
        if email and not EMAIL_REGEX.match(email):
            errors.append("Invalid email format.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("suppliers/form.html", is_edit=True, supplier=supplier)

        supplier.name = name
        supplier.phone = phone or None
        supplier.email = email or None
        supplier.address = address or None

        db.session.commit()
        flash(f"Supplier '{supplier.name}' updated successfully!", "success")
        return redirect(url_for("suppliers.index"))

    return render_template("suppliers/form.html", is_edit=True, supplier=supplier)


@suppliers_bp.route("/<int:supplier_id>")
@login_required
@admin_required
def details(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    products = supplier.products.filter_by(is_active=True).all()
    
    total_units = sum(p.stock_qty for p in products)
    cost_valuation = sum(p.stock_qty * p.cost_price for p in products)
    retail_valuation = sum(p.stock_qty * p.unit_price for p in products)
    
    return render_template(
        "suppliers/details.html",
        supplier=supplier,
        products=products,
        total_units=total_units,
        cost_valuation=cost_valuation,
        retail_valuation=retail_valuation,
    )


@suppliers_bp.route("/<int:supplier_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    linked_count = supplier.products.count()
    if linked_count > 0:
        flash(
            f"Cannot delete supplier '{supplier.name}' because {linked_count} product line(s) are still linked to it. Please reassign or deactivate those products first.",
            "warning",
        )
        return redirect(url_for("suppliers.details", supplier_id=supplier_id))

    name = supplier.name
    db.session.delete(supplier)
    db.session.commit()
    flash(f"Supplier '{name}' was deleted successfully.", "info")
    return redirect(url_for("suppliers.index"))
