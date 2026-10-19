def test_dashboard_interactive_pie_chart(admin_client):
    """Verify that the dashboard category breakdown renders all interactive controls and handlers."""
    res = admin_client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    # Verify interactive controls and elements
    assert 'id="btnPieRev"' in html
    assert 'id="btnPieUnits"' in html
    assert 'id="pieSubtitle"' in html
    assert 'id="categoryDonutPlot"' in html
    assert 'id="pieDetailBox"' in html
    assert 'id="pieDetailCategory"' in html
    assert 'id="pieDetailStats"' in html
    assert 'id="pieCatalogLink"' in html
    assert 'id="btnResetPie"' in html

    # Verify JavaScript interactive handlers
    assert "getCenterAnnotation" in html
    assert "plotly_hover" in html
    assert "plotly_unhover" in html
    assert "plotly_click" in html
    assert "updateDetailBox" in html


def test_analytics_interactive_category_breakdown(admin_client):
    """Verify that the analytics page category chart has interactive Donut/Bar toggles and handlers."""
    res = admin_client.get("/analytics/")
    assert res.status_code == 200
    html = res.text

    # Verify toggle buttons and chart container
    assert 'id="btnAnalyticsCatDonut"' in html
    assert 'id="btnAnalyticsCatBar"' in html
    assert 'id="analyticsCategoryBar"' in html

    # Verify JavaScript interactive handlers
    assert "getCatDonutTrace" in html
    assert "getCatDonutLayout" in html
    assert "plotly_hover" in html
    assert "plotly_click" in html
