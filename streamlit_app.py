import os
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup workspace paths
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure runtime directories exist
(BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "exports").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "static" / "uploads").mkdir(parents=True, exist_ok=True)

from app import create_app
from database import db
from models.user import User
from models.supplier import Supplier
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from models.inventory_movement import InventoryMovement
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from services.billing_service import BillingService
from seed_data import seed_database


# ---------------------------------------------------------
# Streamlit Page Config & Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="GreenLeaf Nexus | Inventory & Analytics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for GreenLeaf Grocers brand aesthetics
st.markdown(
    """
    <style>
    /* Brand Theme Colors */
    :root {
        --gl-primary: #16865b;
        --gl-primary-dark: #0f593c;
        --gl-accent: #22c55e;
        --gl-bg: #f8fafc;
        --gl-surface: #ffffff;
        --gl-border: #e2e8f0;
    }
    
    /* Header Container */
    .gln-header {
        background: linear-gradient(135deg, #16865b 0%, #0f593c 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 14px rgba(22, 134, 91, 0.2);
    }
    .gln-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff !important;
    }
    .gln-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
        color: #e2f8ec !important;
    }

    /* KPI Metric Cards */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1rem 1.25rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        border-color: #cbd5e1;
    }

    /* Badges */
    .badge-success {
        background-color: #dcfce7;
        color: #15803d;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-warning {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-danger {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-info {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* POS Receipt Box */
    .thermal-receipt {
        background: #fffef8;
        border: 1px dashed #94a3b8;
        border-radius: 8px;
        padding: 1.5rem;
        font-family: 'Courier New', Courier, monospace;
        color: #1e293b;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Singleton Flask Application & Database Context
# ---------------------------------------------------------
@st.cache_resource
def get_app():
    flask_app = create_app("development")
    return flask_app


flask_app = get_app()


def init_database_if_needed():
    """Initializes tables and seeds initial demo data if database is empty."""
    with flask_app.app_context():
        db.create_all()
        try:
            prod_count = Product.query.count()
        except Exception:
            prod_count = 0
            db.session.rollback()

        if prod_count == 0:
            with st.spinner("📦 First launch detected: Seeding realistic demo catalog, sales history, and inventory ledgers..."):
                seed_database(num_sales=260, random_seed=42, app=flask_app, drop_existing=False)
            st.toast("✅ Demo database successfully populated!", icon="🌿")


# ---------------------------------------------------------
# Helper Formatting Utilities
# ---------------------------------------------------------
def fmt_currency(val):
    try:
        return f"₹{float(val):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


# ---------------------------------------------------------
# Page 1: 📊 Executive Dashboard
# ---------------------------------------------------------
def render_dashboard():
    st.markdown(
        """
        <div class="gln-header">
            <h1>🌿 GreenLeaf Nexus Dashboard</h1>
            <p>Fresh Stock. Smart Decisions. Real-Time Supermarket Intelligence & POS Surveillance.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with flask_app.app_context():
        # Date filter controls
        col_filter, col_spacer = st.columns([3, 5])
        with col_filter:
            date_filter = st.selectbox(
                "Filter Time Window",
                options=["last_30_days", "last_7_days", "today", "yesterday", "this_month", "prev_month"],
                format_func=lambda x: {
                    "last_30_days": "Last 30 Days",
                    "last_7_days": "Last 7 Days",
                    "today": "Today",
                    "yesterday": "Yesterday",
                    "this_month": "This Month (MTD)",
                    "prev_month": "Previous Month",
                }.get(x, x),
                index=0,
            )

        kpis = AnalyticsService.get_kpis(range_key=date_filter)
        inv_summary = InventoryService.get_inventory_summary()

        # Alert banners if low stock or expiring products exist
        if kpis["low_stock_count"] > 0 or kpis["near_expiry_count"] > 0:
            c1, c2 = st.columns(2)
            with c1:
                if kpis["low_stock_count"] > 0:
                    st.warning(
                        f"⚠️ **Low Stock Alert**: {kpis['low_stock_count']} products are at or below reorder threshold. Check Inventory tab to reorder.",
                        icon="⚠️",
                    )
            with c2:
                if kpis["near_expiry_count"] > 0:
                    st.error(
                        f"🚨 **Expiry Warning**: {kpis['near_expiry_count']} products expire within 15 days! Review Expiry Surveillance.",
                        icon="🚨",
                    )

        # Primary KPI Metrics Cards
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            rev_delta = f"{kpis['revenue_change_pct']:+.1f}% vs prior" if kpis.get("revenue_change_pct") is not None else None
            st.metric("Total Gross Revenue", fmt_currency(kpis["total_revenue"]), delta=rev_delta)
        with m2:
            st.metric("Total Completed Bills", f"{kpis['total_bills']:,}", delta=f"{kpis['bills_change_pct']:+.1f}%" if kpis.get("bills_change_pct") is not None else None)
        with m3:
            st.metric("Average Bill Value (ABV)", fmt_currency(kpis["average_bill_value"]))
        with m4:
            st.metric("Active Catalog SKUs", f"{kpis['total_products']:,}")
        with m5:
            st.metric("Retail Stock Valuation", fmt_currency(inv_summary["retail_value"]))

        st.markdown("---")

        # Visual Trajectories: Sales Trend & Category Share
        chart_col1, chart_col2 = st.columns([5, 4])

        with chart_col1:
            st.subheader("📈 Daily Gross Revenue Trajectory")
            trend_data = AnalyticsService.get_sales_trend(range_key=date_filter)
            if trend_data["revenue"] and sum(trend_data["revenue"]) > 0:
                df_trend = pd.DataFrame({
                    "Date": trend_data["labels"],
                    "Revenue (₹)": trend_data["revenue"],
                    "Bills Count": trend_data["bills"],
                })
                fig_trend = px.area(
                    df_trend,
                    x="Date",
                    y="Revenue (₹)",
                    title=f"Revenue Trajectory ({kpis['period_label']})",
                    color_discrete_sequence=["#16865b"],
                )
                fig_trend.update_layout(
                    hovermode="x unified",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No completed sales transactions recorded for this selected time window.")

        with chart_col2:
            st.subheader("🍩 Category Revenue Breakdown")
            cat_data = AnalyticsService.get_category_performance(range_key=date_filter)
            if cat_data:
                df_cat = pd.DataFrame(cat_data)
                fig_cat = px.pie(
                    df_cat,
                    names="category",
                    values="revenue",
                    title="Revenue by Product Category",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig_cat.update_layout(
                    margin=dict(l=10, r=10, t=40, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                )
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No category sales recorded in this interval.")

        st.markdown("---")

        # Recent Transactions
        st.subheader("🧾 Recent Sales Transactions")
        recent_sales = Sale.query.filter_by(transaction_status="completed").order_by(Sale.sale_date.desc(), Sale.sale_id.desc()).limit(8).all()
        if recent_sales:
            table_data = []
            for s in recent_sales:
                cashier_name = s.cashier.full_name if s.cashier else "Cashier"
                table_data.append({
                    "Receipt Number": s.receipt_number,
                    "Sale Date": s.sale_date.strftime("%d %b %Y"),
                    "Customer": s.customer_name or "Walk-in Guest",
                    "Cashier": cashier_name,
                    "Items Count": sum(item.quantity for item in s.items),
                    "Payment Mode": s.payment_method,
                    "Total Amount": fmt_currency(s.total_amount),
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
        else:
            st.info("No sales transactions logged yet.")


# ---------------------------------------------------------
# Page 2: 📦 Inventory Surveillance & Restock
# ---------------------------------------------------------
def render_inventory():
    st.title("📦 Inventory Surveillance & Movement Ledger")
    st.caption("Live stock surveillance, expiry tracking, restock management, and movement audits.")

    with flask_app.app_context():
        summary = InventoryService.get_inventory_summary()

        # Valuation Metric Row
        v1, v2, v3, v4 = st.columns(4)
        with v1:
            st.metric("Total Tracked SKUs", f"{summary['total_products']:,}")
        with v2:
            st.metric("Total Physical Units", f"{summary['total_units']:,}")
        with v3:
            st.metric("Retail Inventory Value", fmt_currency(summary["retail_value"]))
        with v4:
            st.metric("Unrealized Profit Margin", fmt_currency(summary["potential_profit"]))

        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Master Stock Ledger",
            "⚠️ Expiry Surveillance Tracker",
            "⚡ Quick Restock & Adjustments",
            "📜 Movement Audit Log",
        ])

        # TAB 1: Master Inventory
        with tab1:
            col_search, col_cat, col_status = st.columns([4, 3, 3])
            with col_search:
                search_q = st.text_input("🔍 Search by SKU, Barcode, or Name", placeholder="e.g. Haldiram, APL, 8901...")
            with col_cat:
                categories = ["All"] + [c[0] for c in db.session.query(Product.category).distinct().all()]
                selected_cat = st.selectbox("Filter Category", categories)
            with col_status:
                stock_filter = st.selectbox("Stock Status", ["All Items", "Low Stock Only", "Out of Stock", "Healthy Stock"])

            query = Product.query.filter(Product.is_active == True)
            if selected_cat != "All":
                query = query.filter(Product.category == selected_cat)
            if search_q:
                q_term = f"%{search_q.strip()}%"
                query = query.filter(
                    (Product.name.ilike(q_term)) | (Product.sku.ilike(q_term)) | (Product.barcode.ilike(q_term))
                )

            products = query.order_by(Product.stock_qty.asc()).all()

            # Filter by stock status in memory
            if stock_filter == "Low Stock Only":
                products = [p for p in products if p.is_low_stock and p.stock_qty > 0]
            elif stock_filter == "Out of Stock":
                products = [p for p in products if p.stock_qty <= 0]
            elif stock_filter == "Healthy Stock":
                products = [p for p in products if p.stock_qty > p.reorder_level]

            if products:
                items_data = []
                for p in products:
                    status_text = "🟢 In Stock"
                    if p.stock_qty <= 0:
                        status_text = "🔴 Out of Stock"
                    elif p.is_low_stock:
                        status_text = f"🟡 Low Stock (≤ {p.reorder_level})"

                    items_data.append({
                        "SKU": p.sku,
                        "Product Name": p.name,
                        "Category": p.category,
                        "In Stock": p.stock_qty,
                        "Reorder Level": p.reorder_level,
                        "Retail Price": fmt_currency(p.unit_price),
                        "Cost Price": fmt_currency(p.cost_price),
                        "Expiry Date": p.expiry_date.strftime("%d %b %Y") if p.expiry_date else "N/A",
                        "Status": status_text,
                    })
                st.dataframe(pd.DataFrame(items_data), use_container_width=True, hide_index=True)
            else:
                st.info("No matching products found for the selected criteria.")

        # TAB 2: Expiry Surveillance
        with tab2:
            st.subheader("🚨 Expiry Surveillance Watchlist")
            st.caption("Identifies expired SKUs and perishable items expiring within the next 15 days.")

            expiry_threshold = st.slider("Expiry Warning Horizon (Days)", min_value=1, max_value=60, value=15)
            expiring_prods = InventoryService.get_expiry_alerts(days=expiry_threshold)

            if expiring_prods:
                exp_data = []
                for p in expiring_prods:
                    days_left = p.days_to_expiry
                    if days_left < 0:
                        urgency = f"🔴 EXPIRED ({abs(days_left)} days ago)"
                    elif days_left == 0:
                        urgency = "🚨 EXPIRES TODAY"
                    elif days_left <= 7:
                        urgency = f"🟠 Urgent: {days_left} days left"
                    else:
                        urgency = f"🟡 Warning: {days_left} days left"

                    exp_data.append({
                        "SKU": p.sku,
                        "Product Name": p.name,
                        "Category": p.category,
                        "Units in Stock": p.stock_qty,
                        "Expiry Date": p.expiry_date.strftime("%d %b %Y"),
                        "Urgency Level": urgency,
                        "Supplier": p.supplier.name if p.supplier else "Direct Wholesale",
                    })
                st.dataframe(pd.DataFrame(exp_data), use_container_width=True, hide_index=True)
            else:
                st.success(f"🎉 No products in catalog are expired or expiring within {expiry_threshold} days!")

        # TAB 3: Quick Restock & Adjustments
        with tab3:
            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.subheader("📥 Add Restock Delivery")
                st.caption("Adds new incoming shipment units and records an inventory movement.")
                all_active_products = Product.query.filter_by(is_active=True).order_by(Product.name.asc()).all()
                prod_options = {f"{p.name} ({p.sku}) - Stock: {p.stock_qty}": p.product_id for p in all_active_products}

                with st.form("restock_form"):
                    selected_label = st.selectbox("Select Product to Restock", list(prod_options.keys()))
                    restock_qty = st.number_input("Quantity Added", min_value=1, value=10, step=1)
                    ref_po = st.text_input("PO / Invoice Reference", placeholder="e.g. PO-2026-DELIVERY-01")
                    restock_notes = st.text_input("Internal Notes", placeholder="e.g. Received from wholesale vendor")
                    submitted_restock = st.form_submit_button("Confirm & Add Stock", use_container_width=True)

                    if submitted_restock and selected_label:
                        pid = prod_options[selected_label]
                        admin_user = User.query.filter_by(role="admin").first()
                        try:
                            updated_p = InventoryService.restock_product(
                                product_id=pid,
                                quantity_added=restock_qty,
                                user_id=admin_user.user_id if admin_user else None,
                                reference=ref_po or "Streamlit Restock",
                                notes=restock_notes or f"Restocked {restock_qty} units via Streamlit Portal",
                            )
                            st.success(f"✅ Successfully restocked {restock_qty} units of **{updated_p.name}**! New stock: **{updated_p.stock_qty}**.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Restock error: {str(e)}")

            with col_r2:
                st.subheader("⚖️ Audit Stock Adjustment")
                st.caption("Adjusts stock to match a physical count (loss, damage, audit).")
                with st.form("adjust_form"):
                    selected_adj_label = st.selectbox("Select Product for Audit Count", list(prod_options.keys()))
                    counted_qty = st.number_input("Actual Counted Physical Stock", min_value=0, value=20, step=1)
                    adj_reason = st.selectbox("Reason for Adjustment", ["Physical Cycle Count", "Damaged / Broken Goods", "Perishable Spoilage", "Customer Return / Restock", "Other Correction"])
                    adj_notes = st.text_input("Audit Notes", placeholder="e.g. Reconciled during monthly shelf inspection")
                    submitted_adjust = st.form_submit_button("Update Physical Stock", use_container_width=True)

                    if submitted_adjust and selected_adj_label:
                        pid = prod_options[selected_adj_label]
                        admin_user = User.query.filter_by(role="admin").first()
                        try:
                            updated_p = InventoryService.adjust_stock(
                                product_id=pid,
                                new_quantity=counted_qty,
                                user_id=admin_user.user_id if admin_user else None,
                                reason=adj_reason,
                                notes=adj_notes or f"Adjusted to {counted_qty} units",
                            )
                            st.success(f"✅ Stock for **{updated_p.name}** adjusted to **{updated_p.stock_qty}** units.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Adjustment error: {str(e)}")

        # TAB 4: Movement Audit Trail
        with tab4:
            st.subheader("📜 Recent Inventory Movement Logs")
            st.caption("Immutable ledger tracking every sale deduction, restock shipment, and audit adjustment.")
            movements = InventoryMovement.query.order_by(InventoryMovement.created_at.desc(), InventoryMovement.movement_id.desc()).limit(40).all()
            if movements:
                mov_data = []
                for m in movements:
                    mov_data.append({
                        "ID": f"#{m.movement_id}",
                        "Timestamp": m.created_at.strftime("%d %b %Y %H:%M"),
                        "Product": m.product.name if m.product else "N/A",
                        "SKU": m.product.sku if m.product else "N/A",
                        "Movement Type": m.movement_type.upper(),
                        "Quantity Change": f"{m.quantity_change:+d}",
                        "Previous Stock": m.previous_stock,
                        "Resulting Stock": m.resulting_stock,
                        "Reference": m.reference or "-",
                        "Notes": m.notes or "-",
                    })
                st.dataframe(pd.DataFrame(mov_data), use_container_width=True, hide_index=True)
            else:
                st.info("No movement records logged yet.")


# ---------------------------------------------------------
# Page 3: 📈 Analytics & Sales BI
# ---------------------------------------------------------
def render_analytics():
    st.title("📈 Business Intelligence & Demand Analytics")
    st.caption("Pandas-driven descriptive and diagnostic analytics for GreenLeaf Grocers.")

    with flask_app.app_context():
        time_frame = st.selectbox(
            "Select Analytics Window",
            ["last_30_days", "last_7_days", "this_month", "prev_month"],
            format_func=lambda x: {
                "last_30_days": "Last 30 Days",
                "last_7_days": "Last 7 Days",
                "this_month": "This Month",
                "prev_month": "Previous Month",
            }.get(x, x),
        )

        top_col1, top_col2 = st.columns([5, 5])

        with top_col1:
            st.subheader("🏆 Top 10 Best-Selling Products")
            top_prods = AnalyticsService.get_top_products(range_key=time_frame, limit=10)
            if top_prods:
                df_top = pd.DataFrame(top_prods)
                fig_top = px.bar(
                    df_top,
                    x="revenue",
                    y="name",
                    orientation="h",
                    title="Gross Revenue by Top Products (₹)",
                    labels={"revenue": "Revenue (₹)", "name": "Product"},
                    color="revenue",
                    color_continuous_scale="Greens",
                )
                fig_top.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("No product sales in this period.")

        with top_col2:
            st.subheader("💳 Payment Methods Breakdown")
            pay_data = AnalyticsService.get_payment_method_breakdown(range_key=time_frame)
            if pay_data:
                df_pay = pd.DataFrame(pay_data)
                fig_pay = px.pie(
                    df_pay,
                    names="payment_method",
                    values="revenue",
                    title="Revenue by Payment Channel",
                    hole=0.4,
                    color_discrete_sequence=["#16865b", "#3b82f6", "#f59e0b", "#8b5cf6"],
                )
                fig_pay.update_layout(margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_pay, use_container_width=True)
            else:
                st.info("No payment transactions in this period.")

        st.markdown("---")

        st.subheader("🐢 Slow-Moving Stock Surveillance")
        st.caption("Identifies active SKUs with 0 or minimal sales in the last 30 days that risk occupying shelf space or nearing spoilage.")
        slow_movers = AnalyticsService.get_slow_moving_products(days=30, threshold_sales=3)
        if slow_movers:
            df_slow = pd.DataFrame(slow_movers)
            df_slow["cost_value_str"] = df_slow["cost_value"].apply(fmt_currency)
            df_slow_view = df_slow[["sku", "name", "category", "current_stock", "units_sold", "cost_value_str"]].rename(
                columns={
                    "sku": "SKU",
                    "name": "Product Name",
                    "category": "Category",
                    "current_stock": "Current Stock",
                    "units_sold": "Units Sold (30d)",
                    "cost_value_str": "Capital Blocked (Cost)",
                }
            )
            st.dataframe(df_slow_view, use_container_width=True, hide_index=True)
        else:
            st.success("✨ All active SKUs are rotating with healthy turnover velocity!")


# ---------------------------------------------------------
# Page 4: 🔮 7-Day Demand Forecasting
# ---------------------------------------------------------
def render_forecasting():
    st.title("🔮 7-Day Demand Forecasting & Replenishment")
    st.caption("Calculates 30-day historical moving average daily run-rates and factors in safety stock buffers to recommend replenishment quantities.")

    with flask_app.app_context():
        forecasts = AnalyticsService.get_demand_forecast()
        if not forecasts:
            st.info("No product demand data available.")
            return

        df_f = pd.DataFrame(forecasts)
        needing_reorder = df_f[df_f["suggested_replenishment"] > 0]

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.metric("Total Catalog SKUs Analyzed", len(df_f))
        with fc2:
            st.metric("SKUs Requiring Immediate Reorder", len(needing_reorder))
        with fc3:
            total_reorder_units = int(needing_reorder["suggested_replenishment"].sum()) if not needing_reorder.empty else 0
            st.metric("Total Replenishment Units Needed", f"{total_reorder_units:,}")

        st.subheader("📋 Recommended Purchase Order Replenishment Manifest")

        filter_reorder = st.checkbox("Show only SKUs needing replenishment", value=True)
        display_df = needing_reorder if filter_reorder else df_f

        if not display_df.empty:
            # Map suppliers
            prod_ids = display_df["product_id"].tolist()
            prods = Product.query.filter(Product.product_id.in_(prod_ids)).all()
            supplier_map = {p.product_id: (p.supplier.name if p.supplier else "Direct Wholesaler") for p in prods}
            supplier_contact = {p.product_id: (p.supplier.phone if p.supplier else "-") for p in prods}

            display_df = display_df.copy()
            display_df["Supplier"] = display_df["product_id"].map(supplier_map)
            display_df["Supplier Phone"] = display_df["product_id"].map(supplier_contact)

            view_df = display_df[[
                "sku",
                "name",
                "category",
                "current_stock",
                "avg_daily_demand",
                "predicted_7d_demand",
                "safety_stock",
                "suggested_replenishment",
                "confidence",
                "Supplier",
                "Supplier Phone",
            ]].rename(
                columns={
                    "sku": "SKU",
                    "name": "Product Name",
                    "category": "Category",
                    "current_stock": "Current Stock",
                    "avg_daily_demand": "Avg Daily Sales",
                    "predicted_7d_demand": "Projected 7D Demand",
                    "safety_stock": "Safety Buffer",
                    "suggested_replenishment": "⚡ Recommended Order",
                    "confidence": "Forecast Confidence",
                }
            )

            st.dataframe(view_df, use_container_width=True, hide_index=True)

            # CSV Download Button
            csv_data = view_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Purchase Order Manifest (CSV)",
                data=csv_data,
                file_name=f"greenleaf_purchase_order_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.success("✨ Current stock levels across all catalog products comfortably satisfy projected 7-day demand!")


# ---------------------------------------------------------
# Page 5: 🛒 Point of Sale (POS) Billing Terminal
# ---------------------------------------------------------
def render_pos():
    st.title("🛒 POS Billing Terminal")
    st.caption("Point-of-sale register with real-time stock deduction and thermal receipt generation.")

    if "pos_cart" not in st.session_state:
        st.session_state.pos_cart = []

    with flask_app.app_context():
        col_pos_left, col_pos_right = st.columns([5, 5])

        with col_pos_left:
            st.subheader("🛍️ Add Items to Cart")
            active_prods = Product.query.filter(Product.is_active == True, Product.stock_qty > 0).order_by(Product.name.asc()).all()

            if not active_prods:
                st.warning("No products with stock available in catalog.")
            else:
                prod_choices = {f"{p.name} [{p.sku}] - ₹{p.unit_price:.2f} (Stock: {p.stock_qty})": p.product_id for p in active_prods}
                selected_item_label = st.selectbox("Search & Select Product", list(prod_choices.keys()))
                selected_pid = prod_choices[selected_item_label]
                sel_product = db.session.get(Product, selected_pid)

                c_qty, c_btn = st.columns([3, 4])
                with c_qty:
                    add_qty = st.number_input("Quantity", min_value=1, max_value=max(1, sel_product.stock_qty), value=1, step=1)
                with c_btn:
                    st.write("")
                    st.write("")
                    if st.button("➕ Add to Cart", use_container_width=True):
                        # Check if product is already in cart
                        existing = next((item for item in st.session_state.pos_cart if item["product_id"] == selected_pid), None)
                        if existing:
                            new_q = existing["quantity"] + add_qty
                            if new_q > sel_product.stock_qty:
                                st.error(f"Cannot add {add_qty} more. Total in cart ({new_q}) exceeds available stock ({sel_product.stock_qty}).")
                            else:
                                existing["quantity"] = new_q
                                st.toast(f"Updated {sel_product.name} quantity to {new_q}!", icon="🛒")
                        else:
                            st.session_state.pos_cart.append({
                                "product_id": sel_product.product_id,
                                "name": sel_product.name,
                                "sku": sel_product.sku,
                                "unit_price": sel_product.unit_price,
                                "quantity": add_qty,
                            })
                            st.toast(f"Added {sel_product.name} to cart!", icon="🌿")

            st.markdown("---")
            st.subheader("🛒 Current Shopping Cart")
            if not st.session_state.pos_cart:
                st.info("The shopping cart is currently empty. Select products above to begin checkout.")
            else:
                cart_display = []
                for idx, item in enumerate(st.session_state.pos_cart):
                    line_tot = item["quantity"] * item["unit_price"]
                    cart_display.append({
                        "#": idx + 1,
                        "Product": item["name"],
                        "SKU": item["sku"],
                        "Price": fmt_currency(item["unit_price"]),
                        "Qty": item["quantity"],
                        "Total": fmt_currency(line_tot),
                    })
                st.dataframe(pd.DataFrame(cart_display), use_container_width=True, hide_index=True)

                if st.button("🗑️ Clear Entire Cart", type="secondary"):
                    st.session_state.pos_cart = []
                    st.rerun()

        with col_pos_right:
            st.subheader("💳 Checkout & Authoritative Billing")
            if not st.session_state.pos_cart:
                st.info("Add items to calculate bill totals.")
            else:
                # Prepare billing inputs
                cart_calc_input = [{"product_id": it["product_id"], "quantity": it["quantity"]} for it in st.session_state.pos_cart]

                cashiers = User.query.filter(User.is_active == True).all()
                cashier_opts = {u.full_name: u.user_id for u in cashiers}
                chosen_cashier_name = st.selectbox("Active Cashier", list(cashier_opts.keys()))
                chosen_cashier_id = cashier_opts[chosen_cashier_name]

                col_disc, col_pay = st.columns(2)
                with col_disc:
                    discount_pct = st.number_input("Discount (%)", min_value=0.0, max_value=30.0, value=0.0, step=1.0)
                with col_pay:
                    pay_method = st.selectbox("Payment Method", ["UPI", "Cash", "Card", "Store Credit"])

                cust_col1, cust_col2 = st.columns(2)
                with cust_col1:
                    cust_name = st.text_input("Customer Name (Optional)", placeholder="e.g. Ramesh Kumar")
                with cust_col2:
                    cust_phone = st.text_input("Customer Phone (Optional)", placeholder="e.g. 9876543210")

                # Authoritative calculation
                try:
                    bill_summary = BillingService.calculate_bill(cart_calc_input, discount_percent=discount_pct)
                    
                    st.markdown(
                        f"""
                        <div style="background:#f1f5f9; padding:1.2rem; border-radius:8px; margin:1rem 0;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span>Subtotal:</span><strong>{fmt_currency(bill_summary['subtotal'])}</strong>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px; color:#15803d;">
                                <span>Discount ({discount_pct:.0f}%):</span><strong>- {fmt_currency(bill_summary['discount_amount'])}</strong>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span>Tax (GST 5%):</span><strong>+ {fmt_currency(bill_summary['tax_amount'])}</strong>
                            </div>
                            <hr style="margin:8px 0; border:none; border-top:1px solid #cbd5e1;">
                            <div style="display:flex; justify-content:space-between; font-size:1.3rem; color:#0f593c;">
                                <strong>Grand Total:</strong><strong>{fmt_currency(bill_summary['grand_total'])}</strong>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button("🚀 Complete Checkout & Print Receipt", type="primary", use_container_width=True):
                        sale_record = BillingService.process_checkout(
                            cashier_id=chosen_cashier_id,
                            cart_items_data=cart_calc_input,
                            discount_percent=discount_pct,
                            payment_method=pay_method,
                            customer_name=cust_name or None,
                            customer_phone=cust_phone or None,
                            notes="Checkout processed via GreenLeaf Streamlit POS Terminal",
                        )
                        st.session_state.last_sale_id = sale_record.sale_id
                        st.session_state.pos_cart = []
                        st.success(f"🎉 Transaction Completed! Receipt #{sale_record.receipt_number}")
                        st.rerun()

                except Exception as e:
                    st.error(f"Billing calculation error: {str(e)}")

            # Render Receipt if a sale was recently made
            if "last_sale_id" in st.session_state:
                last_sale = db.session.get(Sale, st.session_state.last_sale_id)
                if last_sale:
                    st.markdown("---")
                    st.subheader("🧾 Generated Thermal Receipt")
                    receipt_lines = [
                        "========================================",
                        "          GREENLEAF GROCERS             ",
                        "     Fresh Stock. Smart Decisions.      ",
                        "  124 Eco Valley Road, Bengaluru 560034 ",
                        "========================================",
                        f"Receipt: {last_sale.receipt_number}",
                        f"Date   : {last_sale.created_at.strftime('%d-%b-%Y %I:%M %p')}",
                        f"Cashier: {last_sale.cashier.full_name if last_sale.cashier else 'Staff'}",
                        f"Customer: {last_sale.customer_name or 'Walk-in'}",
                        "----------------------------------------",
                        "Item                Qty   Price    Total",
                        "----------------------------------------",
                    ]
                    for item in last_sale.items:
                        name_short = (item.product_name_snapshot[:18]).ljust(18)
                        qty_str = str(item.quantity).rjust(3)
                        prc_str = f"{item.unit_price:.2f}".rjust(7)
                        tot_str = f"{item.line_total:.2f}".rjust(8)
                        receipt_lines.append(f"{name_short} {qty_str} {prc_str} {tot_str}")

                    receipt_lines.extend([
                        "----------------------------------------",
                        f"Subtotal        : INR {last_sale.subtotal:,.2f}",
                        f"Discount ({last_sale.discount_percent:.0f}%)   : INR {last_sale.discount_amount:,.2f}",
                        f"Tax (GST 5%)    : INR {last_sale.tax_amount:,.2f}",
                        "----------------------------------------",
                        f"GRAND TOTAL     : INR {last_sale.total_amount:,.2f}",
                        f"Payment Mode    : {last_sale.payment_method}",
                        "========================================",
                        "   Thank you for shopping at GreenLeaf! ",
                        "========================================",
                    ])
                    receipt_text = "\n".join(receipt_lines)
                    st.markdown(f'<div class="thermal-receipt"><pre>{receipt_text}</pre></div>', unsafe_allow_html=True)
                    st.download_button(
                        "📄 Download Receipt Text",
                        data=receipt_text,
                        file_name=f"{last_sale.receipt_number}.txt",
                        mime="text/plain",
                    )


# ---------------------------------------------------------
# Page 6: 🏷️ Product Catalog
# ---------------------------------------------------------
def render_catalog():
    st.title("🏷️ Supermarket Product Catalog")
    st.caption("Browse, search, and manage products with real-world Indian snacks and groceries.")

    with flask_app.app_context():
        c_search, c_cat = st.columns([3, 2])
        with c_search:
            q = st.text_input("🔍 Search Catalog", placeholder="Search by name, SKU or barcode...")
        with c_cat:
            cats = ["All Categories"] + [c[0] for c in db.session.query(Product.category).distinct().all()]
            sel_cat = st.selectbox("Category Filter", cats)

        query = Product.query.filter_by(is_active=True)
        if sel_cat != "All Categories":
            query = query.filter_by(category=sel_cat)
        if q:
            term = f"%{q.strip()}%"
            query = query.filter((Product.name.ilike(term)) | (Product.sku.ilike(term)) | (Product.barcode.ilike(term)))

        products = query.order_by(Product.name.asc()).all()

        st.subheader(f"Catalog Products ({len(products)} found)")

        # Display as tabular overview
        if products:
            catalog_rows = []
            for p in products:
                catalog_rows.append({
                    "SKU": p.sku,
                    "Barcode": p.barcode or "-",
                    "Name": p.name,
                    "Category": p.category,
                    "Retail Price": fmt_currency(p.unit_price),
                    "Cost Price": fmt_currency(p.cost_price),
                    "In Stock": p.stock_qty,
                    "Reorder Threshold": p.reorder_level,
                    "Supplier": p.supplier.name if p.supplier else "Direct Wholesaler",
                })
            df_cat = pd.DataFrame(catalog_rows)
            st.dataframe(df_cat, use_container_width=True, hide_index=True)

            csv_catalog = df_cat.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Export Full Catalog (CSV)",
                data=csv_catalog,
                file_name="greenleaf_catalog.csv",
                mime="text/csv",
            )
        else:
            st.info("No matching products found.")

        # Expandable Add New Product Form
        with st.expander("➕ Add New Product to Catalog"):
            with st.form("add_product_form"):
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    new_sku = st.text_input("Product SKU *", placeholder="e.g. SNK-HAL-027")
                    new_name = st.text_input("Product Name *", placeholder="e.g. Haldiram Moong Dal (200g)")
                    new_cat = st.selectbox("Category *", ["Snacks", "Dairy", "Beverages", "Fruits", "Vegetables", "Grains and Pulses", "Bakery", "Household Essentials"])
                    new_barcode = st.text_input("Barcode / EAN (Optional)", placeholder="e.g. 8901451234567")
                with p_col2:
                    new_price = st.number_input("Retail Price (₹) *", min_value=1.0, value=50.0, step=1.0)
                    new_cost = st.number_input("Cost Price (₹) *", min_value=0.5, value=35.0, step=1.0)
                    new_stock = st.number_input("Initial Physical Stock *", min_value=0, value=25, step=1)
                    new_reorder = st.number_input("Reorder Level *", min_value=1, value=10, step=1)
                    new_expiry = st.date_input("Expiry Date (Optional)", value=date.today() + timedelta(days=120))

                submit_prod = st.form_submit_button("Create Product", use_container_width=True)
                if submit_prod:
                    if not new_sku or not new_name:
                        st.error("SKU and Name are mandatory.")
                    else:
                        existing_p = Product.query.filter_by(sku=new_sku.strip()).first()
                        if existing_p:
                            st.error(f"SKU '{new_sku}' already exists.")
                        else:
                            p = Product(
                                sku=new_sku.strip(),
                                barcode=new_barcode.strip() if new_barcode else None,
                                name=new_name.strip(),
                                category=new_cat,
                                unit_price=float(new_price),
                                cost_price=float(new_cost),
                                stock_qty=int(new_stock),
                                reorder_level=int(new_reorder),
                                expiry_date=new_expiry,
                                is_active=True,
                            )
                            db.session.add(p)
                            db.session.commit()
                            st.success(f"✅ Product '{new_name}' added to catalog successfully!")
                            st.rerun()


# ---------------------------------------------------------
# Page 7: ⚙️ Database & Settings
# ---------------------------------------------------------
def render_settings():
    st.title("⚙️ System Status & Database Management")
    st.caption("Inspect live database parameters, verify table integrity, and re-seed demo data.")

    with flask_app.app_context():
        db_path = flask_app.config.get("SQLALCHEMY_DATABASE_URI")
        st.write(f"**Database URI**: `{db_path}`")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Products", Product.query.count())
        with c2:
            st.metric("Total Completed Sales", Sale.query.filter_by(transaction_status="completed").count())
        with c3:
            st.metric("Total Movements Logged", InventoryMovement.query.count())
        with c4:
            st.metric("Suppliers Configured", Supplier.query.count())

        st.markdown("---")
        st.subheader("🔄 Database Re-Seeding Routine")
        st.write(
            """
            Clicking the button below will reset the SQLite database, re-create all schema tables,
            and populate fresh demo data including **80+ supermarket SKUs** (with authentic Indian snacks
            and Open Food Facts entries), **500+ historical sales transactions**, and audit trails.
            """
        )

        if st.button("🚀 Reset & Re-Seed Demo Database", type="primary"):
            with st.spinner("Seeding database with realistic supermarket dataset..."):
                seed_database(num_sales=300, random_seed=42, app=flask_app, drop_existing=True)
            st.success("✅ Demo database successfully re-seeded!")
            st.rerun()

        st.markdown("---")
        st.subheader("🌐 Hosting Information")
        st.info(
            """
            - **Platform**: Streamlit Community Cloud / Local Execution
            - **Backend Engine**: Flask 3.1 + SQLAlchemy 3.1 ORM
            - **Analytics Layer**: Pandas 3.0 + Plotly 7.1
            - **Repository**: [GitHub: SubhadeepBhandari25/GreenLeaf-Nexus](https://github.com/SubhadeepBhandari25/GreenLeaf-Nexus)
            """
        )


# ---------------------------------------------------------
# Application Entry Point & Navigation
# ---------------------------------------------------------
def main():
    init_database_if_needed()

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <span style="font-size: 2.5rem;">🌿</span>
                <h2 style="margin: 0; color: #16865b; font-weight: 700;">GreenLeaf Nexus</h2>
                <p style="margin: 0; font-size: 0.85rem; color: #64748b;">Supermarket ERP & Analytics</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navigate",
            options=[
                "📊 Executive Dashboard",
                "📦 Inventory & Surveillance",
                "📈 Sales & Demand Analytics",
                "🔮 7-Day Demand Forecasting",
                "🛒 POS Billing Terminal",
                "🏷️ Product Catalog",
                "⚙️ Database & Settings",
            ],
            index=0,
        )

        st.markdown("---")
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #64748b; line-height: 1.5;">
                <strong>GreenLeaf Grocers</strong><br>
                Store #101 • Bengaluru<br>
                Currency: <strong>INR (₹)</strong><br>
                Tax Rate: <strong>5% GST</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Route to selected page
    if page == "📊 Executive Dashboard":
        render_dashboard()
    elif page == "📦 Inventory & Surveillance":
        render_inventory()
    elif page == "📈 Sales & Demand Analytics":
        render_analytics()
    elif page == "🔮 7-Day Demand Forecasting":
        render_forecasting()
    elif page == "🛒 POS Billing Terminal":
        render_pos()
    elif page == "🏷️ Product Catalog":
        render_catalog()
    elif page == "⚙️ Database & Settings":
        render_settings()


if __name__ == "__main__":
    main()
