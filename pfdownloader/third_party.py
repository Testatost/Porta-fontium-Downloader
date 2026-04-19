from __future__ import annotations

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import pip_system_certs.wrapt_requests  # type: ignore  # noqa: F401
except Exception:
    pass

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    HAVE_REPORTLAB = True
except Exception:
    A4 = None
    canvas = None
    HAVE_REPORTLAB = False
