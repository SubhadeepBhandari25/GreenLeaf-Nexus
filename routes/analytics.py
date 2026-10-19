from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from routes.auth import admin_required
from services.analytics_service import AnalyticsService

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
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

    kpis = AnalyticsService.get_kpis(range_key, custom_start, custom_end)
    sales_trend = AnalyticsService.get_sales_trend(range_key, custom_start, custom_end)
    monthly_sales = AnalyticsService.get_monthly_sales(months_back=12)
    top_products = AnalyticsService.get_top_products(range_key, limit=10, custom_start=custom_start, custom_end=custom_end)
    category_perf = AnalyticsService.get_category_performance(range_key, custom_start=custom_start, custom_end=custom_end)
    slow_movers = AnalyticsService.get_slow_moving_products(days=30, limit=10)
    forecasts = AnalyticsService.get_demand_forecast_7days()[:10]

    return render_template(
        "analytics/index.html",
        kpis=kpis,
        sales_trend=sales_trend,
        monthly_sales=monthly_sales,
        top_products=top_products,
        category_perf=category_perf,
        slow_movers=slow_movers,
        forecasts=forecasts,
        current_range=range_key,
        custom_start=custom_start_str or "",
        custom_end=custom_end_str or "",
    )


@analytics_bp.route("/api/chart-data")
@login_required
@admin_required
def chart_data_api():
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

    trend = AnalyticsService.get_sales_trend(range_key, custom_start, custom_end)
    category = AnalyticsService.get_category_performance(range_key, custom_start, custom_end)
    top_products = AnalyticsService.get_top_products(range_key, limit=10, custom_start=custom_start, custom_end=custom_end)
    monthly = AnalyticsService.get_monthly_sales(months_back=12)

    return jsonify({
        "trend": trend,
        "category": category,
        "top_products": top_products,
        "monthly": monthly,
    })
