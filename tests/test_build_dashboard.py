from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest  # noqa: E402
from dashboards.build_dashboard import embed_report  # noqa: E402

TEMPLATE = 'x const EMBEDDED_REPORT = /*__ARGUS_REPORT__*/ null /*__END_REPORT__*/; y'


def test_embed_replaces_marker_region():
    out = embed_report(TEMPLATE, '[{"case_id":"c1"}]')
    assert '/*__ARGUS_REPORT__*/ null /*__END_REPORT__*/' not in out
    assert '[{"case_id":"c1"}]' in out
    assert 'EMBEDDED_REPORT' in out and out.startswith('x ') and out.endswith(' y')


def test_embed_escapes_script_close():
    out = embed_report(TEMPLATE, '[{"s":"</script>"}]')
    assert '</script>' not in out
    assert '<\\/script>' in out


def test_embed_missing_marker_raises():
    with pytest.raises(ValueError):
        embed_report('no markers here', '[]')
