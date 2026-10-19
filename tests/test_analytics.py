from datetime import date
from models.product import Product
from services.billing_service import BillingService
from services.analytics_service import AnalyticsService


def test_empty_period_analytics(app):
    """Test analytics service returns clean zeroed metrics for an empty database/period."""
    with app.app_context():
        kpis = AnalyticsService.get_kpis(range_key="today")
        assert kpis["total_revenue"] == 0.0
        assert kpis["total_bills"] == 0
        assert kpis["average_bill_value"] == 0.0

        trend = AnalyticsService.get_sales_trend(range_key="last_7_days")
        assert len(trend["dates"]) == 7
        assert all(rev == 0.0 for rev in trend["revenue"])

        top = AnalyticsService.get_top_products(range_key="today")
        assert top == []


def test_analytics_with_sales_data(app):
    """Test analytics calculations after processing real sales."""
    with app.app_context():
        p1 = Product.query.filter_by(sku="TEST-SKU-001").first()
        p2 = Product.query.filter_by(sku="TEST-SKU-002").first()

        # Checkout sale 1
        BillingService.process_checkout(
            cashier_id=1,
            cart_items_data=[{"product_id": p1.product_id, "quantity": 3}],  # 300
        )
        # Checkout sale 2
        BillingService.process_checkout(
            cashier_id=1,
            cart_items_data=[{"product_id": p2.product_id, "quantity": 2}],  # 100
        )

        kpis = AnalyticsService.get_kpis(range_key="today")
        assert kpis["total_bills"] == 2
        # Total revenue: (300 + 5% tax = 315) + (100 + 5% tax = 105) = 420.0
        assert kpis["total_revenue"] == 420.0
        assert kpis["average_bill_value"] == 210.0

        top_prods = AnalyticsService.get_top_products(range_key="today", limit=5)
        assert len(top_prods) == 2
        assert top_prods[0]["name"] == "Organic Apples"
        assert top_prods[0]["units_sold"] == 3

        cat_perf = AnalyticsService.get_category_performance(range_key="today")
        assert len(cat_perf) == 2
        cat_names = [c["category"] for c in cat_perf]
        assert "Fruits" in cat_names
        assert "Dairy" in cat_names
