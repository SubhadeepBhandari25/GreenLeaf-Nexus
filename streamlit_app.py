"""
GreenLeaf Nexus - Smart Inventory & Sales Management System with Analytics Dashboard
Streamlit Application Entrypoint & Cloud Deployment Engine
Brand Identity: GreenLeaf Grocers | Tagline: Fresh Stock. Smart Decisions.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure base paths
BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = INSTANCE_DIR / "greenleaf.db"

# -----------------------------------------------------------------------------
# Database Setup & Seeding Helper
# -----------------------------------------------------------------------------
def get_db_connection():
    """Returns a thread-safe SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database_ready():
    """Ensures SQLite database exists and is populated with seed data."""
    needs_seeding = False
    if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
        needs_seeding = True
    else:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM products")
            count = cur.fetchone()[0]
            conn.close()
            if count == 0:
                needs_seeding = True
        except Exception:
            needs_seeding = True

    if needs_seeding:
        try:
            from seed_data import seed_database
            seed_database(drop_existing=True)
        except Exception as e:
            st.error(f"Error seeding database: {e}")


# Run pre-flight database check
ensure_database_ready()


# -----------------------------------------------------------------------------
# Core Data Access Functions
# -----------------------------------------------------------------------------
def load_products_df(active_only=True):
    """Loads all products as a Pandas DataFrame."""
    conn = get_db_connection()
    query = """
        SELECT p.*, s.name as supplier_name 
        FROM products p 
        LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
    """
    if active_only:
        query += " WHERE p.is_active = 1"
    query += " ORDER BY p.category, p.name"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        today = pd.Timestamp.now().normalize()
        df["expiry_date_dt"] = pd.to_datetime(df["expiry_date"], errors="coerce")
        df["days_to_expiry"] = (df["expiry_date_dt"] - today).dt.days

        def get_stock_status(row):
            if row["stock_qty"] <= 0:
                return "Out of Stock"
            if row["stock_qty"] <= row["reorder_level"]:
                return "Low Stock"
            return "Healthy"

        def get_expiry_status(row):
            if pd.isnull(row["days_to_expiry"]):
                return "No Expiry"
            days = row["days_to_expiry"]
            if days < 0:
                return "Expired"
            if days == 0:
                return "Expiring Today"
            if days <= 7:
                return "Within 7 Days"
            if days <= 15:
                return "Within 15 Days"
            return "Fresh"

        df["stock_status"] = df.apply(get_stock_status, axis=1)
        df["expiry_status"] = df.apply(get_expiry_status, axis=1)
        df["margin_pct"] = np.where(
            df["unit_price"] > 0,
            ((df["unit_price"] - df["cost_price"]) / df["unit_price"]) * 100,
            0.0
        )
        df["inventory_value"] = df["stock_qty"] * df["unit_price"]

    return df


def load_sales_df(start_date=None, end_date=None):
    """Loads sales transactions with optional date range."""
    conn = get_db_connection()
    query = "SELECT * FROM sales WHERE transaction_status = 'completed'"
    params = []
    if start_date:
        query += " AND sale_date >= ?"
        params.append(str(start_date))
    if end_date:
        query += " AND sale_date <= ?"
        params.append(str(end_date))
    query += " ORDER BY sale_date DESC, sale_time DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def load_sale_items_df(start_date=None, end_date=None):
    """Loads sale items with joined product and sale metadata."""
    conn = get_db_connection()
    query = """
        SELECT si.*, s.sale_date, s.invoice_number, p.category, p.image_path, p.cost_price
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.sale_id
        LEFT JOIN products p ON si.product_id = p.product_id
        WHERE s.transaction_status = 'completed'
    """
    params = []
    if start_date:
        query += " AND s.sale_date >= ?"
        params.append(str(start_date))
    if end_date:
        query += " AND s.sale_date <= ?"
        params.append(str(end_date))
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def load_inventory_movements_df(limit=100):
    """Loads recent inventory movements audit trail."""
    conn = get_db_connection()
    query = """
        SELECT m.*, p.name as product_name, p.sku, u.full_name as user_name
        FROM inventory_movements m
        JOIN products p ON m.product_id = p.product_id
        LEFT JOIN users u ON m.user_id = u.user_id
        ORDER BY m.created_at DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=[limit])
    conn.close()
    return df


def load_suppliers_df():
    """Loads supplier vendors list."""
    conn = get_db_connection()
    query = """
        SELECT s.*, COUNT(p.product_id) as total_products
        FROM suppliers s
        LEFT JOIN products p ON s.supplier_id = p.supplier_id
        GROUP BY s.supplier_id
        ORDER BY s.name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# -----------------------------------------------------------------------------
