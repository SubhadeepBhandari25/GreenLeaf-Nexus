from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import func
from database import db
from models.sale import Sale
from models.sale_item import SaleItem
from models.product import Product
from models.user import User


class AnalyticsService:
    @staticmethod
    def get_date_range_bounds(range_key="last_30_days", custom_start=None, custom_end=None):
        """
        Calculates inclusive date boundaries for filters:
        today, yesterday, last_7_days, last_30_days, this_month, prev_month, custom
        """
        today = date.today()
        if range_key == "today":
            start = today
            end = today
        elif range_key == "yesterday":
            start = today - timedelta(days=1)
            end = today - timedelta(days=1)
        elif range_key == "last_7_days":
            start = today - timedelta(days=6)
            end = today
        elif range_key == "last_30_days":
            start = today - timedelta(days=29)
            end = today
        elif range_key == "this_month":
            start = today.replace(day=1)
            end = today
        elif range_key == "prev_month":
            first_this_month = today.replace(day=1)
            prev_month_end = first_this_month - timedelta(days=1)
            start = prev_month_end.replace(day=1)
            end = prev_month_end
        elif range_key == "custom":
            start = custom_start or (today - timedelta(days=29))
            end = custom_end or today
        else:
            start = today - timedelta(days=29)
            end = today
        return start, end

    @classmethod
    def get_kpis(cls, range_key="last_30_days", custom_start=None, custom_end=None):
        """Calculates top-level KPI metrics and period-over-period delta comparisons."""
        start_date, end_date = cls.get_date_range_bounds(range_key, custom_start, custom_end)
        days_span = (end_date - start_date).days + 1

        # Current period query
        current_sales = Sale.query.filter(
            Sale.transaction_status == "completed",
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        ).all()

        current_rev = sum(s.total_amount for s in current_sales)
        current_bills = len(current_sales)
        current_abv = (current_rev / current_bills) if current_bills > 0 else 0.0

        # Previous period comparison query
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_span - 1)

        prev_sales = Sale.query.filter(
            Sale.transaction_status == "completed",
            Sale.sale_date >= prev_start,
            Sale.sale_date <= prev_end,
        ).all()

        prev_rev = sum(s.total_amount for s in prev_sales)
        prev_bills = len(prev_sales)
        prev_abv = (prev_rev / prev_bills) if prev_bills > 0 else 0.0

        rev_change_pct = (
            round(((current_rev - prev_rev) / prev_rev) * 100, 1) if prev_rev > 0 else None
        )
        bills_change_pct = (
            round(((current_bills - prev_bills) / prev_bills) * 100, 1) if prev_bills > 0 else None
        )

        # Inventory live counts
        active_products = Product.query.filter_by(is_active=True).all()
        total_products = len(active_products)
        low_stock_count = sum(1 for p in active_products if p.is_low_stock)
        
        today = date.today()
        near_expiry_count = sum(
            1 for p in active_products if p.expiry_date and today <= p.expiry_date <= today + timedelta(days=15)
        )

        return {
            "period_label": f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "total_revenue": round(current_rev, 2),
            "total_bills": current_bills,
            "average_bill_value": round(current_abv, 2),
            "revenue_change_pct": rev_change_pct,
            "bills_change_pct": bills_change_pct,
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "near_expiry_count": near_expiry_count,
        }

    @classmethod
    def get_sales_trend(cls, range_key="last_30_days", custom_start=None, custom_end=None):
        """
        Extracts sales data into a Pandas DataFrame and calculates daily revenue and volume.
        """
        start_date, end_date = cls.get_date_range_bounds(range_key, custom_start, custom_end)

        sales = Sale.query.filter(
            Sale.transaction_status == "completed",
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        ).order_by(Sale.sale_date.asc()).all()

        # Build full date index to prevent missing date gaps
        all_dates = pd.date_range(start=start_date, end=end_date, freq="D")
        date_strs = [d.strftime("%Y-%m-%d") for d in all_dates]
        labels = [d.strftime("%d %b") for d in all_dates]

        if not sales:
            return {
                "dates": date_strs,
                "labels": labels,
                "revenue": [0.0] * len(date_strs),
                "bills": [0] * len(date_strs),
                "quantities": [0] * len(date_strs),
            }

        data = []
        for s in sales:
            qty = sum(item.quantity for item in s.items)
            data.append({
                "date": s.sale_date.strftime("%Y-%m-%d"),
                "total_amount": s.total_amount,
                "quantity": qty,
                "bills": 1,
            })

        df = pd.DataFrame(data)
        grouped = df.groupby("date").agg({
            "total_amount": "sum",
            "quantity": "sum",
            "bills": "count",
        }).reindex(date_strs, fill_value=0.0)

        return {
            "dates": date_strs,
            "labels": labels,
            "revenue": [round(float(v), 2) for v in grouped["total_amount"]],
            "bills": [int(v) for v in grouped["bills"]],
            "quantities": [int(v) for v in grouped["quantity"]],
        }

    @classmethod
    def get_monthly_sales(cls, months_back=12):
        """Calculates month-by-month revenue, bill counts, and month-over-month growth."""
        today = date.today()
        # Approx 12 months back
        start_date = (today.replace(day=1) - timedelta(days=365)).replace(day=1)

        sales = Sale.query.filter(
            Sale.transaction_status == "completed",
            Sale.sale_date >= start_date,
        ).all()

        if not sales:
            return []

        data = [{
            "month": s.sale_date.strftime("%Y-%m"),
            "month_label": s.sale_date.strftime("%b %Y"),
            "revenue": s.total_amount,
            "bills": 1,
            "qty": sum(item.quantity for item in s.items),
        } for s in sales]

        df = pd.DataFrame(data)
        grouped = df.groupby(["month", "month_label"], as_index=False).agg({
            "revenue": "sum",
            "bills": "count",
            "qty": "sum",
        }).sort_values("month")

        grouped["prev_rev"] = grouped["revenue"].shift(1)
        grouped["mom_growth"] = np.where(
            grouped["prev_rev"] > 0,
            ((grouped["revenue"] - grouped["prev_rev"]) / grouped["prev_rev"]) * 100,
            0.0
        )

        results = []
        for _, row in grouped.iterrows():
            results.append({
                "month": row["month"],
                "month_label": row["month_label"],
                "revenue": round(float(row["revenue"]), 2),
                "bills": int(row["bills"]),
                "quantity": int(row["qty"]),
                "mom_growth": round(float(row["mom_growth"]), 1) if pd.notnull(row["mom_growth"]) else 0.0,
            })
        return results

    @classmethod
    def get_top_products(cls, range_key="last_30_days", limit=10, custom_start=None, custom_end=None):
        """Identifies top-selling products by quantity and revenue using Pandas."""
        start_date, end_date = cls.get_date_range_bounds(range_key, custom_start, custom_end)

        items = db.session.query(
            SaleItem.product_name_snapshot,
            Product.category,
            Product.image_path,
            SaleItem.quantity,
            SaleItem.line_total,
        ).join(Sale, Sale.sale_id == SaleItem.sale_id)\
         .outerjoin(Product, Product.product_id == SaleItem.product_id)\
         .filter(
             Sale.transaction_status == "completed",
             Sale.sale_date >= start_date,
             Sale.sale_date <= end_date,
         ).all()

        if not items:
            return []

        df = pd.DataFrame(items, columns=["name", "category", "image_path", "quantity", "revenue"])
        df["category"] = df["category"].fillna("General")
        df["image_path"] = df["image_path"].fillna("")

        grouped = df.groupby(["name", "category", "image_path"], as_index=False).agg({
            "quantity": "sum",
            "revenue": "sum",
        }).sort_values(by="revenue", ascending=False).head(limit)

        results = []
        for _, row in grouped.iterrows():
            results.append({
                "name": row["name"],
                "category": row["category"],
                "image_path": str(row["image_path"]) if pd.notnull(row["image_path"]) else "",
                "units_sold": int(row["quantity"]),
                "revenue": round(float(row["revenue"]), 2),
            })
        return results

    @classmethod
    def get_category_performance(cls, range_key="last_30_days", custom_start=None, custom_end=None):
        """Calculates revenue and item share per product category."""
        start_date, end_date = cls.get_date_range_bounds(range_key, custom_start, custom_end)

        items = db.session.query(
            Product.category,
            SaleItem.quantity,
            SaleItem.line_total,
        ).join(SaleItem, Product.product_id == SaleItem.product_id)\
         .join(Sale, Sale.sale_id == SaleItem.sale_id)\
         .filter(
             Sale.transaction_status == "completed",
             Sale.sale_date >= start_date,
             Sale.sale_date <= end_date,
         ).all()

        if not items:
            return []

        df = pd.DataFrame(items, columns=["category", "quantity", "revenue"])
        total_rev = df["revenue"].sum()

        grouped = df.groupby("category", as_index=False).agg({
            "quantity": "sum",
            "revenue": "sum",
        }).sort_values(by="revenue", ascending=False)

        results = []
        for _, row in grouped.iterrows():
            pct = (row["revenue"] / total_rev * 100) if total_rev > 0 else 0.0
            results.append({
                "category": row["category"],
                "units_sold": int(row["quantity"]),
                "revenue": round(float(row["revenue"]), 2),
                "percentage": round(float(pct), 1),
            })
        return results

    @classmethod
    def get_slow_moving_products(cls, days=30, limit=10):
        """Identifies products with zero or minimal sales during the past specified days."""
        cutoff_date = date.today() - timedelta(days=days)

        active_products = Product.query.filter_by(is_active=True).all()
        if not active_products:
            return []

        # Find sales quantities per product in the timeframe
        sold_stats = dict(
            db.session.query(
                SaleItem.product_id,
                func.sum(SaleItem.quantity)
            ).join(Sale, Sale.sale_id == SaleItem.sale_id)\
             .filter(
                 Sale.transaction_status == "completed",
                 Sale.sale_date >= cutoff_date,
             ).group_by(SaleItem.product_id).all()
        )

        data = []
        for p in active_products:
            qty_sold = sold_stats.get(p.product_id, 0)
            if qty_sold == 0:
                status_label = "No Sales"
            elif qty_sold <= 2:
                status_label = "Critically Slow"
            else:
                continue

            data.append({
                "product_id": p.product_id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "stock_qty": p.stock_qty,
                "units_sold_30d": qty_sold,
                "status": status_label,
            })

        # Sort by units sold ascending, then by current stock descending
        data.sort(key=lambda x: (x["units_sold_30d"], -x["stock_qty"]))
        return data[:limit]

    @classmethod
    def get_demand_forecast_7days(cls):
        """
        7-Day Demand Forecasting:
        Uses a 30-day historical moving average of daily sales to predict next 7-day demand,
        then computes suggested replenishment factoring in current stock and safety stock.
        """
        cutoff_date = date.today() - timedelta(days=30)
        active_products = Product.query.filter_by(is_active=True).all()

        sold_items = db.session.query(
            SaleItem.product_id,
            SaleItem.quantity,
            Sale.sale_date,
        ).join(Sale, Sale.sale_id == SaleItem.sale_id)\
         .filter(
             Sale.transaction_status == "completed",
             Sale.sale_date >= cutoff_date,
         ).all()

        if not sold_items:
            # Baseline with fallback
            return [{
                "product_id": p.product_id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "current_stock": p.stock_qty,
                "avg_daily_demand": 0.0,
                "predicted_7d_demand": 0,
                "safety_stock": p.reorder_level,
                "suggested_replenishment": max(0, p.reorder_level - p.stock_qty),
                "confidence": "Low (Insufficient History)",
            } for p in active_products[:15]]

        df = pd.DataFrame(sold_items, columns=["product_id", "quantity", "sale_date"])
        # Calculate daily demand per product over the 30 days
        prod_totals = df.groupby("product_id")["quantity"].sum().to_dict()

        forecasts = []
        for p in active_products:
            total_sold_30d = prod_totals.get(p.product_id, 0)
            avg_daily = total_sold_30d / 30.0
            predicted_7d = int(np.ceil(avg_daily * 7))
            safety_stock = p.reorder_level
            # Suggested replenishment = Predicted demand + Safety Stock - Current Stock
            suggested = max(0, (predicted_7d + safety_stock) - p.stock_qty)

            confidence = "High" if total_sold_30d >= 15 else ("Moderate" if total_sold_30d > 0 else "Low")

            forecasts.append({
                "product_id": p.product_id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "current_stock": p.stock_qty,
                "avg_daily_demand": round(avg_daily, 2),
                "predicted_7d_demand": predicted_7d,
                "safety_stock": safety_stock,
                "suggested_replenishment": suggested,
                "confidence": confidence,
            })

        # Order by highest replenishment need
        forecasts.sort(key=lambda x: -x["suggested_replenishment"])
        return forecasts
