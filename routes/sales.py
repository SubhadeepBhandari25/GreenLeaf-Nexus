from datetime import date
from flask import Blueprint, render_template, request, abort, current_app
from flask_login import login_required, current_user
from database import db
from models.sale import Sale
from models.sale_item import SaleItem
from models.user import User

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    search_invoice = request.args.get("invoice", "").strip()
    cashier_id = request.args.get("cashier_id", type=int)
    payment_method = request.args.get("payment_method", "").strip()
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    min_total = request.args.get("min_total", type=float)
    max_total = request.args.get("max_total", type=float)

    query = Sale.query.filter_by(transaction_status="completed")

    # Cashier permission isolation
    if not current_user.is_admin:
        query = query.filter(Sale.user_id == current_user.user_id)
    elif cashier_id:
        query = query.filter(Sale.user_id == cashier_id)

    if search_invoice:
        query = query.filter(Sale.invoice_number.ilike(f"%{search_invoice}%"))

    if payment_method:
        query = query.filter(Sale.payment_method == payment_method)

    if start_date_str:
        try:
            start_d = date.fromisoformat(start_date_str)
            query = query.filter(Sale.sale_date >= start_d)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_d = date.fromisoformat(end_date_str)
            query = query.filter(Sale.sale_date <= end_d)
        except ValueError:
            pass

    if min_total is not None:
        query = query.filter(Sale.total_amount >= min_total)

    if max_total is not None:
        query = query.filter(Sale.total_amount <= max_total)

    pagination = query.order_by(Sale.sale_date.desc(), Sale.sale_time.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    sales = pagination.items

    cashiers = User.query.filter_by(is_active=True).all() if current_user.is_admin else []

    return render_template(
        "sales/index.html",
        sales=sales,
        pagination=pagination,
        cashiers=cashiers,
        search_invoice=search_invoice,
        cashier_id=cashier_id,
        payment_method=payment_method,
        start_date=start_date_str,
        end_date=end_date_str,
        min_total=min_total,
        max_total=max_total,
    )


@sales_bp.route("/<int:sale_id>")
@login_required
def details(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    if not current_user.is_admin and sale.user_id != current_user.user_id:
        abort(403)
    return render_template("sales/details.html", sale=sale)


@sales_bp.route("/<int:sale_id>/receipt")
@login_required
def receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    if not current_user.is_admin and sale.user_id != current_user.user_id:
        abort(403)

    return render_template(
        "sales/receipt.html",
        sale=sale,
        store_name=current_app.config.get("STORE_NAME"),
        store_tagline=current_app.config.get("STORE_TAGLINE"),
        store_address=current_app.config.get("STORE_ADDRESS"),
        store_phone=current_app.config.get("STORE_PHONE"),
        store_email=current_app.config.get("STORE_EMAIL"),
        currency=current_app.config.get("CURRENCY_SYMBOL"),
    )
