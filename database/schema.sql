-- ========================================================
-- GreenLeaf Nexus Database Schema (SQLite / Relational SQL)
-- ========================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'cashier',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(30),
    email VARCHAR(100),
    address TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku VARCHAR(50) NOT NULL UNIQUE,
    barcode VARCHAR(50),
    name VARCHAR(120) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    cost_price REAL NOT NULL DEFAULT 0.0 CHECK(cost_price >= 0),
    stock_qty INTEGER NOT NULL DEFAULT 0 CHECK(stock_qty >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 10 CHECK(reorder_level >= 0),
    expiry_date DATE,
    supplier_id INTEGER,
    image_path VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    sale_date DATE NOT NULL,
    sale_time TIME NOT NULL,
    user_id INTEGER NOT NULL,
    subtotal REAL NOT NULL DEFAULT 0.0,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    tax_amount REAL NOT NULL DEFAULT 0.0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'Cash',
    transaction_status VARCHAR(20) NOT NULL DEFAULT 'completed',
    customer_name VARCHAR(100),
    customer_phone VARCHAR(30),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS sale_items (
    sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name_snapshot VARCHAR(120) NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    unit_cost_snapshot REAL NOT NULL DEFAULT 0.0,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    line_total REAL NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER,
    movement_type VARCHAR(30) NOT NULL,
    quantity_change INTEGER NOT NULL,
    previous_stock INTEGER NOT NULL,
    resulting_stock INTEGER NOT NULL,
    reference VARCHAR(100),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    details TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_sales_invoice ON sales(invoice_number);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_user ON sales(user_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_product ON inventory_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_type ON inventory_movements(movement_type);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
