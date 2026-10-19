from datetime import date
from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required
from routes.auth import admin_required
from services.csv_service import CsvService
from services.inventory_service import InventoryService
from services.analytics_service import AnalyticsService

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
@admin_required
def index():
    inventory_summary = InventoryService.get_inventory_summary()
    kpis_30d = AnalyticsService.get_kpis("last_30_days")
    return render_template(
        "reports/index.html",
        inventory_summary=inventory_summary,
        kpis=kpis_30d,
    )


@reports_bp.route("/export/sales")
@login_required
@admin_required
def export_sales():
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            pass

    csv_data = CsvService.export_sales_csv(start_date=start_date, end_date=end_date)
    filename = f"greenleaf_sales_{date.today().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/inventory")
@login_required
@admin_required
def export_inventory():
    filter_type = request.args.get("type", "all")
    if filter_type not in ("all", "low_stock", "expiry_alerts"):
        filter_type = "all"

    csv_data = CsvService.export_inventory_csv(filter_type=filter_type)
    filename = f"greenleaf_inventory_{filter_type}_{date.today().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