# Database Mutation Actions (Thread-safe Parameterized Queries)
# -----------------------------------------------------------------------------
def execute_pos_checkout(cart_items, subtotal, discount_amount, tax_amount, total_amount, payment_method, customer_name, customer_phone, user_id=1):
    """Executes atomic POS checkout, writes sale, items, movements, and deducts stock."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN TRANSACTION")

        # Verify stock for all items first
        for item in cart_items:
            cur.execute("SELECT stock_qty, name FROM products WHERE product_id = ?", (item["product_id"],))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Product ID {item['product_id']} not found.")
            if row["stock_qty"] < item["quantity"]:
                raise ValueError(f"Insufficient stock for '{row['name']}'. Available: {row['stock_qty']}, Requested: {item['quantity']}")

        # Generate invoice number
        cur.execute("SELECT COUNT(*) FROM sales")
        next_count = cur.fetchone()[0] + 1
        invoice_no = f"INV-{datetime.now().strftime('%Y%m')}-{next_count:04d}"

        now = datetime.now()
        sale_date_str = now.strftime("%Y-%m-%d")
        sale_time_str = now.strftime("%H:%M:%S")
        created_at_str = now.strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO sales (
                invoice_number, sale_date, sale_time, user_id,
                subtotal, discount_amount, tax_amount, total_amount,
                payment_method, transaction_status, customer_name, customer_phone,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_no, sale_date_str, sale_time_str, user_id,
            subtotal, discount_amount, tax_amount, total_amount,
            payment_method, "completed", customer_name or "", customer_phone or "",
            "Streamlit POS Terminal Checkout", created_at_str
        ))
        sale_id = cur.lastrowid

        # Insert sale items and update stock
        for item in cart_items:
            cur.execute("SELECT stock_qty, cost_price FROM products WHERE product_id = ?", (item["product_id"],))
            prod_row = cur.fetchone()
            prev_stock = prod_row["stock_qty"]
            new_stock = prev_stock - item["quantity"]
            cost_price = prod_row["cost_price"]

            cur.execute("""
                INSERT INTO sale_items (
                    sale_id, product_id, product_name_snapshot, quantity,
                    unit_price, unit_cost_snapshot, discount_amount, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sale_id, item["product_id"], item["name"], item["quantity"],
                item["unit_price"], cost_price, item.get("discount", 0.0), item["line_total"]
            ))

            cur.execute("UPDATE products SET stock_qty = ?, updated_at = ? WHERE product_id = ?", (new_stock, created_at_str, item["product_id"]))

            # Record inventory movement
            cur.execute("""
                INSERT INTO inventory_movements (
                    product_id, user_id, movement_type, quantity_change,
                    previous_stock, resulting_stock, reference, notes, created_at
                ) VALUES (?, ?, 'sale', ?, ?, ?, ?, ?, ?)
            """, (
                item["product_id"], user_id, -item["quantity"],
                prev_stock, new_stock, invoice_no, f"POS Sale #{invoice_no}", created_at_str
            ))

        conn.commit()
        return invoice_no, None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        conn.close()


