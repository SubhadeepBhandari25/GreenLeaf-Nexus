import csv
import io
from datetime import datetime, date
from database import db
from models.product import Product
from models.supplier import Supplier
from models.inventory_movement import InventoryMovement
from models.sale import Sale
from models.sale_item import SaleItem


def sanitize_csv_cell(value):
    """
    Neutralizes CSV formula injection vulnerabilities (CWE-1236).
    If a cell begins with '=', '+', '-', or '@', prepends a single quote.
    """
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + str_val
    return str_val


class CsvService:
    EXPECTED_PRODUCT_HEADERS = [
        "sku",
        "name",
        "category",
        "unit_price",
        "cost_price",
        "stock_qty",
        "reorder_level",
        "expiry_date",
        "supplier_name",
        "barcode",
    ]

    @classmethod
    def import_products_csv(cls, file_stream, user_id=None):
        """
        Imports products from a CSV file.
        Returns a dict: {'total_rows': N, 'imported': M, 'errors': [{'row': r, 'error': msg}]}
        """
        content = file_stream.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")  # Handles BOM if present

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        if not rows:
            return {"total_rows": 0, "imported": 0, "errors": [{"row": 0, "error": "CSV file is empty."}]}

        raw_header = [h.strip().lower() for h in rows[0]]
        # Verify required headers
        required_cols = ["sku", "name", "category", "unit_price", "stock_qty"]
        missing = [col for col in required_cols if col not in raw_header]
        if missing:
            return {
                "total_rows": len(rows) - 1,
                "imported": 0,
                "errors": [{"row": 1, "error": f"Missing mandatory CSV headers: {', '.join(missing)}"}],
            }

        header_idx = {h: i for i, h in enumerate(raw_header)}
        errors = []
        new_products = []
        seen_skus_in_file = set()

        for row_num, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == "" for c in row):
                continue  # skip completely blank rows

            def get_val(col_name, default=""):
                idx = header_idx.get(col_name)
                if idx is not None and idx < len(row):
                    return row[idx].strip()
                return default

            sku = get_val("sku")
            name = get_val("name")
            category = get_val("category")
            unit_price_str = get_val("unit_price")
            cost_price_str = get_val("cost_price", "0")
            stock_qty_str = get_val("stock_qty", "0")
            reorder_lvl_str = get_val("reorder_level", "10")
            expiry_str = get_val("expiry_date")
            supplier_name = get_val("supplier_name")
            barcode = get_val("barcode")

            # Validation
            if not sku:
                errors.append({"row": row_num, "error": "SKU cannot be empty."})
                continue
            if not name:
                errors.append({"row": row_num, "error": f"Product name cannot be empty for SKU '{sku}'."})
                continue
            if not category:
                errors.append({"row": row_num, "error": f"Category cannot be empty for SKU '{sku}'."})
                continue

            # Duplicate SKU checks
            if sku in seen_skus_in_file:
                errors.append({"row": row_num, "error": f"Duplicate SKU '{sku}' within CSV file."})
                continue
            seen_skus_in_file.add(sku)

            existing_prod = Product.query.filter_by(sku=sku).first()
            if existing_prod:
                errors.append({"row": row_num, "error": f"Product with SKU '{sku}' already exists in database."})
                continue

            # Price & Stock validation
            try:
                unit_price = float(unit_price_str)
                if unit_price < 0:
                    raise ValueError()
            except ValueError:
                errors.append({"row": row_num, "error": f"Invalid unit_price '{unit_price_str}' (must be >= 0)."})
                continue

            try:
                cost_price = float(cost_price_str) if cost_price_str else 0.0
                if cost_price < 0:
                    raise ValueError()
            except ValueError:
                errors.append({"row": row_num, "error": f"Invalid cost_price '{cost_price_str}' (must be >= 0)."})
                continue

            try:
                stock_qty = int(stock_qty_str)
                if stock_qty < 0:
                    raise ValueError()
            except ValueError:
                errors.append({"row": row_num, "error": f"Invalid stock_qty '{stock_qty_str}' (must be an integer >= 0)."})
                continue

            try:
                reorder_level = int(reorder_lvl_str) if reorder_lvl_str else 10
                if reorder_level < 0:
                    raise ValueError()
            except ValueError:
                errors.append({"row": row_num, "error": f"Invalid reorder_level '{reorder_lvl_str}' (must be an integer >= 0)."})
                continue

            # Expiry date parsing
            expiry_date = None
            if expiry_str:
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                    try:
                        expiry_date = datetime.strptime(expiry_str, fmt).date()
                        break
                    except ValueError:
                        pass
                if not expiry_date:
                    errors.append({"row": row_num, "error": f"Invalid expiry_date '{expiry_str}'. Format YYYY-MM-DD expected."})
                    continue

            # Supplier handling
            supplier_id = None
            if supplier_name:
                supplier = Supplier.query.filter_by(name=supplier_name).first()
                if not supplier:
                    supplier = Supplier(name=supplier_name)
                    db.session.add(supplier)
                    db.session.flush()
                supplier_id = supplier.supplier_id

            product = Product(
                sku=sku,
                name=name,
                category=category,
                unit_price=unit_price,
                cost_price=cost_price,
                stock_qty=stock_qty,
                reorder_level=reorder_level,
                expiry_date=expiry_date,
                supplier_id=supplier_id,
                barcode=barcode if barcode else None,
                is_active=True,
            )
            new_products.append(product)

        # If any errors, or if valid products found, handle transaction
        if errors and not new_products:
            return {"total_rows": len(rows) - 1, "imported": 0, "errors": errors}

        try:
            for prod in new_products:
                db.session.add(prod)
                db.session.flush()
                # Create initial movement if stock > 0
                if prod.stock_qty > 0:
                    movement = InventoryMovement(
                        product_id=prod.product_id,
                        user_id=user_id,
                        movement_type="initial",
                        quantity_change=prod.stock_qty,
                        previous_stock=0,
                        resulting_stock=prod.stock_qty,
                        reference="CSV Import",
                        notes=f"Initial stock imported via CSV for SKU {prod.sku}",
                    )
                    db.session.add(movement)
            db.session.commit()
            return {"total_rows": len(rows) - 1, "imported": len(new_products), "errors": errors}
        except Exception as e:
            db.session.rollback()
            return {
                "total_rows": len(rows) - 1,
                "imported": 0,
                "errors": [{"row": 0, "error": f"Database transaction failed: {str(e)}"}],
            }

    @staticmethod
    def export_sales_csv(start_date=None, end_date=None):
        """Generates a sanitized CSV string of completed sales transactions."""
        query = Sale.query.filter_by(transaction_status="completed")
        if start_date:
            query = query.filter(Sale.sale_date >= start_date)
        if end_date:
            query = query.filter(Sale.sale_date <= end_date)
        sales = query.order_by(Sale.sale_date.desc(), Sale.sale_time.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Invoice Number",
            "Date",
            "Time",
            "Cashier",
            "Total Items",
            "Total Quantity",
            "Subtotal",
            "Discount",
            "Tax",
            "Grand Total",
            "Payment Method",
            "Customer Name",
            "Customer Phone",
        ])

        for s in sales:
            writer.writerow([
                sanitize_csv_cell(s.invoice_number),
                s.sale_date.strftime("%Y-%m-%d"),
                s.sale_time.strftime("%H:%M:%S") if s.sale_time else "",
                sanitize_csv_cell(s.cashier.full_name if s.cashier else "Unknown"),
                len(s.items),
                s.total_quantity,
                f"{s.subtotal:.2f}",
                f"{s.discount_amount:.2f}",
                f"{s.tax_amount:.2f}",
                f"{s.total_amount:.2f}",
                sanitize_csv_cell(s.payment_method),
                sanitize_csv_cell(s.customer_name or ""),
                sanitize_csv_cell(s.customer_phone or ""),
            ])
        return output.getvalue()

    @staticmethod
    def export_inventory_csv(filter_type="all"):
        """
        Generates a sanitized CSV string of product inventory.
        filter_type can be 'all', 'low_stock', or 'expiry_alerts'
        """
        query = Product.query.filter_by(is_active=True)
        if filter_type == "low_stock":
            query = query.filter(Product.stock_qty <= Product.reorder_level)
        elif filter_type == "expiry_alerts":
            today = date.today()
            target = today + timedelta(days=15)
            query = query.filter(Product.expiry_date.isnot(None), Product.expiry_date <= target)

        products = query.order_by(Product.category.asc(), Product.name.asc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "SKU",
            "Barcode",
            "Name",
            "Category",
            "Selling Price",
            "Cost Price",
            "Stock Qty",
            "Reorder Level",
            "Stock Status",
            "Expiry Date",
            "Expiry Status",
            "Supplier",
            "Retail Valuation",
            "Cost Valuation",
        ])

        for p in products:
            retail_val = p.stock_qty * p.unit_price
            cost_val = p.stock_qty * p.cost_price
            writer.writerow([
                sanitize_csv_cell(p.sku),
                sanitize_csv_cell(p.barcode or ""),
                sanitize_csv_cell(p.name),
                sanitize_csv_cell(p.category),
                f"{p.unit_price:.2f}",
                f"{p.cost_price:.2f}",
                p.stock_qty,
                p.reorder_level,
                p.stock_status,
                p.expiry_date.strftime("%Y-%m-%d") if p.expiry_date else "",
                p.expiry_status,
                sanitize_csv_cell(p.supplier.name if p.supplier else ""),
                f"{retail_val:.2f}",
                f"{cost_val:.2f}",
            ])
        return output.getvalue()
