import os
import random
import sys
from datetime import datetime, date, time, timedelta
from app import create_app
from database import db
from models.user import User
from models.supplier import Supplier
from models.product import Product
from models.sale import Sale
from models.sale_item import SaleItem
from models.inventory_movement import InventoryMovement
from models.audit_log import AuditLog

# Seed definitions
CATEGORIES = [
    "Fruits",
    "Vegetables",
    "Dairy",
    "Bakery",
    "Grains and Pulses",
    "Beverages",
    "Snacks",
    "Household Essentials",
]

SUPPLIERS_DATA = [
    {
        "name": "FreshHarvest Farm Producer Co.",
        "phone": "+91 98451 12345",
        "email": "orders@freshharvestfarms.in",
        "address": "Survey 45, Devanahalli Agro Belt, Bengaluru Rural - 562110",
    },
    {
        "name": "DairyPure Agro Ventures",
        "phone": "+91 98452 23456",
        "email": "procurement@dairypure.com",
        "address": "Plot 12B, KIADB Industrial Area, Doddaballapura - 561203",
    },
    {
        "name": "GoldenGrain Wholesale Distributors",
        "phone": "+91 98453 34567",
        "email": "sales@goldengrainwholesale.in",
        "address": "APMC Yard Market Block C, Yeshwantpur, Bengaluru - 560022",
    },
    {
        "name": "SunSpire Bakery & Confectionery",
        "phone": "+91 98454 45678",
        "email": "supply@sunspirebakers.com",
        "address": "4th Phase, Peenya Industrial Area, Bengaluru - 560058",
    },
    {
        "name": "GreenLife Consumer Goods Pvt Ltd",
        "phone": "+91 98455 56789",
        "email": "info@greenlifeconsumer.com",
        "address": "Hosur Road Logistics Hub, Electronic City, Bengaluru - 560100",
    },
]

