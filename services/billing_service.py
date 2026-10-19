import uuid
from datetime import datetime, date
from flask import current_app
from database import db
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from models.inventory_movement import InventoryMovement


class BillingService:
    @staticmethod
    def calculate_bill(cart_items_data, discount_percent=0.0, discount_amount=0.0):
        """
        Calculates authoritative totals for a set of cart items.
        cart_items_data: list of dicts with keys 'product_id' (or Product object) and 'quantity'.
        Returns a dict with line_items, subtotal, discount, taxable_amount, tax, and grand_total.
        """
        tax_rate = current_app.config.get("TAX_RATE", 0.05)
        max_discount_pct = current_app.config.get("MAX_DISCOUNT_PERCENT", 30.0)

        line_items = []
        subtotal = 0.0

        for item in cart_items_data:
            p_id = item["product_id"]
            qty = int(item["quantity"])
            if qty <= 0:
                raise ValueError(f"Quantity must be at least 1. Got {qty} for product ID {p_id}.")

            product = db.session.get(Product, p_id)
            if not product:
                raise ValueError(f"Product with ID {p_id} not found.")
            if not product.is_active:
                raise ValueError(f"Product '{product.name}' is inactive and cannot be sold.")

            line_subtotal = round(product.unit_price * qty, 2)
            subtotal += line_subtotal

            line_items.append({
                "product": product,
                "product_id": product.product_id,
                "name": product.name,
                "sku": product.sku,
                "quantity": qty,
                "unit_price": product.unit_price,
                "cost_price": product.cost_price,
                "available_stock": product.stock_qty,
                "line_total": line_subtotal,
            })

        subtotal = round(subtotal, 2)

        # Validate & calculate discount
        calculated_discount = 0.0
        if discount_percent > 0:
            if discount_percent > max_discount_pct:
                raise ValueError(f"Discount percentage cannot exceed {max_discount_pct}%.")
            calculated_discount = round(subtotal * (discount_percent / 100.0), 2)
        elif discount_amount > 0:
            if discount_amount > subtotal:
                raise ValueError("Discount amount cannot exceed the subtotal.")
            calculated_discount = round(discount_amount, 2)

        calculated_discount = min(calculated_discount, subtotal)
        taxable_amount = max(0.0, round(subtotal - calculated_discount, 2))
        tax = round(taxable_amount * tax_rate, 2)
        grand_total = round(taxable_amount + tax, 2)

        return {
            "line_items": line_items,
            "subtotal": subtotal,
            "discount_amount": calculated_discount,
            "taxable_amount": taxable_amount,
            "tax_rate": tax_rate,
            "tax_amount": tax,
            "grand_total": grand_total,
        }

    @staticmethod
    def generate_invoice_number():
        """Generates a unique invoice number format: GLN-YYYYMMDD-XXXXXX"""
        today_str = datetime.now().strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"GLN-{today_str}-{random_suffix}"

    @classmethod
    def process_checkout(
        cls,
        cashier_id,
        cart_items_data,
        discount_percent=0.0,
        discount_amount=0.0,
        payment_method="Cash",
        customer_name=None,
        customer_phone=None,
        notes=None,
    ):
        """
        Executes an atomic checkout:
        1. Validates inputs & cart
        2. Validates live stock
        3. Recalculates authoritative totals
        4. Creates Sale and SaleItems
        5. Deducts inventory & creates InventoryMovements
        6. Commits atomically or rolls back on any error
        """
        if not cart_items_data or len(cart_items_data) == 0:
            raise ValueError("Cannot checkout with an empty cart.")

        # Ensure payment method is valid
        valid_methods = {"Cash", "Card", "UPI", "Store Credit", "Digital Wallet"}
        if payment_method not in valid_methods:
            payment_method = "Cash"

        try:
            # Step 1 & 2: Calculate bill and lock down prices
            bill_calc = cls.calculate_bill(
                cart_items_data, discount_percent=discount_percent, discount_amount=discount_amount
            )

            # Step 3: Check stock availability with strict lock verification
            for item in bill_calc["line_items"]:
                product = item["product"]
                req_qty = item["quantity"]
                if product.stock_qty < req_qty:
                    raise ValueError(
                        f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}, Requested: {req_qty}."
                    )

            # Step 4: Create Sale Record
            invoice_num = cls.generate_invoice_number()
            sale = Sale(
                invoice_number=invoice_num,
                sale_date=date.today(),
                sale_time=datetime.now().time(),
                user_id=cashier_id,
                subtotal=bill_calc["subtotal"],
                discount_amount=bill_calc["discount_amount"],
                tax_amount=bill_calc["tax_amount"],
                total_amount=bill_calc["grand_total"],
                payment_method=payment_method,
                transaction_status="completed",
                customer_name=customer_name.strip() if customer_name else None,
                customer_phone=customer_phone.strip() if customer_phone else None,
                notes=notes.strip() if notes else None,
            )
            db.session.add(sale)
            db.session.flush()  # Populates sale.sale_id

            # Step 5: Create SaleItems, deduct inventory, and record movements
            for item in bill_calc["line_items"]:
                product = item["product"]
                qty = item["quantity"]

                # Proportion of discount for this line item
                line_discount = 0.0
                if bill_calc["subtotal"] > 0:
                    line_discount = round(
                        (item["line_total"] / bill_calc["subtotal"]) * bill_calc["discount_amount"], 2
                    )

                sale_item = SaleItem(
                    sale_id=sale.sale_id,
                    product_id=product.product_id,
                    product_name_snapshot=product.name,
                    quantity=qty,
                    unit_price=product.unit_price,
                    unit_cost_snapshot=product.cost_price,
                    discount_amount=line_discount,
                    line_total=item["line_total"],
                )
                db.session.add(sale_item)

                # Inventory deduction
                prev_stock = product.stock_qty
                new_stock = prev_stock - qty
                product.stock_qty = new_stock

                # Inventory movement record
                movement = InventoryMovement(
                    product_id=product.product_id,
                    user_id=cashier_id,
                    movement_type="sale",
                    quantity_change=-qty,
                    previous_stock=prev_stock,
                    resulting_stock=new_stock,
                    reference=invoice_num,
                    notes=f"POS Sale Invoice #{invoice_num}",
                )
                db.session.add(movement)

            # Commit all changes atomically
            db.session.commit()
            return sale

        except Exception as e:
            db.session.rollback()
            raise e
