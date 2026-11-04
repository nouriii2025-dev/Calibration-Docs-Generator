import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "jobs",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "jobs.context.lab",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
STATIC_URL = "static/"
USE_TZ = False
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Excel data source (edit this path, or set CAL_EXCEL_PATH) ----------
EXCEL_PATH = Path(os.environ.get("CAL_EXCEL_PATH", BASE_DIR / "data" / "job_sheet.xlsx"))

# ---- Letterhead used on printed documents --------------------------------
LAB = {
    "name": "Your Calibration Laboratory",
    "address": "Address line · City · UAE",
    "contact": "Tel: +971 0 000 0000 · info@example.com",
    "accreditation": "",   # e.g. "ISO/IEC 17025 accredited"
}

CERT = {
    "procedure_no": "LCP/AAF/022",
    "temp_note": "Temperature variation during calibration did not exceed ±1 °C",
    "standards": [
        {"name": "Multiprocess Calibrator", "serial": "5969", "cert_no": "ALPHA-AELE-2601151"},
        {"name": "Pressure Controller",
         "serial": "41000CSQ + 41000B98 // 41000CSQ + 41000CG4",
         "cert_no": "WP26/446 // WP26/447"},
    ],
    "comments": [  # the 4 bullet lines from the sample
        "It provides traceability of measurements to recognized national / international Standards and to units of measurements realized to recognized national / international standard laboratories.",
        "The Calibration results refers only to the measured value and does not carry any implication regarding the long term stability of the instrument.",
        "This certificate may not be reproduced, except in full, without prior written approval of the AAF laboratory.",
        "The calibration interval given in this certificate is provided as per the recommendation of customer.",
    ],
    "engineer_title": "Calibration Engineer",
    "engineer_name": "Shibili. K",
    "approver_title": "Technical Manager",
    "approver_name": "Fazil E.M",
    "footer": {
        "headline": "Authorized Calibration Laboratory & Service Centre",
        "address": "PO Box: 30495, Warehouse G-1, HIGHBAY, Dubai Silicon Oasis, Dubai-UAE",
        "form_no": "Form No.: FRM/AAF/39, Rev. No.: 03, Effective Date: 01-Jun-2023",
        "tel": "+ 971 4 3207944 / 2241464",
        "fax": "+ 971 4 3207933 / 2276062",
        "email": "calibration@accutech.ae",
        "website": "www.accutech.ae",
    },
}

# Foundation Fieldbus certificate: same as CERT, plus the differences in FF_Format.pdf
CERT_FF = {
    **CERT,
    "standards": list(reversed(CERT["standards"])),
    "temp_note": "",
    "engineer_title": "Calibration Technician",
    "engineer_name": "Shibili. K",
    "approver_name": "Fazil.E.M",
}


HYDRO = {
    "title": "Certificate of Hydrotest",
    "procedure_no": "LCP/AAF/012",
    "guideline": "ASME B31",
    "temp_during_test": "20 to 30 °C",
    "test_medium": "Clean Water, pH : 6 to 8",
    "test_pressure": "",       
    "default_pressure": "600 bar",
    "pressure_standards": [
        {"pressure": "1 bar",    "serial": "5833176 + 6000.899", "cert_no": "AAF-110002"},
        {"pressure": "2.5 bar",  "serial": "5599253 + 6000.899", "cert_no": "AAF-110003"},
        {"pressure": "6 bar",    "serial": "5890381 + 6000.899", "cert_no": "AAF-110004"},
        {"pressure": "10 bar",   "serial": "5871295 + 6000.899", "cert_no": "AAF-110005"},
        {"pressure": "25 bar",   "serial": "5890379 + 6000.899", "cert_no": "AAF-110006"},
        {"pressure": "60 bar",   "serial": "5945590 + 6000.899", "cert_no": "AAF-110007"},
        {"pressure": "100 bar",  "serial": "5890371 + 6001.528", "cert_no": "AAF-110008"},
        {"pressure": "250 bar",  "serial": "5918898 + 6001.528", "cert_no": "AAF-110009"},
        {"pressure": "600 bar",  "serial": "5945597 + 6001.528", "cert_no": "AAF-110010"},
        {"pressure": "1000 bar", "serial": "5946532 + 6001.528", "cert_no": "AAF-110011"},
    ],
    "standard_name": "Process Calibrator with Transmitter CPT 6400",
    "standards": [
        {"name": "Process Calibrator with Transmitter CPT 6400",
         "serial": "5945597 + 6001.528", "cert_no": "AAF-110010"},
    ],
    "statement": ("The above mentioned Unit Under Test is hydrotested and the pressure is held for "
                  "10 minutes and no leakage or any other abnormal condition is observed. "
                  "Hence, it is certified for use."),
    "remarks": [
        "UUT is received in good condition.",
        "It provides traceability of measurements to recognized national / international Standards and to units of measurements realized to recognized national / international standard laboratories.",
        "The Test results refers only to the measured value and does not carry any implication regarding the long term stability of the instrument.",
        "This certificate may not be reproduced, except in full, without prior written approval of the AAF laboratory.",
        "The calibration interval given in this certificate is provided as per the recommendation of customer.",
    ],
    "engineer_title": "Calibration Engineer",
    "engineer_name": "Sarandas. K. L",
    "approver_title": "Technical Manager",
    "approver_name": "Fazil.E.M",
}

VDF = {
    "title": "Visual, Dimensional and Function Test Report",
    "ga_drawing_no": "VD-1100-624-DWG-004",   
    "overall_result": "Satisfactory \u2013 The Instrument assembly passed the Visual, Dimensional and Functional checks performed.",
    "engineer_title": "Calibration Engineer",
    "engineer_name": "Sarandas. K. L",
    "approver_title": "Technical Manager",
    "approver_name": "Fazil E.M",
}