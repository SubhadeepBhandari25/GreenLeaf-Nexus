import io
from services.csv_service import CsvService, sanitize_csv_cell
from models.product import Product


def test_sanitize_csv_cell():
    """Test formula injection prefix neutralization."""
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-123") == "'-123"
    assert sanitize_csv_cell("@external") == "'@external"
    assert sanitize_csv_cell("Normal Product Name") == "Normal Product Name"
    assert sanitize_csv_cell(None) == ""


def test_valid_csv_import(app):
    """Test importing products from valid CSV content."""
    csv_text = """sku,name,category,unit_price,cost_price,stock_qty,reorder_level
CSV-IMPORT-001,Alphonso Mangoes,Fruits,350.0,250.0,20,5
CSV-IMPORT-002,Robusta Bananas,Fruits,60.0,40.0,30,10
"""
    stream = io.StringIO(csv_text)

    with app.app_context():
        result = CsvService.import_products_csv(stream, user_id=1)
        assert result["imported"] == 2
        assert len(result["errors"]) == 0

        p1 = Product.query.filter_by(sku="CSV-IMPORT-001").first()
        assert p1 is not None
        assert p1.name == "Alphonso Mangoes"
        assert p1.unit_price == 350.0
        assert p1.stock_qty == 20


def test_invalid_csv_rows_reported(app):
    """Test CSV import identifies and reports invalid rows without crashing."""
    csv_text = """sku,name,category,unit_price,cost_price,stock_qty,reorder_level
VALID-001,Valid Item,Dairy,80.0,60.0,15,5
INVALID-002,,Dairy,80.0,60.0,15,5
INVALID-003,Bad Price,Dairy,-10.0,60.0,15,5
INVALID-004,Bad Stock,Dairy,50.0,30.0,-2,5
"""
    stream = io.StringIO(csv_text)

    with app.app_context():
        result = CsvService.import_products_csv(stream, user_id=1)
        # Should import 1 valid, report 3 errors
        assert result["imported"] == 1
        assert len(result["errors"]) == 3
        err_rows = [e["row"] for e in result["errors"]]
        assert 3 in err_rows  # empty name
        assert 4 in err_rows  # negative price
        assert 5 in err_rows  # negative stock


def test_csv_export(app):
    """Test generating CSV export containing product inventory."""
    with app.app_context():
        csv_output = CsvService.export_inventory_csv(filter_type="all")
        assert "SKU,Barcode,Name,Category,Selling Price" in csv_output
        assert "TEST-SKU-001" in csv_output
        assert "Organic Apples" in csv_output
