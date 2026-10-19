from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from routes.auth import admin_required
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from models.sale import Sale

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
@admin_required
def index():
    range_key = request.args.get("range", "last_30_days")
    custom_start_str = request.args.get("start_date")
    custom_end_str = request.args.get("end_date")

    custom_start = None
    custom_end = None
    if custom_start_str:
        try:
            custom_start = date.fromisoformat(custom_start_str)
        except ValueError:
            pass
    if custom_end_str:
        try:
            custom_end = date.fromisoformat(custom_end_str)
        except ValueError:
            pass

    # Authoritative KPIs
    kpis = AnalyticsService.get_kpis(range_key, custom_start, custom_end)
    trend_data = AnalyticsService.get_sales_trend(range_key, custom_start, custom_end)
    top_products = AnalyticsService.get_top_products(range_key, limit=5, custom_start=custom_start, custom_end=custom_end)
    category_perf = AnalyticsService.get_category_performance(range_key, custom_start=custom_start, custom_end=custom_end)

    # Inventory alerts
    low_stock_list = InventoryService.get_low_stock_products(limit=6)
    near_expiry_list = InventoryService.get_expiry_alerts(days=15)[:6]

    # Recent transactions
    recent_sales = Sale.query.filter_by(transaction_status="completed")\
        .order_by(Sale.sale_date.desc(), Sale.sale_time.desc())\
        .limit(6).all()

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        trend_data=trend_data,
        top_products=top_products,
        category_perf=category_perf,
        low_stock_list=low_stock_list,
        near_expiry_list=near_expiry_list,
        recent_sales=recent_sales,
        current_range=range_key,
    )


@dashboard_bp.route("/api/dashboard/trend")
@login_required
@admin_required
def trend_api():
    range_key = request.args.get("range", "last_30_days")
    trend = AnalyticsService.get_sales_trend(range_key)
    return jsonify(trend)
