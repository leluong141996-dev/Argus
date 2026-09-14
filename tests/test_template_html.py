from __future__ import annotations
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "dashboards" / "web" / "template.html"


def test_template_has_required_anchors_and_marker():
    html = TEMPLATE.read_text()
    for anchor in ('id="stage-matrix"', 'id="row-table"', 'id="file-input"', 'id="error-box"'):
        assert anchor in html, anchor
    assert "/*__ARGUS_REPORT__*/" in html
    assert "/*__END_REPORT__*/" in html
    assert "EMBEDDED_REPORT" in html
    assert "http://" not in html and "https://" not in html
    assert "cdn" not in html.lower()
