import sys
from datetime import datetime, date, timedelta
from app import create_app
from database import db
from models.product import Product
from models.supplier import Supplier
from models.inventory_movement import InventoryMovement
from models.user import User

INDIAN_SNACKS = [
    ("SNK-BHU-011", "Haldiram's Nagpur Bhujia Sev (200g)", "Snacks", 55.0, 38.0, 20, "8904004400210", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80", "Crispy moth pulse and besan sev seasoned with fragrant Indian spices."),
    ("SNK-ALU-012", "Haldiram's Aloo Bhujia Spicy Mint (220g)", "Snacks", 60.0, 42.0, 25, "8904004400227", "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=400&q=80", "Crunchy potato mint sev made with fresh potatoes, gram pulse, and refreshing mint spices."),
    ("SNK-KHM-013", "Haldiram's Khatta Meetha Mixture (200g)", "Snacks", 55.0, 39.0, 15, "8904004400234", "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=400&q=80", "Sweet and tart namkeen mixture with crispy sago pearls, green peas, and spiced sev."),
    ("SNK-AIO-014", "Haldiram's All-In-One Royal Mixture (200g)", "Snacks", 65.0, 45.0, 15, "8904004400241", "https://images.unsplash.com/photo-1541592106381-b31e9677c0e5?auto=format&fit=crop&w=400&q=80", "Medley of roasted nuts, lentils, raisins, and savory sev with aromatic royal spices."),
    ("SNK-MNG-015", "Haldiram's Salted Moong Dal (200g)", "Snacks", 50.0, 34.0, 15, "8904004400258", "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?auto=format&fit=crop&w=400&q=80", "Golden fried, salted split yellow moong lentils — crunchy, savory, and protein-packed."),
    ("SNK-NAV-016", "Haldiram's Navrattan Spicy Mixture (200g)", "Snacks", 55.0, 38.0, 15, "8904004400265", "https://images.unsplash.com/photo-1613728913341-8f289d0c266e?auto=format&fit=crop&w=400&q=80", "Fiery nine-gem mixture of seasoned chickpea flour noodles, lentils, and nuts."),
    ("SNK-KUR-017", "Kurkure Masala Munch Crunchy Twisteez (90g)", "Snacks", 20.0, 14.0, 30, "8901491102148", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80", "India's favorite crunchy puffed rice and corn curls spiced with signature chatpata masala."),
    ("SNK-KUR-018", "Kurkure Solid Masti Masala Twisteez (85g)", "Snacks", 20.0, 14.0, 20, "8901491102155", "https://images.unsplash.com/photo-1621447504864-d8686e12698c?auto=format&fit=crop&w=400&q=80", "Teeth-gripping spiral rolls loaded with bold chilli and mango powder zing."),
    ("SNK-LAY-019", "Lay's India's Magic Masala Potato Chips (52g)", "Snacks", 20.0, 14.0, 35, "8901491101851", "https://images.unsplash.com/photo-1527842891421-42eec6e703ea?auto=format&fit=crop&w=400&q=80", "The iconic blue-pack potato chips dusted with fiery coriander, cumin, dry mango, and chilli masala."),
    ("SNK-LAY-020", "Lay's West Indies Hot 'n' Sweet Chilli (52g)", "Snacks", 20.0, 14.0, 25, "8901491101868", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80", "Sweet and spicy fusion potato chips flavored with exotic Caribbean heat."),
    ("SNK-BNG-021", "Bingo! Mad Angles Achaari Masti (66g)", "Snacks", 20.0, 14.0, 25, "8901725134105", "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=400&q=80", "Crispy corn triangles infused with the bold, tangy bite of traditional mango pickle."),
    ("SNK-BNG-022", "Bingo! Tedhe Medhe Masala Tadka Crunch (90g)", "Snacks", 20.0, 14.0, 25, "8901725134112", "https://images.unsplash.com/photo-1621447504864-d8686e12698c?auto=format&fit=crop&w=400&q=80", "Spindle-shaped zigzag crunchy snacks tossed in a lip-smacking Indian spice mix."),
    ("SNK-PRL-023", "Parle-G Gold Real Milk & Wheat Biscuits (250g)", "Snacks", 30.0, 22.0, 40, "8901719101014", "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80", "India's most beloved chai-time biscuit made with good wheat flour, milk, and golden glucose."),
    ("SNK-BRT-024", "Britannia Good Day Rich Butter Cookies (200g)", "Snacks", 40.0, 28.0, 30, "8901063101018", "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=400&q=80", "Iconic smile-patterned buttery cookies with a melt-in-mouth golden crunch."),
    ("SNK-BRT-025", "Britannia Bourbon Original Choco Cream (150g)", "Snacks", 35.0, 24.0, 25, "8901063101025", "https://images.unsplash.com/photo-1590080875515-8a3a8dc5735e?auto=format&fit=crop&w=400&q=80", "Sugar-crusted crunchy dark chocolate biscuits filled with silky cocoa cream."),
    ("SNK-BRT-026", "Britannia Marie Gold Tea Time Biscuits (300g)", "Snacks", 35.0, 24.0, 25, "8901063101032", "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=400&q=80", "Crisp, light, low-fat tea biscuits enriched with essential vitamins and minerals."),
    ("SNK-SNF-027", "Sunfeast Dark Fantasy Choco Fills Cookies (75g)", "Snacks", 40.0, 27.0, 20, "8901725134204", "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?auto=format&fit=crop&w=400&q=80", "Crispy golden crust encapsulating a molten lava center of pure melted chocolate."),
    ("SNK-GUL-028", "Haldiram's Nagpur Royal Gulab Jamun (1 kg Tin)", "Snacks", 240.0, 170.0, 10, "8904004400272", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80", "Soft, spongy cottage cheese and mawa dumplings soaked in aromatic rose and saffron sugar syrup."),
    ("SNK-SOA-029", "Haldiram's Desi Ghee Soan Papdi (250g)", "Snacks", 90.0, 62.0, 12, "8904004400289", "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=400&q=80", "Flaky, melt-in-mouth traditional Indian sweet topped with sliced pistachios and almonds."),
    ("SNK-MAG-030", "Maggi 2-Minute Masala Instant Noodles (4-Pack, 280g)", "Snacks", 56.0, 42.0, 35, "8901058852331", "https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=400&q=80", "India's favorite comfort snack — fortified with iron and made with signature roasted spices tastemaker."),
    ("SNK-LIJ-031", "Lijjat Udad Dal Black Pepper Papad (200g)", "Snacks", 75.0, 52.0, 15, "8906008120017", "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=400&q=80", "Sun-dried authentic urad dal papad seasoned with crushed black pepper and hing."),
    ("SNK-MAK-032", "Tata Sampann Roasted Phool Makhana Rock Salt (100g)", "Snacks", 140.0, 98.0, 12, "8901011120038", "https://images.unsplash.com/photo-1508061252966-f72fb7044435?auto=format&fit=crop&w=400&q=80", "Crunchy non-fried lotus seeds roasted in olive oil and Himalayan pink rock salt."),
    ("SNK-BLJ-033", "Balaji Wafers Masala Masti Potato Chips (100g)", "Snacks", 30.0, 20.0, 20, "8906010501149", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80", "Thin cut crispy Gujarati style potato wafers dusted with zesty dry mango and chili seasoning."),
    ("SNK-SAM-034", "Haldiram's Cocktail Punjabi Samosa Bites (400g)", "Snacks", 135.0, 95.0, 10, "8904004400296", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80", "Flaky pastry pockets stuffed with spiced potatoes, green peas, and cashews."),
    ("SNK-CAD-036", "Cadbury Dairy Milk Silk Chocolate (150g)", "Snacks", 175.0, 130.0, 15, "7622201732011", "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=400&q=80", "Irresistibly silky, rich, creamy milk chocolate made with a glass and a half of pure dairy milk."),
    ("SNK-BAK-037", "Chitale Bandhu Authentic Pune Bakarwadi (250g)", "Snacks", 95.0, 68.0, 15, "8906012440019", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80", "World-famous sweet, spicy, and tangy rolled spiral savory snack from Pune, Maharashtra."),
]


def populate_snacks():
    app = create_app("development")
    with app.app_context():
        admin = User.query.filter_by(role="admin").first()
        admin_id = admin.user_id if admin else 1

        supplier = Supplier.query.filter(Supplier.name.ilike("%GreenLife%")).first()
        if not supplier:
            supplier = Supplier.query.first()
        supplier_id = supplier.supplier_id if supplier else None

        expiry_date = date.today() + timedelta(days=240)
        added_count = 0
        updated_count = 0

        for sku, name, category, unit_price, cost_price, reorder_lvl, barcode, img_url, desc in INDIAN_SNACKS:
            existing = Product.query.filter((Product.sku == sku) | (Product.barcode == barcode)).first()
            if existing:
                existing.name = name
                existing.category = category
                existing.unit_price = unit_price
                existing.cost_price = cost_price
                existing.reorder_level = reorder_lvl
                existing.barcode = barcode
                existing.image_path = img_url
                existing.description = desc
                existing.is_active = True
                if existing.stock_qty <= 0:
                    existing.stock_qty = 50
                updated_count += 1
            else:
                initial_stock = 45 + (hash(sku) % 35)
                prod = Product(
                    sku=sku,
                    barcode=barcode,
                    name=name,
                    description=desc,
                    category=category,
                    unit_price=unit_price,
                    cost_price=cost_price,
                    stock_qty=initial_stock,
                    reorder_level=reorder_lvl,
                    expiry_date=expiry_date,
                    supplier_id=supplier_id,
                    image_path=img_url,
                    is_active=True,
                )
                db.session.add(prod)
                db.session.flush()

                # Add opening stock inventory movement
                movement = InventoryMovement(
                    product_id=prod.product_id,
                    user_id=admin_id,
                    movement_type="initial",
                    quantity_change=initial_stock,
                    previous_stock=0,
                    resulting_stock=initial_stock,
                    reference="Indian Snacks Catalog Expansion",
                    notes="Direct intake of popular Indian snacks & namkeen catalog",
                    created_at=datetime.utcnow(),
                )
                db.session.add(movement)
                added_count += 1

        db.session.commit()
        print(f"Successfully processed Indian Snacks: {added_count} newly added, {updated_count} updated.")
        total_prods = Product.query.count()
        print(f"Total active products in database now: {total_prods}")


if __name__ == "__main__":
    populate_snacks()
