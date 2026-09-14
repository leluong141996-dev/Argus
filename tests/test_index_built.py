from __future__ import annotations
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "dashboards" / "web"


def test_index_built_with_embedded_nonnull_report():
    html = (WEB / "index.html").read_text()
    for anchor in ('id="stage-matrix"', 'id="row-table"', 'id="file-input"'):
        assert anchor in html
    assert "EMBEDDED_REPORT" in html
    m = re.search(r"/\*__ARGUS_REPORT__\*/(.*?)/\*__END_REPORT__\*/", html, re.DOTALL)
    assert m is not None
    assert m.group(1).strip() not in ("null", "")
    assert "</script>" not in m.group(1)  # embedded JSON must not close the script tag
    assert "http://" not in html and "https://" not in html