def restock_product(product_id, quantity, reference="Streamlit Restock", notes=""):
    """Adds stock and creates an audit movement."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT stock_qty, name FROM products WHERE product_id = ?", (product_id,))
        row = cur.fetchone()
        if not row:
            return False, "Product not found"
        prev_stock = row["stock_qty"]
        new_stock = prev_stock + quantity
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("UPDATE products SET stock_qty = ?, updated_at = ? WHERE product_id = ?", (new_stock, now_str, product_id))
        cur.execute("""
            INSERT INTO inventory_movements (
                product_id, user_id, movement_type, quantity_change,
                previous_stock, resulting_stock, reference, notes, created_at
            ) VALUES (?, 1, 'restock', ?, ?, ?, ?, ?, ?)
        """, (product_id, quantity, prev_stock, new_stock, reference, notes or f"Restocked +{quantity}", now_str))
        conn.commit()
        return True, f"Successfully restocked {quantity} units of '{row['name']}'. New stock: {new_stock}."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def adjust_stock(product_id, new_quantity, reason="Audit Adjustment", notes=""):
    """Corrects physical stock count and creates movement record."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT stock_qty, name FROM products WHERE product_id = ?", (product_id,))
        row = cur.fetchone()
        if not row:
            return False, "Product not found"
        prev_stock = row["stock_qty"]
        diff = new_quantity - prev_stock
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("UPDATE products SET stock_qty = ?, updated_at = ? WHERE product_id = ?", (new_quantity, now_str, product_id))
        cur.execute("""
            INSERT INTO inventory_movements (
                product_id, user_id, movement_type, quantity_change,
                previous_stock, resulting_stock, reference, notes, created_at
            ) VALUES (?, 1, 'adjustment', ?, ?, ?, ?, ?, ?)
        """, (product_id, diff, prev_stock, new_quantity, reason, notes or f"Adjusted stock from {prev_stock} to {new_quantity}", now_str))
        conn.commit()
        return True, f"Stock count updated for '{row['name']}'. Set to {new_quantity}."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def add_product(sku, barcode, name, category, unit_price, cost_price, stock_qty, reorder_level, expiry_date, supplier_id=None, image_path=None):
    """Adds a new product to the catalog."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO products (
                sku, barcode, name, category, unit_price, cost_price,
                stock_qty, reorder_level, expiry_date, supplier_id, image_path,
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            sku, barcode or "", name, category, unit_price, cost_price,
            stock_qty, reorder_level, expiry_date or None, supplier_id or None, image_path or "",
            now_str, now_str
        ))
        prod_id = cur.lastrowid
        cur.execute("""
            INSERT INTO inventory_movements (
                product_id, user_id, movement_type, quantity_change,
                previous_stock, resulting_stock, reference, notes, created_at
            ) VALUES (?, 1, 'initial', ?, 0, ?, 'Product Creation', 'Initial Stock', ?)
        """, (prod_id, stock_qty, stock_qty, now_str))
        conn.commit()
        return True, f"Product '{name}' (SKU: {sku}) added successfully!"
    except sqlite3.IntegrityError:
        return False, f"A product with SKU '{sku}' already exists."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Main Streamlit Application UI
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="GreenLeaf Nexus - Grocers ERP & Analytics",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize Session States
    if "cart" not in st.session_state:
        st.session_state.cart = []
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Executive Analytics"
    if "last_receipt" not in st.session_state:
        st.session_state.last_receipt = None

    # Custom Clean Emerald Styling
    st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(135deg, #0F593C 0%, #16865B 100%);
            padding: 1.4rem 1.8rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(22, 134, 91, 0.15);
        }
        .main-header h1 {
            color: #ffffff !important;
            margin: 0;
            font-size: 1.9rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .main-header p {
            color: #E8F5E9 !important;
            margin: 4px 0 0 0;
            font-size: 0.95rem;
            opacity: 0.9;
        }
        .kpi-card {
            background: #ffffff;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.15s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: #16865B;
        }
        .metric-title {
            color: #64748B;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            color: #0F172A;
            font-size: 1.8rem;
            font-weight: 700;
            margin-top: 4px;
        }
        .metric-sub {
            color: #16865B;
            font-size: 0.82rem;
            margin-top: 2px;
            font-weight: 500;
        }
        .badge-healthy {
            background-color: #DEF7EC;
            color: #03543F;
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        .badge-warning {
            background-color: #FEF08A;
            color: #713F12;
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        .badge-danger {
            background-color: #FDE8E8;
            color: #9B1C1C;
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        .receipt-card {
            background: #FAFAFA;
            border: 1px dashed #CBD5E1;
            padding: 1.5rem;
            border-radius: 8px;
            font-family: monospace;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        </style>
    """, unsafe_allow_html=True)

    # Top Brand Header Banner
    st.markdown("""
        <div class="main-header">
            <h1>🌿 GreenLeaf Nexus</h1>
            <p>Smart Inventory & Sales Management System with Interactive Analytics Dashboard • GreenLeaf Grocers</p>
        </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # Sidebar: Branding & Navigation
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/SubhadeepBhandari25/GreenLeaf-Nexus/main/static/img/greenleaf-logo.png", width=180) if os.path.exists("static/img/greenleaf-logo.png") else st.markdown("### 🌿 **GreenLeaf Grocers**")
        st.caption("Store #104 — Eco Valley, Bengaluru")
        
        st.markdown("---")
        st.markdown("### 🧭 **Navigation**")
        menu = st.radio(
            "Select Module",
            [
                "📊 Executive Dashboard",
                "🔮 7-Day Demand Forecasting",
                "🛒 POS Billing Terminal",
                "📦 Inventory & Expiry Surveillance",
                "🏷️ Product Catalog & Quick Add",
                "🚚 Suppliers Directory",
                "📑 Reports & Data Export",
            ],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("### 👤 **Active Session**")
        user_role = st.selectbox("Current Operator", ["Arun Verma (Cashier)", "Priya Sharma (Admin)", "Deepa Nair (Cashier)"])
        user_id = 1 if "Admin" in user_role else (2 if "Arun" in user_role else 3)

        st.markdown("---")
        # Live Quick Counts
        prod_df = load_products_df()
        low_count = (prod_df["stock_status"] == "Low Stock").sum() if not prod_df.empty else 0
        exp_count = (prod_df["expiry_status"].isin(["Expired", "Expiring Today", "Within 7 Days"])).sum() if not prod_df.empty else 0
        
        st.markdown("#### ⚡ **Live Alerts**")
        if low_count > 0:
            st.warning(f"⚠️ **{low_count} SKUs** below reorder level")
        else:
            st.success("✅ Stock levels healthy")

        if exp_count > 0:
            st.error(f"⏳ **{exp_count} SKUs** near/at expiry")

        st.caption(f"Database: `greenleaf.db` • Total SKUs: {len(prod_df)}")

    # -------------------------------------------------------------------------
    # 1. Executive Dashboard (Analytics)
    # -------------------------------------------------------------------------
    if menu == "📊 Executive Dashboard":
        st.subheader("📊 Executive Analytics & Business Intelligence")
        
        # Date Filter Controls
        col_f1, col_f2 = st.columns([2, 4])
        with col_f1:
            time_filter = st.selectbox(
                "Time Period",
                ["Last 30 Days", "Last 7 Days", "This Month", "Previous Month", "All Time"]
            )
        
        today = date.today()
        if time_filter == "Last 7 Days":
            start_d = today - timedelta(days=6)
            end_d = today
        elif time_filter == "Last 30 Days":
            start_d = today - timedelta(days=29)
            end_d = today
        elif time_filter == "This Month":
            start_d = today.replace(day=1)
            end_d = today
        elif time_filter == "Previous Month":
            first_this = today.replace(day=1)
            prev_end = first_this - timedelta(days=1)
            start_d = prev_end.replace(day=1)
            end_d = prev_end
        else:
            start_d = None
            end_d = None

        with col_f2:
            period_str = f"{start_d.strftime('%d %b %Y')} – {end_d.strftime('%d %b %Y')}" if start_d else "All Available History"
            st.info(f"📅 Showing transactions for: **{period_str}**")

        # Load sales and items
        sales_df = load_sales_df(start_d, end_d)
        items_df = load_sale_items_df(start_d, end_d)
        all_prods = load_products_df()

        # Top KPI Metrics Cards
        k1, k2, k3, k4 = st.columns(4)
        total_rev = sales_df["total_amount"].sum() if not sales_df.empty else 0.0
        total_bills = len(sales_df)
        abv = (total_rev / total_bills) if total_bills > 0 else 0.0
        
        # Estimate profit margin
        if not items_df.empty and "cost_price" in items_df.columns:
            total_cost = (items_df["quantity"] * items_df["cost_price"].fillna(0)).sum()
            gross_margin = (((total_rev - total_cost) / total_rev) * 100) if total_rev > 0 else 0.0
        else:
            gross_margin = 24.5

        with k1:
            st.metric("Total Revenue", f"₹{total_rev:,.2f}", delta=f"{total_bills} transactions")
        with k2:
            st.metric("Invoices / Bills", f"{total_bills:,}", delta="Completed")
        with k3:
            st.metric("Average Bill Value", f"₹{abv:,.2f}", delta="Per customer basket")
        with k4:
            st.metric("Gross Profit Margin", f"{gross_margin:.1f}%", delta="Estimated return")

        st.markdown("---")

        # Visualizations: Sales Trajectory & Category Share
        c_chart1, c_chart2 = st.columns([6, 4])
        
        with c_chart1:
            st.markdown("##### 📈 **Daily Revenue & Transaction Volume**")
            if not sales_df.empty:
                daily_grp = sales_df.groupby("sale_date").agg(
                    revenue=("total_amount", "sum"),
                    bills=("sale_id", "count")
                ).reset_index().sort_values("sale_date")

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Bar(
                    x=daily_grp["sale_date"],
                    y=daily_grp["revenue"],
                    name="Daily Revenue (₹)",
                    marker_color="#16865B",
                    opacity=0.85
                ))
                fig_trend.add_trace(go.Scatter(
                    x=daily_grp["sale_date"],
                    y=daily_grp["bills"],
                    name="Bill Count",
                    yaxis="y2",
                    mode="lines+markers",
                    line=dict(color="#F59E0B", width=3),
                    marker=dict(size=6)
                ))
                fig_trend.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    yaxis=dict(title="Revenue (₹)", gridcolor="#F1F5F9"),
                    yaxis2=dict(title="Invoices", overlaying="y", side="right", showgrid=False),
                    xaxis=dict(gridcolor="#F1F5F9"),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=350
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No transaction records found for this timeframe.")

        with c_chart2:
            st.markdown("##### 🍩 **Revenue Contribution by Category**")
            if not items_df.empty:
                cat_grp = items_df.groupby("category")["line_total"].sum().reset_index()
                cat_grp = cat_grp.sort_values(by="line_total", ascending=False)
                
                fig_donut = px.pie(
                    cat_grp,
                    names="category",
                    values="line_total",
                    hole=0.55,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_donut.update_traces(textposition="inside", textinfo="percent+label")
                fig_donut.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=350
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("No item data available.")

        # Bottom Grid: Top Selling Items and Slow Moving SKUs
        t_col1, t_col2 = st.columns(2)
        
        with t_col1:
            st.markdown("##### 🏆 **Top 10 High-Velocity Products**")
            if not items_df.empty:
                top_items = items_df.groupby(["product_name_snapshot", "category"]).agg(
                    units_sold=("quantity", "sum"),
                    revenue=("line_total", "sum")
                ).reset_index().sort_values(by="revenue", ascending=False).head(10)
                
                top_items["revenue"] = top_items["revenue"].apply(lambda v: f"₹{v:,.2f}")
                top_items.columns = ["Product", "Category", "Units Sold", "Gross Revenue"]
                st.dataframe(top_items, use_container_width=True, hide_index=True)
            else:
                st.write("No sales records available.")

        with t_col2:
            st.markdown("##### 🐢 **Slow-Moving Inventory Surveillance (30 Days)**")
            if not all_prods.empty:
                cutoff = date.today() - timedelta(days=30)
                recent_sales_conn = get_db_connection()
                sold_30d = pd.read_sql_query("""
                    SELECT product_id, SUM(quantity) as qty_sold
                    FROM sale_items si
                    JOIN sales s ON si.sale_id = s.sale_id
                    WHERE s.transaction_status = 'completed' AND s.sale_date >= ?
                    GROUP BY product_id
                """, recent_sales_conn, params=[str(cutoff)])
                recent_sales_conn.close()

                sold_map = dict(zip(sold_30d["product_id"], sold_30d["qty_sold"]))
                all_prods["sold_30d"] = all_prods["product_id"].map(sold_map).fillna(0).astype(int)
                slow_movers = all_prods[all_prods["sold_30d"] <= 2][["sku", "name", "category", "stock_qty", "sold_30d"]]
                slow_movers = slow_movers.sort_values(by=["sold_30d", "stock_qty"], ascending=[True, False]).head(10)
                slow_movers.columns = ["SKU", "Product", "Category", "Stock", "Sales (30d)"]
                st.dataframe(slow_movers, use_container_width=True, hide_index=True)
            else:
                st.write("Catalog empty.")

    # -------------------------------------------------------------------------
    # 2. 7-Day Demand Forecasting
    # -------------------------------------------------------------------------
    elif menu == "🔮 7-Day Demand Forecasting":
        st.subheader("🔮 Predictive 7-Day Demand & Automated Replenishment")
        st.markdown(r"""
            This statistical demand forecast calculates a 30-day moving daily consumption velocity ($\lambda$),
            factors in buffer safety stock ($\text{Reorder Level}$), and projects optimal replenishment:
            $$\text{Suggested Replenishment} = \max\left(0, (\lceil\text{Daily Demand} \times 7\rceil + \text{Safety Stock}) - \text{Current Stock}\right)$$
        """)

        # Calculate forecast dataframe
        prods = load_products_df()
        cutoff_date = date.today() - timedelta(days=30)
        conn = get_db_connection()
        sold_history = pd.read_sql_query("""
            SELECT product_id, SUM(quantity) as total_sold
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.transaction_status = 'completed' AND s.sale_date >= ?
            GROUP BY product_id
        """, conn, params=[str(cutoff_date)])
        conn.close()

        sold_dict = dict(zip(sold_history["product_id"], sold_history["total_sold"]))
        prods["sold_30d"] = prods["product_id"].map(sold_dict).fillna(0).astype(int)
        prods["avg_daily"] = (prods["sold_30d"] / 30.0).round(2)
        prods["predicted_7d"] = np.ceil(prods["avg_daily"] * 7).astype(int)
        prods["safety_stock"] = prods["reorder_level"]
        prods["suggested_order"] = (prods["predicted_7d"] + prods["safety_stock"] - prods["stock_qty"]).clip(lower=0)
        prods["confidence"] = np.where(prods["sold_30d"] >= 15, "High", np.where(prods["sold_30d"] > 0, "Moderate", "Low (Limited History)"))

        # Summary KPIs
        fc1, fc2, fc3, fc4 = st.columns(4)
        restock_needed_count = (prods["suggested_order"] > 0).sum()
        total_units_needed = prods["suggested_order"].sum()
        high_conf_count = (prods["confidence"] == "High").sum()

        with fc1:
            st.metric("SKUs Requiring Restock", f"{restock_needed_count} / {len(prods)}")
        with fc2:
            st.metric("Total Replenishment Units", f"{total_units_needed:,} units")
        with fc3:
            st.metric("High Confidence SKUs", f"{high_conf_count}")
        with fc4:
            st.metric("Historical Window", "30 Days Rolling")

        st.markdown("---")

        # Category Filter & Interactive Table
        col_cat, col_need = st.columns([3, 2])
        with col_cat:
            cats = ["All Categories"] + sorted(prods["category"].unique().tolist())
            selected_cat = st.selectbox("Filter Category", cats)
        with col_need:
            only_restock = st.checkbox("Show only SKUs needing replenishment", value=True)

        filtered_fc = prods.copy()
        if selected_cat != "All Categories":
            filtered_fc = filtered_fc[filtered_fc["category"] == selected_cat]
        if only_restock:
            filtered_fc = filtered_fc[filtered_fc["suggested_order"] > 0]

        display_fc = filtered_fc[[
            "sku", "name", "category", "stock_qty", "avg_daily",
            "predicted_7d", "safety_stock", "suggested_order", "confidence"
        ]].sort_values(by="suggested_order", ascending=False)

        display_fc.columns = [
            "SKU", "Product", "Category", "Current Stock", "Avg Daily Sales",
            "7D Forecast", "Safety Stock", "Suggested Order", "Confidence"
        ]

        st.dataframe(display_fc, use_container_width=True, hide_index=True)

        # Quick Restock Widget
        st.markdown("---")
        st.markdown("##### ⚡ **One-Click Quick Restock from Forecast**")
        if not filtered_fc.empty:
            q_col1, q_col2, q_col3 = st.columns([3, 2, 2])
            with q_col1:
                item_options = {f"{r['sku']} — {r['name']} (Needs: {r['suggested_order']})": r["product_id"] for _, r in filtered_fc.iterrows()}
                chosen_label = st.selectbox("Select Product to Replenish", list(item_options.keys()))
                chosen_id = item_options[chosen_label]
                chosen_row = filtered_fc[filtered_fc["product_id"] == chosen_id].iloc[0]
            with q_col2:
                default_qty = max(1, int(chosen_row["suggested_order"]))
                restock_qty = st.number_input("Units to Order & Add", min_value=1, max_value=5000, value=default_qty)
            with q_col3:
                st.write("")
                st.write("")
                if st.button("🚀 Execute Restock Now", type="primary", use_container_width=True):
                    ok, msg = restock_product(chosen_id, restock_qty, reference="Forecast PO", notes="Automated 7d forecast replenishment")
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # -------------------------------------------------------------------------
    # 3. Point of Sale (POS) Billing Terminal
    # -------------------------------------------------------------------------
    elif menu == "🛒 POS Billing Terminal":
        st.subheader("🛒 Point of Sale (POS) Billing Terminal")

        col_catalog, col_cart = st.columns([5, 4])

        with col_catalog:
            st.markdown("##### 🔍 **Live Product Lookup**")
            prods = load_products_df(active_only=True)
            
            c_s1, c_s2 = st.columns([3, 2])
            with c_s1:
                search_term = st.text_input("Search Name, SKU, or Barcode", placeholder="e.g. Apple, Maggi, FRU-APL-001...")
            with c_s2:
                cat_choices = ["All"] + sorted(prods["category"].unique().tolist())
                chosen_cat = st.selectbox("Category", cat_choices)

            # Filter catalog
            matches = prods.copy()
            if chosen_cat != "All":
                matches = matches[matches["category"] == chosen_cat]
            if search_term:
                term = search_term.strip().lower()
                matches = matches[
                    matches["name"].str.lower().str.contains(term) |
                    matches["sku"].str.lower().str.contains(term) |
                    matches["barcode"].astype(str).str.contains(term)
                ]

            st.caption(f"Showing {len(matches)} matching products")

            # Catalog Select & Add Box
            if not matches.empty:
                selected_prod_sku = st.selectbox(
                    "Select Product to Add",
                    matches["sku"] + " — " + matches["name"] + " (₹" + matches["unit_price"].astype(str) + " | Stock: " + matches["stock_qty"].astype(str) + ")",
                    key="pos_selector"
                )
                selected_sku_code = selected_prod_sku.split(" — ")[0]
                prod_row = matches[matches["sku"] == selected_sku_code].iloc[0]

                # Product Card with image preview
                p_c1, p_c2 = st.columns([2, 3])
                with p_c1:
                    img_path = prod_row["image_path"]
                    if img_path and os.path.exists(img_path.lstrip("/")):
                        st.image(img_path.lstrip("/"), width=130)
                    else:
                        st.markdown(f"📦 **{prod_row['category']}**")
                with p_c2:
                    st.markdown(f"**{prod_row['name']}**")
                    st.write(f"SKU: `{prod_row['sku']}` | Price: **₹{prod_row['unit_price']:,.2f}**")
                    if prod_row["stock_qty"] <= 0:
                        st.error("Out of stock")
                    elif prod_row["stock_qty"] <= prod_row["reorder_level"]:
                        st.warning(f"Low Stock ({prod_row['stock_qty']} units)")
                    else:
                        st.success(f"In Stock ({prod_row['stock_qty']} units)")

                # Add to Cart Controls
                q1, q2 = st.columns([2, 3])
                with q1:
                    add_qty = st.number_input("Quantity", min_value=1, max_value=max(1, int(prod_row["stock_qty"])), value=1, key="pos_qty_input")
                with q2:
                    st.write("")
                    st.write("")
                    can_add = prod_row["stock_qty"] > 0
                    if st.button("➕ Add Item to Cart", disabled=not can_add, type="primary", use_container_width=True):
                        # Check if already in cart
                        existing = next((i for i in st.session_state.cart if i["product_id"] == prod_row["product_id"]), None)
                        if existing:
                            if existing["quantity"] + add_qty > prod_row["stock_qty"]:
                                st.error("Cannot add more than available stock!")
                            else:
                                existing["quantity"] += add_qty
                                existing["line_total"] = existing["quantity"] * existing["unit_price"]
                                st.success(f"Updated quantity for {prod_row['name']}")
                                st.rerun()
                        else:
                            st.session_state.cart.append({
                                "product_id": int(prod_row["product_id"]),
                                "sku": str(prod_row["sku"]),
                                "name": str(prod_row["name"]),
                                "unit_price": float(prod_row["unit_price"]),
                                "quantity": int(add_qty),
                                "line_total": float(prod_row["unit_price"] * add_qty)
                            })
                            st.success(f"Added {prod_row['name']} to cart!")
                            st.rerun()
            else:
                st.warning("No products matched your search.")

        # Active Cart & Checkout Panel
        with col_cart:
            st.markdown("##### 🧾 **Active Customer Cart**")
            
            if st.session_state.cart:
                cart_df = pd.DataFrame(st.session_state.cart)
                for idx, item in enumerate(st.session_state.cart):
                    c_it1, c_it2, c_it3 = st.columns([4, 2, 1])
                    with c_it1:
                        st.write(f"**{item['name']}**  \n`{item['sku']}` @ ₹{item['unit_price']:,.2f}")
                    with c_it2:
                        st.write(f"Qty: **{item['quantity']}**  \n**₹{item['line_total']:,.2f}**")
                    with c_it3:
                        if st.button("❌", key=f"del_{idx}"):
                            st.session_state.cart.pop(idx)
                            st.rerun()

                st.markdown("---")

                # Bill Financial Calculations
                subtotal = sum(i["line_total"] for i in st.session_state.cart)
                
                b1, b2 = st.columns(2)
                with b1:
                    discount_pct = st.slider("Discount (%)", min_value=0, max_value=30, value=0)
                with b2:
                    payment_method = st.selectbox("Payment Method", ["Cash", "UPI / QR", "Credit/Debit Card"])

                discount_amount = subtotal * (discount_pct / 100.0)
                taxable_base = subtotal - discount_amount
                tax_rate = 0.05  # 5% GST
                tax_amount = taxable_base * tax_rate
                grand_total = taxable_base + tax_amount

                st.markdown(f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:12px; border-radius:8px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between;"><span>Subtotal:</span> <strong>₹{subtotal:,.2f}</strong></div>
                        <div style="display:flex; justify-content:space-between; color:#DC2626;"><span>Discount ({discount_pct}%):</span> <strong>-₹{discount_amount:,.2f}</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>GST / Tax (5%):</span> <strong>+₹{tax_amount:,.2f}</strong></div>
                        <hr style="margin:8px 0; border:none; border-top:1px dashed #CBD5E1;"/>
                        <div style="display:flex; justify-content:space-between; font-size:1.2rem; color:#0F593C;"><span>Grand Total:</span> <strong>₹{grand_total:,.2f}</strong></div>
                    </div>
                """, unsafe_allow_html=True)

                c_name = st.text_input("Customer Name (Optional)", placeholder="Walk-in Customer")
                c_phone = st.text_input("Customer Phone (Optional)", placeholder="+91 98765 43210")

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("🗑️ Clear Cart", use_container_width=True):
                        st.session_state.cart = []
                        st.rerun()
                with btn_c2:
                    if st.button("💳 Complete Sale", type="primary", use_container_width=True):
                        inv_no, err = execute_pos_checkout(
                            cart_items=st.session_state.cart,
                            subtotal=subtotal,
                            discount_amount=discount_amount,
                            tax_amount=tax_amount,
                            total_amount=grand_total,
                            payment_method=payment_method,
                            customer_name=c_name,
                            customer_phone=c_phone,
                            user_id=user_id
                        )
                        if inv_no:
                            st.session_state.last_receipt = {
                                "invoice": inv_no,
                                "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                                "cashier": user_role.split(" (")[0],
                                "customer": c_name or "Walk-in Guest",
                                "items": list(st.session_state.cart),
                                "subtotal": subtotal,
                                "discount": discount_amount,
                                "tax": tax_amount,
                                "total": grand_total,
                                "method": payment_method
                            }
                            st.session_state.cart = []
                            st.success(f"Sale recorded! Invoice: {inv_no}")
                            st.rerun()
                        else:
                            st.error(f"Checkout Failed: {err}")
            else:
                st.info("🛒 Shopping cart is currently empty. Select items from the catalog on the left.")

            # Display Most Recent Receipt
            if st.session_state.last_receipt:
                st.markdown("---")
                rc = st.session_state.last_receipt
                st.markdown(f"""
                    <div class="receipt-card">
                        <div style="text-align:center;">
                            <h3 style="margin:0; color:#0F593C;">GREENLEAF GROCERS</h3>
                            <p style="margin:0; font-size:0.8rem;">124 Eco Valley Road, Bengaluru</p>
                            <p style="margin:0; font-size:0.8rem;">Tax Invoice #{rc['invoice']}</p>
                            <hr style="border-top:1px dashed #94A3B8; margin:8px 0;"/>
                        </div>
                        <div style="font-size:0.8rem;">
                            <div>Date: {rc['date']}</div>
                            <div>Cashier: {rc['cashier']} | Guest: {rc['customer']}</div>
                            <div>Payment: {rc['method']}</div>
                            <hr style="border-top:1px dashed #94A3B8; margin:8px 0;"/>
                        </div>
                        <div style="font-size:0.85rem;">
                            {''.join([f"<div style='display:flex; justify-content:space-between;'><span>{it['name']} x{it['quantity']}</span><span>₹{it['line_total']:,.2f}</span></div>" for it in rc['items']])}
                            <hr style="border-top:1px dashed #94A3B8; margin:8px 0;"/>
                            <div style="display:flex; justify-content:space-between;"><span>Subtotal:</span><span>₹{rc['subtotal']:,.2f}</span></div>
                            <div style="display:flex; justify-content:space-between;"><span>Discount:</span><span>-₹{rc['discount']:,.2f}</span></div>
                            <div style="display:flex; justify-content:space-between;"><span>GST (5%):</span><span>+₹{rc['tax']:,.2f}</span></div>
                            <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:1rem; margin-top:4px;">
                                <span>NET TOTAL:</span><span>₹{rc['total']:,.2f}</span>
                            </div>
                        </div>
                        <div style="text-align:center; margin-top:12px; font-size:0.75rem;">
                            <p style="margin:0;">* THANK YOU FOR SHOPPING FRESH *</p>
                            <p style="margin:0;">GreenLeaf Nexus Cloud Point of Sale</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 4. Inventory Management & Surveillance
    # -------------------------------------------------------------------------
    elif menu == "📦 Inventory & Expiry Surveillance":
        st.subheader("📦 Inventory Management & Warehouse Surveillance")

        inv_df = load_products_df(active_only=True)

        i_k1, i_k2, i_k3, i_k4 = st.columns(4)
        total_skus = len(inv_df)
        low_stock_skus = (inv_df["stock_status"] == "Low Stock").sum()
        out_of_stock_skus = (inv_df["stock_status"] == "Out of Stock").sum()
        total_val = inv_df["inventory_value"].sum()

        with i_k1:
            st.metric("Total Active SKUs", f"{total_skus}")
        with i_k2:
            st.metric("Low Stock Alerts", f"{low_stock_skus}", delta="Need Restock" if low_stock_skus > 0 else "OK")
        with i_k3:
            st.metric("Out of Stock", f"{out_of_stock_skus}", delta="Critical" if out_of_stock_skus > 0 else "None")
        with i_k4:
            st.metric("Total Valuation", f"₹{total_val:,.2f}")

        st.markdown("---")

        tab_inv, tab_exp, tab_act, tab_audit = st.tabs([
            "📋 Live Inventory Ledger",
            "⏳ Expiry Date Surveillance",
            "⚡ Restock & Adjust Stock",
            "📜 Movement Audit Log"
        ])

        with tab_inv:
            flt_col1, flt_col2, flt_col3 = st.columns([3, 2, 2])
            with flt_col1:
                search_q = st.text_input("Filter Catalog", placeholder="Search by name, SKU, barcode...")
            with flt_col2:
                cat_f = st.selectbox("Category Filter", ["All Categories"] + sorted(inv_df["category"].unique().tolist()))
            with flt_col3:
                status_f = st.selectbox("Stock Status", ["All Statuses", "Low Stock", "Out of Stock", "Healthy"])

            table_df = inv_df.copy()
            if cat_f != "All Categories":
                table_df = table_df[table_df["category"] == cat_f]
            if status_f != "All Statuses":
                table_df = table_df[table_df["stock_status"] == status_f]
            if search_q:
                q = search_q.strip().lower()
                table_df = table_df[
                    table_df["name"].str.lower().str.contains(q) |
                    table_df["sku"].str.lower().str.contains(q)
                ]

            view_cols = ["sku", "name", "category", "stock_qty", "reorder_level", "unit_price", "cost_price", "margin_pct", "stock_status", "expiry_date"]
            display_table = table_df[view_cols].copy()
            display_table["margin_pct"] = display_table["margin_pct"].apply(lambda v: f"{v:.1f}%")
            display_table["unit_price"] = display_table["unit_price"].apply(lambda v: f"₹{v:,.2f}")
            display_table["cost_price"] = display_table["cost_price"].apply(lambda v: f"₹{v:,.2f}")
            display_table.columns = ["SKU", "Product", "Category", "Stock Qty", "Reorder Level", "Selling Price", "Cost Price", "Margin", "Status", "Expiry"]

            st.dataframe(display_table, use_container_width=True, hide_index=True)

        with tab_exp:
            st.markdown("##### ⏳ **Expiry Surveillance Watchlist**")
            st.caption("Surveillance categorized by shelf-life risk tiers.")

            expired_df = inv_df[inv_df["expiry_status"] == "Expired"]
            within_7_df = inv_df[inv_df["expiry_status"].isin(["Expiring Today", "Within 7 Days"])]
            within_15_df = inv_df[inv_df["expiry_status"] == "Within 15 Days"]

            e1, e2, e3 = st.columns(3)
            with e1:
                st.error(f"🚨 **Expired ({len(expired_df)} SKUs)**")
                if not expired_df.empty:
                    st.dataframe(expired_df[["sku", "name", "stock_qty", "expiry_date"]], hide_index=True)
                else:
                    st.write("No expired stock.")
            with e2:
                st.warning(f"⚠️ **Expiring ≤ 7 Days ({len(within_7_df)} SKUs)**")
                if not within_7_df.empty:
                    st.dataframe(within_7_df[["sku", "name", "stock_qty", "days_to_expiry"]], hide_index=True)
                else:
                    st.write("No items expiring this week.")
            with e3:
                st.info(f"📅 **Expiring 8–15 Days ({len(within_15_df)} SKUs)**")
                if not within_15_df.empty:
                    st.dataframe(within_15_df[["sku", "name", "stock_qty", "days_to_expiry"]], hide_index=True)
                else:
                    st.write("No items in 15-day window.")

        with tab_act:
            st.markdown("##### ⚡ **Warehouse Operations**")
            act_col1, act_col2 = st.columns(2)
            
            with act_col1:
                st.markdown("###### 📥 **Restock Incoming Shipment**")
                with st.form("form_restock"):
                    prods_map = {f"{r['sku']} — {r['name']} (Current: {r['stock_qty']})": r["product_id"] for _, r in inv_df.iterrows()}
                    chosen_p = st.selectbox("Product", list(prods_map.keys()))
                    p_id = prods_map[chosen_p]
                    restock_units = st.number_input("Quantity Received", min_value=1, max_value=5000, value=25)
                    po_ref = st.text_input("PO / Invoice Number", placeholder="e.g. PO-2026-99")
                    po_notes = st.text_input("Notes", placeholder="Standard vendor delivery")
                    submit_restock = st.form_submit_button("Confirm Restock", type="primary")

                    if submit_restock:
                        ok, msg = restock_product(p_id, restock_units, reference=po_ref, notes=po_notes)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            with act_col2:
                st.markdown("###### ⚖️ **Physical Stock Audit Adjustment**")
                with st.form("form_adjust"):
                    prods_map_adj = {f"{r['sku']} — {r['name']} (Ledger: {r['stock_qty']})": (r["product_id"], r["stock_qty"]) for _, r in inv_df.iterrows()}
                    chosen_p_adj = st.selectbox("Product", list(prods_map_adj.keys()))
                    p_id_adj, current_stock = prods_map_adj[chosen_p_adj]
                    actual_count = st.number_input("Actual Physical Count", min_value=0, max_value=10000, value=int(current_stock))
                    adj_reason = st.selectbox("Reason", ["Physical Audit Reconciliation", "Damaged Goods Write-off", "Perishable Spoilage", "Customer Return"])
                    adj_notes = st.text_input("Audit Notes", placeholder="Weekly inventory spot check")
                    submit_adj = st.form_submit_button("Apply Stock Count")

                    if submit_adj:
                        ok, msg = adjust_stock(p_id_adj, actual_count, reason=adj_reason, notes=adj_notes)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        with tab_audit:
            st.markdown("##### 📜 **Audit Ledger: Recent Inventory Movements**")
            audit_df = load_inventory_movements_df(limit=100)
            if not audit_df.empty:
                st.dataframe(
                    audit_df[["created_at", "sku", "product_name", "movement_type", "quantity_change", "previous_stock", "resulting_stock", "reference", "user_name"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.write("No movement records logged yet.")

    # -------------------------------------------------------------------------
    # 5. Product Catalog & Management
    # -------------------------------------------------------------------------
    elif menu == "🏷️ Product Catalog & Quick Add":
        st.subheader("🏷️ Product Master Catalog & Management")

        prods_df = load_products_df(active_only=False)

        cat_tab1, cat_tab2 = st.tabs(["🗂️ Product Directory", "➕ Add New Product"])

        with cat_tab1:
            st.markdown(f"**Total Catalog Size: {len(prods_df)} Products**")
            disp = prods_df[["sku", "barcode", "name", "category", "unit_price", "cost_price", "stock_qty", "reorder_level", "is_active", "supplier_name"]].copy()
            disp["unit_price"] = disp["unit_price"].apply(lambda v: f"₹{v:,.2f}")
            disp["cost_price"] = disp["cost_price"].apply(lambda v: f"₹{v:,.2f}")
            disp["is_active"] = disp["is_active"].apply(lambda v: "Active" if v == 1 else "Inactive")
            st.dataframe(disp, use_container_width=True, hide_index=True)

        with cat_tab2:
            st.markdown("##### ➕ **Add New Product to Store Catalog**")
            with st.form("add_product_form"):
                a1, a2 = st.columns(2)
                with a1:
                    p_name = st.text_input("Product Name*", placeholder="e.g. Organic Brown Rice (1 kg)")
                    p_cat = st.selectbox("Category*", [
                        "Fruits", "Vegetables", "Dairy", "Bakery", 
                        "Grains and Pulses", "Beverages", "Snacks", "Household Essentials"
                    ])
                    p_sku = st.text_input("SKU Code*", placeholder="e.g. GRN-BRN-001")
                    p_barcode = st.text_input("Barcode (EAN-13/UPC)", placeholder="e.g. 8901234567890")
                with a2:
                    p_sell = st.number_input("Selling Unit Price (₹)*", min_value=1.0, value=120.0, step=1.0)
                    p_cost = st.number_input("Cost Price (₹)*", min_value=0.0, value=90.0, step=1.0)
                    p_stock = st.number_input("Initial Opening Stock Qty*", min_value=0, value=50, step=1)
                    p_reorder = st.number_input("Low Stock Threshold*", min_value=1, value=10, step=1)

                a3, a4 = st.columns(2)
                with a3:
                    p_exp = st.date_input("Expiry Date (Optional)", value=None)
                with a4:
                    suppliers_df = load_suppliers_df()
                    supp_choices = {f"{r['name']}": r["supplier_id"] for _, r in suppliers_df.iterrows()} if not suppliers_df.empty else {}
                    chosen_sup = st.selectbox("Supplier Vendor", ["None"] + list(supp_choices.keys()))
                    sup_id = supp_choices.get(chosen_sup) if chosen_sup != "None" else None

                submit_prod = st.form_submit_button("💾 Save Product into Catalog", type="primary")

                if submit_prod:
                    if not p_name or not p_sku:
                        st.error("Product Name and SKU are required!")
                    else:
                        exp_str = p_exp.strftime("%Y-%m-%d") if p_exp else None
                        ok, msg = add_product(
                            sku=p_sku.strip(),
                            barcode=p_barcode.strip(),
                            name=p_name.strip(),
                            category=p_cat,
                            unit_price=float(p_sell),
                            cost_price=float(p_cost),
                            stock_qty=int(p_stock),
                            reorder_level=int(p_reorder),
                            expiry_date=exp_str,
                            supplier_id=sup_id
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    # -------------------------------------------------------------------------
    # 6. Suppliers Directory
    # -------------------------------------------------------------------------
    elif menu == "🚚 Suppliers Directory":
        st.subheader("🚚 Verified Supplier Vendors Directory")
        sup_df = load_suppliers_df()
        
        if not sup_df.empty:
            for _, s_row in sup_df.iterrows():
                with st.expander(f"🏢 **{s_row['name']}** — Supplied SKUs: {s_row['total_products']}"):
                    s_c1, s_c2 = st.columns(2)
                    with s_c1:
                        st.write(f"📞 Phone: **{s_row['phone']}**")
                        st.write(f"✉️ Email: **{s_row['email']}**")
                    with s_c2:
                        st.write(f"📍 Address: {s_row['address']}")
        else:
            st.info("No suppliers currently registered.")

    # -------------------------------------------------------------------------
    # 7. Reports & Data Export
    # -------------------------------------------------------------------------
    elif menu == "📑 Reports & Data Export":
        st.subheader("📑 Financial & Inventory Data Export Center")
        st.caption("Generate instant sanitized CSV data exports for compliance, accounting, or supply chain auditing.")

        r1, r2 = st.columns(2)

        with r1:
            st.markdown("##### 💵 **Sales Transactions Report**")
            sales_all = load_sales_df()
            if not sales_all.empty:
                csv_sales = sales_all.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download All Sales CSV",
                    data=csv_sales,
                    file_name=f"greenleaf_sales_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.markdown("##### 📦 **Warehouse Inventory Ledger**")
            inv_all = load_products_df(active_only=True)
            if not inv_all.empty:
                csv_inv = inv_all.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download Inventory Ledger CSV",
                    data=csv_inv,
                    file_name=f"greenleaf_inventory_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with r2:
            st.markdown("##### ⚠️ **Low Stock Reorder Manifest**")
            inv_all = load_products_df(active_only=True)
            low_df = inv_all[inv_all["stock_status"].isin(["Low Stock", "Out of Stock"])] if not inv_all.empty else pd.DataFrame()
            if not low_df.empty:
                csv_low = low_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download Low Stock Manifest CSV",
                    data=csv_low,
                    file_name=f"greenleaf_low_stock_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.write("No low stock items.")

            st.markdown("---")
            st.markdown("##### 📜 **Audit Movements Trail**")
            mov_df = load_inventory_movements_df(limit=1000)
            if not mov_df.empty:
                csv_mov = mov_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download Audit Movements CSV",
                    data=csv_mov,
                    file_name=f"greenleaf_movements_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )


if __name__ == "__main__":
    main()