PRODUCTS_CATALOG = [
    # Fruits (8)
    ("FRU-APL-001", "Royal Gala Apples (1 kg)", "Fruits", 180.0, 130.0, 15, "8901001", "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=400&q=80"),
    ("FRU-BAN-002", "Robusta Bananas (1 dozen)", "Fruits", 55.0, 35.0, 20, "8901002", "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=400&q=80"),
    ("FRU-ORG-003", "Nagpur Sweet Oranges (1 kg)", "Fruits", 90.0, 62.0, 12, "8901003", "https://images.unsplash.com/photo-1582979512210-99b6a53386f9?auto=format&fit=crop&w=400&q=80"),
    ("FRU-MNG-004", "Alphonso Mangoes Premium (1 kg)", "Fruits", 350.0, 260.0, 10, "8901004", "https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=400&q=80"),
    ("FRU-PMP-005", "Fresh Pomegranate (1 kg)", "Fruits", 160.0, 115.0, 10, "8901005", "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=400&q=80"),
    ("FRU-PAP-006", "Farm Fresh Papaya (1 pc)", "Fruits", 45.0, 28.0, 8, "8901006", "https://images.unsplash.com/photo-1517282009859-f000ec3b26fe?auto=format&fit=crop&w=400&q=80"),
    ("FRU-WTM-007", "Kiran Watermelon (1 pc)", "Fruits", 65.0, 40.0, 10, "8901007", "https://images.unsplash.com/photo-1587049352846-4a222e784d38?auto=format&fit=crop&w=400&q=80"),
    ("FRU-GRP-008", "Thompson Seedless Grapes (500g)", "Fruits", 85.0, 58.0, 12, "8901008", "https://images.unsplash.com/photo-1537640538966-79f369143f8f?auto=format&fit=crop&w=400&q=80"),
    
    # Vegetables (8)
    ("VEG-TOM-001", "Farm Fresh Tomatoes (1 kg)", "Vegetables", 35.0, 22.0, 25, "8902001", "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=400&q=80"),
    ("VEG-POT-002", "Jyoti Potatoes (1 kg)", "Vegetables", 32.0, 20.0, 30, "8902002", "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=400&q=80"),
    ("VEG-ONN-003", "Nasik Red Onions (1 kg)", "Vegetables", 42.0, 28.0, 25, "8902003", "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?auto=format&fit=crop&w=400&q=80"),
    ("VEG-SPN-004", "Fresh Palak Spinach (1 bunch)", "Vegetables", 25.0, 14.0, 15, "8902004", "https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=400&q=80"),
    ("VEG-CAR-005", "Ooty Tender Carrots (500g)", "Vegetables", 40.0, 26.0, 12, "8902005", "https://images.unsplash.com/photo-1598170845058-32b9d6a5c317?auto=format&fit=crop&w=400&q=80"),
    ("VEG-CAP-006", "Green Bell Capsicum (500g)", "Vegetables", 50.0, 32.0, 10, "8902006", "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?auto=format&fit=crop&w=400&q=80"),
    ("VEG-CBR-007", "Fresh Green Cucumber (1 kg)", "Vegetables", 38.0, 24.0, 12, "8902007", "https://images.unsplash.com/photo-1604977042946-1eecc30f269e?auto=format&fit=crop&w=400&q=80"),
    ("VEG-CAU-008", "Fresh Cauliflower (1 pc)", "Vegetables", 45.0, 28.0, 10, "8902008", "https://images.unsplash.com/photo-1568584711075-3d021a7c3ca3?auto=format&fit=crop&w=400&q=80"),

    # Dairy (7)
    ("DAI-MLK-001", "Full Cream Cow Milk (1 Litre)", "Dairy", 68.0, 54.0, 30, "8903001", "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=400&q=80"),
    ("DAI-TON-002", "Toned Homogenized Milk (1 Litre)", "Dairy", 54.0, 44.0, 25, "8903002", "https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=400&q=80"),
    ("DAI-CUR-003", "Natural Set Curd (500g)", "Dairy", 40.0, 30.0, 20, "8903003", "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=400&q=80"),
    ("DAI-PAN-004", "Fresh Malai Paneer (200g)", "Dairy", 95.0, 72.0, 15, "8903004", "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=400&q=80"),
    ("DAI-BUT-005", "Salted Table Butter (100g)", "Dairy", 58.0, 46.0, 15, "8903005", "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?auto=format&fit=crop&w=400&q=80"),
    ("DAI-CHS-006", "Cheddar Cheese Slices (200g)", "Dairy", 145.0, 112.0, 10, "8903006", "https://images.unsplash.com/photo-1618164435735-413d3b066c9a?auto=format&fit=crop&w=400&q=80"),
    ("DAI-GHE-007", "Pure Desi Cow Ghee (500ml)", "Dairy", 360.0, 285.0, 8, "8903007", "https://images.unsplash.com/photo-1628088062854-d1870b4553da?auto=format&fit=crop&w=400&q=80"),

    # Bakery (7)
    ("BAK-BRD-001", "Whole Wheat Brown Bread (400g)", "Bakery", 45.0, 32.0, 15, "8904001", "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=400&q=80"),
    ("BAK-MIL-002", "Sweet Milk Bread Loaf (400g)", "Bakery", 40.0, 28.0, 15, "8904002", "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?auto=format&fit=crop&w=400&q=80"),
    ("BAK-PAV-003", "Fresh Ladi Pav (Pack of 6)", "Bakery", 30.0, 18.0, 20, "8904003", "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?auto=format&fit=crop&w=400&q=80"),
    ("BAK-RUS-004", "Crispy Elaichi Rusk (300g)", "Bakery", 60.0, 42.0, 12, "8904004", "https://images.unsplash.com/photo-1590080875515-8a3a8dc5735e?auto=format&fit=crop&w=400&q=80"),
    ("BAK-CRO-005", "Butter Croissant (Pack of 2)", "Bakery", 90.0, 60.0, 8, "8904005", "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=400&q=80"),
    ("BAK-BUN-006", "Fruit Bun with Tutti Frutti", "Bakery", 25.0, 15.0, 15, "8904006", "https://images.unsplash.com/photo-1568252542512-9fe8fe9c87bb?auto=format&fit=crop&w=400&q=80"),
    ("BAK-MUF-007", "Choco Chip Muffins (Pack of 2)", "Bakery", 75.0, 50.0, 10, "8904007", "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?auto=format&fit=crop&w=400&q=80"),

    # Grains & Pulses (7)
    ("GRN-RIC-001", "Sona Masoori Raw Rice (5 kg)", "Grains and Pulses", 340.0, 275.0, 15, "8905001", "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=400&q=80"),
    ("GRN-BAS-002", "Royal Basmati Rice Aged (1 kg)", "Grains and Pulses", 140.0, 105.0, 12, "8905002", "https://images.unsplash.com/photo-1536304993881-ff6e9eefa2a6?auto=format&fit=crop&w=400&q=80"),
    ("GRN-AAT-003", "Chakki Fresh Whole Wheat Atta (5 kg)", "Grains and Pulses", 245.0, 195.0, 15, "8905003", "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=400&q=80"),
    ("GRN-TOU-004", "Unpolished Toor Dal (1 kg)", "Grains and Pulses", 165.0, 130.0, 15, "8905004", "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=400&q=80"),
    ("GRN-MOO-005", "Yellow Moong Dal Split (1 kg)", "Grains and Pulses", 135.0, 104.0, 12, "8905005", "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?auto=format&fit=crop&w=400&q=80"),
    ("GRN-CHZ-006", "Kabuli Chana Chickpeas (1 kg)", "Grains and Pulses", 145.0, 110.0, 10, "8905006", "https://images.unsplash.com/photo-1585996746979-9134a625bc20?auto=format&fit=crop&w=400&q=80"),
    ("GRN-POH-007", "Thick Rice Poha (1 kg)", "Grains and Pulses", 65.0, 46.0, 15, "8905007", "https://images.unsplash.com/photo-1613728913341-8f289d0c266e?auto=format&fit=crop&w=400&q=80"),

    # Beverages (6)
    ("BEV-TEA-001", "Assam CTC Leaf Tea (500g)", "Beverages", 195.0, 145.0, 12, "8906001", "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=400&q=80"),
    ("BEV-COF-002", "South Indian Filter Coffee (200g)", "Beverages", 125.0, 92.0, 10, "8906002", "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=400&q=80"),
    ("BEV-GRN-003", "Organic Green Tea Bags (25 pcs)", "Beverages", 180.0, 132.0, 10, "8906003", "https://images.unsplash.com/photo-1627435601361-ec25f5b1d0e5?auto=format&fit=crop&w=400&q=80"),
    ("BEV-JUC-004", "Real Alphonso Mango Juice (1L)", "Beverages", 110.0, 84.0, 15, "8906004", "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=400&q=80"),
    ("BEV-APP-005", "Sparkling Apple Fizz (600ml)", "Beverages", 40.0, 28.0, 20, "8906005", "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=400&q=80"),
    ("BEV-WAT-006", "Natural Spring Mineral Water (1L)", "Beverages", 20.0, 12.0, 30, "8906006", "https://images.unsplash.com/photo-1548839140-29a749e1bc4e?auto=format&fit=crop&w=400&q=80"),

    # Snacks (6)
    ("SNK-POT-001", "Classic Salted Potato Chips (100g)", "Snacks", 35.0, 24.0, 20, "8907001", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BIS-002", "Digestive High Fibre Biscuits", "Snacks", 45.0, 32.0, 18, "8907002", "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80"),
    ("SNK-NAM-003", "Spicy Aloo Bhujia Sev (200g)", "Snacks", 55.0, 38.0, 15, "8907003", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80"),
    ("SNK-NUT-004", "Roasted Salted Almonds (200g)", "Snacks", 240.0, 185.0, 8, "8907004", "https://images.unsplash.com/photo-1508061252966-f72fb7044435?auto=format&fit=crop&w=400&q=80"),
    ("SNK-CAS-005", "W240 Grade Cashew Nuts (200g)", "Snacks", 260.0, 205.0, 8, "8907005", "https://images.unsplash.com/photo-1569460275918-7091f919e220?auto=format&fit=crop&w=400&q=80"),
    ("SNK-POP-006", "Golden Butter Popcorn (100g)", "Snacks", 40.0, 26.0, 15, "8907006", "https://images.unsplash.com/photo-1578849278619-e73505e9610f?auto=format&fit=crop&w=400&q=80"),

    # Household Essentials (6)
    ("HOU-DET-001", "Matic Laundry Detergent Liquid (1L)", "Household Essentials", 220.0, 165.0, 10, "8908001", "https://images.unsplash.com/photo-1585421514738-01798e348b17?auto=format&fit=crop&w=400&q=80"),
    ("HOU-DSH-002", "Lemon Dishwash Liquid Gel (750ml)", "Household Essentials", 135.0, 98.0, 12, "8908002", "https://images.unsplash.com/photo-1603555501671-8f96b3fce8b5?auto=format&fit=crop&w=400&q=80"),
    ("HOU-SOAP-003", "Moisturizing Bath Soap (Pack of 4)", "Household Essentials", 160.0, 118.0, 15, "8908003", "https://images.unsplash.com/photo-1607006314175-926d83ec8df5?auto=format&fit=crop&w=400&q=80"),
    ("HOU-FLR-004", "Disinfectant Surface Cleaner (1L)", "Household Essentials", 145.0, 106.0, 12, "8908004", "https://images.unsplash.com/photo-1584813470613-5b1c1cad3d69?auto=format&fit=crop&w=400&q=80"),
    ("HOU-TIS-005", "Soft 2-Ply Kitchen Towels (Pack of 2)", "Household Essentials", 90.0, 62.0, 15, "8908005", "https://images.unsplash.com/photo-1584556812952-905ffd0c611a?auto=format&fit=crop&w=400&q=80"),
    ("HOU-TRH-006", "Biodegradable Garbage Bags (30 pcs)", "Household Essentials", 85.0, 56.0, 15, "8908006", "https://images.unsplash.com/photo-1618477461853-cf6ed80faba5?auto=format&fit=crop&w=400&q=80"),

    # Open Food Facts Real-World Retail Database Products (6)
    ("SNK-NUT-007", "Nutella Hazelnut Spread with Cocoa (400g)", "Snacks", 380.0, 290.0, 10, "3017620422003", "https://images.openfoodfacts.org/images/products/301/762/042/2003/front_en.879.400.jpg"),
    ("BEV-COK-007", "Coca-Cola Original Taste (500ml)", "Beverages", 40.0, 28.0, 25, "5449000000996", "https://images.openfoodfacts.org/images/products/544/900/000/0996/front_en.1129.400.jpg"),
    ("SNK-ORE-008", "Oreo Chocolate Sandwich Cookies (120g)", "Snacks", 35.0, 24.0, 20, "7622210449283", "https://images.openfoodfacts.org/images/products/762/221/044/9283/front_en.605.400.jpg"),
    ("SNK-LAY-009", "Lay's Classic Salted Potato Chips (52g)", "Snacks", 20.0, 14.0, 25, "8901491101837", "https://images.openfoodfacts.org/images/products/890/149/110/1837/front_en.26.400.jpg"),
    ("GRN-THI-008", "Thai Peanut Stir-Fry Noodle Kit (240g)", "Grains and Pulses", 195.0, 140.0, 10, "737628064502", "https://images.openfoodfacts.org/images/products/073/762/806/4502/front_en.6.400.jpg"),
    ("SNK-KIN-010", "Kinder Joy with Surprise Toy (20g)", "Snacks", 50.0, 36.0, 15, "8000500310427", "https://images.openfoodfacts.org/images/products/800/050/031/0427/front_en.108.400.jpg"),
    
    # Authentic Indian Snacks & Namkeen Catalog (26 items)
    ("SNK-BHU-011", "Haldiram's Nagpur Bhujia Sev (200g)", "Snacks", 55.0, 38.0, 20, "8904004400210", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80"),
    ("SNK-ALU-012", "Haldiram's Aloo Bhujia Spicy Mint (220g)", "Snacks", 60.0, 42.0, 25, "8904004400227", "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=400&q=80"),
    ("SNK-KHM-013", "Haldiram's Khatta Meetha Mixture (200g)", "Snacks", 55.0, 39.0, 15, "8904004400234", "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=400&q=80"),
    ("SNK-AIO-014", "Haldiram's All-In-One Royal Mixture (200g)", "Snacks", 65.0, 45.0, 15, "8904004400241", "https://images.unsplash.com/photo-1541592106381-b31e9677c0e5?auto=format&fit=crop&w=400&q=80"),
    ("SNK-MNG-015", "Haldiram's Salted Moong Dal (200g)", "Snacks", 50.0, 34.0, 15, "8904004400258", "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?auto=format&fit=crop&w=400&q=80"),
    ("SNK-NAV-016", "Haldiram's Navrattan Spicy Mixture (200g)", "Snacks", 55.0, 38.0, 15, "8904004400265", "https://images.unsplash.com/photo-1613728913341-8f289d0c266e?auto=format&fit=crop&w=400&q=80"),
    ("SNK-KUR-017", "Kurkure Masala Munch Crunchy Twisteez (90g)", "Snacks", 20.0, 14.0, 30, "8901491102148", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80"),
    ("SNK-KUR-018", "Kurkure Solid Masti Masala Twisteez (85g)", "Snacks", 20.0, 14.0, 20, "8901491102155", "https://images.unsplash.com/photo-1621447504864-d8686e12698c?auto=format&fit=crop&w=400&q=80"),
    ("SNK-LAY-019", "Lay's India's Magic Masala Potato Chips (52g)", "Snacks", 20.0, 14.0, 35, "8901491101851", "https://images.unsplash.com/photo-1527842891421-42eec6e703ea?auto=format&fit=crop&w=400&q=80"),
    ("SNK-LAY-020", "Lay's West Indies Hot 'n' Sweet Chilli (52g)", "Snacks", 20.0, 14.0, 25, "8901491101868", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BNG-021", "Bingo! Mad Angles Achaari Masti (66g)", "Snacks", 20.0, 14.0, 25, "8901725134105", "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BNG-022", "Bingo! Tedhe Medhe Masala Tadka Crunch (90g)", "Snacks", 20.0, 14.0, 25, "8901725134112", "https://images.unsplash.com/photo-1621447504864-d8686e12698c?auto=format&fit=crop&w=400&q=80"),
    ("SNK-PRL-023", "Parle-G Gold Real Milk & Wheat Biscuits (250g)", "Snacks", 30.0, 22.0, 40, "8901719101014", "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BRT-024", "Britannia Good Day Rich Butter Cookies (200g)", "Snacks", 40.0, 28.0, 30, "8901063101018", "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BRT-025", "Britannia Bourbon Original Choco Cream (150g)", "Snacks", 35.0, 24.0, 25, "8901063101025", "https://images.unsplash.com/photo-1590080875515-8a3a8dc5735e?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BRT-026", "Britannia Marie Gold Tea Time Biscuits (300g)", "Snacks", 35.0, 24.0, 25, "8901063101032", "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=400&q=80"),
    ("SNK-SNF-027", "Sunfeast Dark Fantasy Choco Fills Cookies (75g)", "Snacks", 40.0, 27.0, 20, "8901725134204", "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?auto=format&fit=crop&w=400&q=80"),
    ("SNK-GUL-028", "Haldiram's Nagpur Royal Gulab Jamun (1 kg Tin)", "Snacks", 240.0, 170.0, 10, "8904004400272", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80"),
    ("SNK-SOA-029", "Haldiram's Desi Ghee Soan Papdi (250g)", "Snacks", 90.0, 62.0, 12, "8904004400289", "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=400&q=80"),
    ("SNK-MAG-030", "Maggi 2-Minute Masala Instant Noodles (4-Pack, 280g)", "Snacks", 56.0, 42.0, 35, "8901058852331", "https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=400&q=80"),
    ("SNK-LIJ-031", "Lijjat Udad Dal Black Pepper Papad (200g)", "Snacks", 75.0, 52.0, 15, "8906008120017", "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=400&q=80"),
    ("SNK-MAK-032", "Tata Sampann Roasted Phool Makhana Rock Salt (100g)", "Snacks", 140.0, 98.0, 12, "8901011120038", "https://images.unsplash.com/photo-1508061252966-f72fb7044435?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BLJ-033", "Balaji Wafers Masala Masti Potato Chips (100g)", "Snacks", 30.0, 20.0, 20, "8906010501149", "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80"),
    ("SNK-SAM-034", "Haldiram's Cocktail Punjabi Samosa Bites (400g)", "Snacks", 135.0, 95.0, 10, "8904004400296", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80"),
    ("SNK-CAD-036", "Cadbury Dairy Milk Silk Chocolate (150g)", "Snacks", 175.0, 130.0, 15, "7622201732011", "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=400&q=80"),
    ("SNK-BAK-037", "Chitale Bandhu Authentic Pune Bakarwadi (250g)", "Snacks", 95.0, 68.0, 15, "8906012440019", "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80"),
]


def seed_database(num_sales=520, random_seed=42, app=None, drop_existing=False):
    random.seed(random_seed)

    if app is None:
        try:
            from flask import has_app_context, current_app
            if has_app_context():
                app = current_app._get_current_object()
        except Exception:
            pass

    if app is None:
        app = create_app("development")

    from flask import has_app_context
    created_ctx = False
    if not has_app_context():
        ctx = app.app_context()
        ctx.push()
        created_ctx = True

    try:
        print("Initializing GreenLeaf Nexus Seed Routine...")
        db.session.remove()
        if drop_existing:
            try:
                db.drop_all()
            except Exception:
                db.session.rollback()
                for mdl in [AuditLog, InventoryMovement, SaleItem, Sale, Product, Supplier, User]:
                    try:
                        db.session.query(mdl).delete()
                    except Exception:
                        pass
                db.session.commit()
        db.create_all()
        print("Database schema successfully verified.")

        # 1. Create Default Users (1 Admin, 2 Cashiers)
        admin = User(
            username="admin",
            full_name="Admin Supervisor (Priya Sharma)",
            role="admin",
            is_active=True,
            created_at=datetime(2026, 1, 1, 9, 0, 0),
        )
        admin.set_password("admin123")

        cashier1 = User(
            username="cashier1",
            full_name="Arun Verma",
            role="cashier",
            is_active=True,
            created_at=datetime(2026, 1, 1, 9, 30, 0),
        )
        cashier1.set_password("cashier123")

        cashier2 = User(
            username="cashier2",
            full_name="Deepa Nair",
            role="cashier",
            is_active=True,
            created_at=datetime(2026, 1, 1, 10, 0, 0),
        )
        cashier2.set_password("cashier123")

        inactive_cashier = User(
            username="cashier_old",
            full_name="Ex-Cashier Rohan",
            role="cashier",
            is_active=False,
            created_at=datetime(2026, 1, 1, 10, 0, 0),
        )
        inactive_cashier.set_password("cashier123")

        db.session.add_all([admin, cashier1, cashier2, inactive_cashier])
        db.session.commit()
        print("Created 1 Admin and 2 Cashier user accounts.")

        # 2. Create Suppliers
        suppliers = []
        for s_data in SUPPLIERS_DATA:
            supplier = Supplier(
                name=s_data["name"],
                phone=s_data["phone"],
                email=s_data["email"],
                address=s_data["address"],
                created_at=datetime(2026, 1, 2, 8, 0, 0),
            )
            db.session.add(supplier)
            suppliers.append(supplier)
        db.session.commit()
        print(f"Created {len(suppliers)} wholesale suppliers.")

        # 3. Create Products with coherent stock and expiry distributions
        today = date.today()
        products = []

        # Product stock & expiry scenario assignments:
        # A few items will have LOW STOCK (stock <= reorder_level)
        # A few items will be EXPIRED
        # A few items NEAR EXPIRY (within 7 - 15 days)
        # A few items SLOW-MOVING (will not be included in recent sales)
        # Rest will have healthy stock

        for idx, p_info in enumerate(PRODUCTS_CATALOG):
            sku, name, category, unit_price, cost_price, reorder_lvl, barcode, image_url = p_info
            supplier = suppliers[idx % len(suppliers)]

            # Determine Target Final Stock
            if idx == 0:  # Royal Gala Apples -> Low Stock (3 units)
                target_stock = 3
            elif idx == 8: # Tomatoes -> Low Stock (4 units)
                target_stock = 4
            elif idx == 16: # Full cream milk -> Out of stock (0 units)
                target_stock = 0
            elif idx == 24: # Whole wheat bread -> Low Stock (2 units)
                target_stock = 2
            elif idx in (40, 41): # Slow moving items
                target_stock = 45
            else:
                target_stock = random.randint(25, 120)

            # Determine Expiry Date scenario
            if category in ("Fruits", "Vegetables", "Dairy", "Bakery"):
                if idx in (1, 9):  # Expired
                    expiry_date = today - timedelta(days=random.randint(2, 10))
                elif idx in (2, 10, 17, 25):  # Near Expiry within 15 days
                    expiry_date = today + timedelta(days=random.randint(2, 12))
                else:  # Safe expiry
                    expiry_date = today + timedelta(days=random.randint(25, 90))
            elif category in ("Beverages", "Snacks", "Grains and Pulses"):
                expiry_date = today + timedelta(days=random.randint(120, 360))
            else:
                expiry_date = None  # Household Essentials don't expire

            product = Product(
                sku=sku,
                barcode=barcode,
                name=name,
                description=f"Fresh, premium quality {name.lower()} sourced directly from trusted partners.",
                category=category,
                unit_price=unit_price,
                cost_price=cost_price,
                stock_qty=target_stock,  # will be reconciled with sales
                reorder_level=reorder_lvl,
                expiry_date=expiry_date,
                supplier_id=supplier.supplier_id,
                image_path=f"/static/img/products/{sku}.jpg" if os.path.exists(os.path.join("static", "img", "products", f"{sku}.jpg")) else image_url,
                is_active=True,
                created_at=datetime(2026, 1, 5, 8, 30, 0),
            )
            db.session.add(product)
            products.append(product)

        db.session.commit()
        print(f"Created {len(products)} distinct products across 8 categories.")

        # 4. Generate >=500 Realistic Sales Distributed Over Past 4 Months
        print(f"Generating {num_sales} realistic sales transactions...")
        cashiers = [cashier1, cashier2]
        payment_methods = ["Cash", "Card", "UPI", "Digital Wallet"]
        tax_rate = app.config.get("TAX_RATE", 0.05)

        # Track total quantities sold per product to calculate proper opening stock & initial movement
        product_sold_counts = {p.product_id: 0 for p in products}

        # Date range for sales: past 120 days up to today
        start_history = today - timedelta(days=110)
        days_span = (today - start_history).days

        # Exclude slow-moving products (index 40, 41) from recent sales (past 30 days)
        slow_product_ids = {products[40].product_id, products[41].product_id}

        sales_to_insert = []
        sale_items_to_insert = []
        movements_to_insert = []

        for sale_idx in range(1, num_sales + 1):
            # Weight distribution towards recent days
            days_ago = int(days_span * (random.random() ** 1.35))
            sale_date = today - timedelta(days=days_ago)

            random_hour = random.randint(9, 21)
            random_minute = random.randint(0, 59)
            random_second = random.randint(0, 59)
            sale_time = time(random_hour, random_minute, random_second)
            sale_datetime = datetime.combine(sale_date, sale_time)

            cashier = random.choice(cashiers)
            payment = random.choices(payment_methods, weights=[0.45, 0.25, 0.25, 0.05])[0]
            invoice_num = f"GLN-{sale_date.strftime('%Y%m%d')}-{1000 + sale_idx}"

            # Number of line items (1 to 5)
            num_items = random.choices([1, 2, 3, 4, 5], weights=[0.25, 0.35, 0.25, 0.1, 0.05])[0]

            # Pick eligible products
            available_prods = products
            if days_ago <= 30:
                available_prods = [p for p in products if p.product_id not in slow_product_ids]

            chosen_prods = random.sample(available_prods, num_items)

            # Build line items
            line_subtotals = []
            sale_lines_data = []
            sale_subtotal = 0.0

            for prod in chosen_prods:
                qty = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.1, 0.05])[0]
                line_tot = round(prod.unit_price * qty, 2)
                sale_subtotal += line_tot
                product_sold_counts[prod.product_id] += qty

                sale_lines_data.append({
                    "product": prod,
                    "product_id": prod.product_id,
                    "name": prod.name,
                    "quantity": qty,
                    "unit_price": prod.unit_price,
                    "cost_price": prod.cost_price,
                    "line_total": line_tot,
                })

            sale_subtotal = round(sale_subtotal, 2)

            # Random occasional discount (5%, 10%, or 0%)
            discount_pct = random.choices([0.0, 5.0, 10.0], weights=[0.8, 0.15, 0.05])[0]
            discount_amt = round(sale_subtotal * (discount_pct / 100.0), 2)
            taxable_amt = max(0.0, round(sale_subtotal - discount_amt, 2))
            tax_amt = round(taxable_amt * tax_rate, 2)
            grand_total = round(taxable_amt + tax_amt, 2)

            # Optional customer info for ~30% of sales
            cust_name = None
            cust_phone = None
            if random.random() < 0.3:
                first_names = ["Rahul", "Sneha", "Kiran", "Vikram", "Ananya", "Rohan", "Pooja", "Amit", "Naveen"]
                last_names = ["Sharma", "Patel", "Reddy", "Iyer", "Gowda", "Kulkarni", "Das", "Singh"]
                cust_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                cust_phone = f"+91 {random.randint(90000, 99999)} {random.randint(10000, 99999)}"

            sale = Sale(
                invoice_number=invoice_num,
                sale_date=sale_date,
                sale_time=sale_time,
                user_id=cashier.user_id,
                subtotal=sale_subtotal,
                discount_amount=discount_amt,
                tax_amount=tax_amt,
                total_amount=grand_total,
                payment_method=payment,
                transaction_status="completed",
                customer_name=cust_name,
                customer_phone=cust_phone,
                created_at=sale_datetime,
            )
            db.session.add(sale)
            db.session.flush()

            # Create SaleItem records
            for line in sale_lines_data:
                prod = line["product"]
                line_discount = round((line["line_total"] / sale_subtotal) * discount_amt, 2) if sale_subtotal > 0 else 0.0

                sale_item = SaleItem(
                    sale_id=sale.sale_id,
                    product_id=prod.product_id,
                    product_name_snapshot=prod.name,
                    quantity=line["quantity"],
                    unit_price=prod.unit_price,
                    unit_cost_snapshot=prod.cost_price,
                    discount_amount=line_discount,
                    line_total=line["line_total"],
                )
                db.session.add(sale_item)

                # Record inventory movement for this sale
                # We will record movement with timestamp of the sale
                movement = InventoryMovement(
                    product_id=prod.product_id,
                    user_id=cashier.user_id,
                    movement_type="sale",
                    quantity_change=-line["quantity"],
                    previous_stock=0,  # Will be adjusted relative to opening stock
                    resulting_stock=0,
                    reference=invoice_num,
                    notes=f"POS Sale #{invoice_num}",
                    created_at=sale_datetime,
                )
                movements_to_insert.append(movement)

        db.session.commit()
        print(f"Successfully generated and committed {num_sales} completed sales and line items.")

        # 5. Reconcile Opening Stock & Inventory Movements
        # Coherent approach:
        # Opening Stock = Target Current Stock + Total Sold + Restocked
        # Add Initial Movement record for each product
        for prod in products:
            total_sold = product_sold_counts[prod.product_id]
            target_current = prod.stock_qty
            opening_stock = target_current + total_sold

            # Opening stock movement
            initial_mov = InventoryMovement(
                product_id=prod.product_id,
                user_id=admin.user_id,
                movement_type="initial",
                quantity_change=opening_stock,
                previous_stock=0,
                resulting_stock=opening_stock,
                reference="Warehouse Opening Intake",
                notes="Initial store opening inventory balance",
                created_at=datetime(2026, 1, 4, 8, 0, 0),
            )
            db.session.add(initial_mov)

            # If item was restocked along the way (e.g. half of sales were replenished)
            if total_sold > 30:
                mid_restock_qty = int(total_sold * 0.4)
                restock_mov = InventoryMovement(
                    product_id=prod.product_id,
                    user_id=admin.user_id,
                    movement_type="restock",
                    quantity_change=mid_restock_qty,
                    previous_stock=opening_stock - total_sold,
                    resulting_stock=opening_stock - total_sold + mid_restock_qty,
                    reference="PO-2026-RESTOCK-A",
                    notes="Mid-quarter replenishment shipment",
                    created_at=datetime(2026, 2, 15, 11, 0, 0),
                )
                db.session.add(restock_mov)

        db.session.commit()
        print("Inventory opening stocks and movement audit logs reconciled cleanly.")

        # Print summary
        total_prods = Product.query.count()
        total_sales = Sale.query.count()
        total_items = SaleItem.query.count()
        total_revenue = db.session.query(db.func.sum(Sale.total_amount)).scalar()

        print("\n========================================================")
        print("GREENLEAF NEXUS — DEMO DATASET READY!")
        print("========================================================")
        print(f"Products in database  : {total_prods}")
        print(f"Sales transactions    : {total_sales}")
        print(f"Itemized sale records : {total_items}")
        print(f"Total revenue booked  : INR {total_revenue:,.2f}")
        print("Demo Credentials:")
        print("  - Admin   : admin / admin123")
        print("  - Cashier1: cashier1 / cashier123")
        print("  - Cashier2: cashier2 / cashier123")
        print("========================================================\n")
    finally:
        if created_ctx and "ctx" in locals():
            ctx.pop()


if __name__ == "__main__":
    seed_database(drop_existing=True)
