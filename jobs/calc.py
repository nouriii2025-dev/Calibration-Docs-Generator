import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_RANGE = re.compile(r"^\s*([-–−]?\s*[\d.]+)\s*to\s*([-–−]?\s*[\d.]+)\s*(.*)$", re.I)


def _num(s):
    return float(s.replace("–", "-").replace("−", "-").replace(" ", ""))


def _fmt(v):
    return ("%.4f" % round(v, 4)).rstrip("0").rstrip(".") or "0"

def resolution_dp(resolution):
    """Decimal places of the resolution: '0.0001' -> 4, '0.01 mbar' -> 2, '1' -> 0.
    Returns None when the resolution is blank or cannot be read."""
    m = re.search(r"\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?", str(resolution or ""))
    if not m:
        return None
    try:
        d = Decimal(m.group().replace(",", ".")).normalize()
    except InvalidOperation:
        return None
    if d <= 0:
        return None
    return max(0, -d.as_tuple().exponent)


def precision(resolution):
    """Applied = res + 1, Measured = res, Average = measured + 1, Deviation = measured + 1.
    Returns None when the resolution is unknown (old behaviour is kept)."""
    dp = resolution_dp(resolution)
    if dp is None:
        return None
    return {"applied": dp + 1, "meas": dp, "avg": dp + 1, "dev": dp + 1}


def _fixed(v, dp):
    """Fixed-dp string, rounded half-up, no float noise, no '-0.000'."""
    d = Decimal(format(v, ".10g")).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)
    return f"{d:.{dp}f}".lstrip("-") if d == 0 else f"{d:.{dp}f}"

def test_points(cal_range):
    """0/25/50/75/100 % points of a range such as '0 to 1.23 mbar'."""
    m = _RANGE.match(cal_range or "")
    if not m:
        return [{"pct": p, "value": ""} for p in (0, 25, 50, 75, 100)], ""
    try:
        lo, hi = _num(m.group(1)), _num(m.group(2))
    except ValueError:
        return [{"pct": p, "value": ""} for p in (0, 25, 50, 75, 100)], ""
    return [{"pct": p, "value": _fmt(lo + (hi - lo) * p / 100)} for p in (0, 25, 50, 75, 100)], m.group(3).strip()


def _fmt_min(v, min_dp=2, max_dp=4):
    """Round to max_dp, drop trailing zeros but keep at least min_dp decimals."""
    v = round(v, max_dp) + 0.0          # turns -0.0 into 0.0
    whole, dec = f"{v:.{max_dp}f}".split(".")
    return f"{whole}.{dec.rstrip('0').ljust(min_dp, '0')}"


def certificate_rows(cal_range, resolution=None):
    pcts = (0, 25, 50, 75, 100)
    m = _RANGE.match(cal_range or "")
    try:
        lo, hi = _num(m.group(1)), _num(m.group(2))
    except (AttributeError, ValueError):
        return [{"pct": p, "applied_txt": "", "applied_txt4": "", "applied_raw": "",
            "equiv_txt": "", "equiv_raw": ""} for p in pcts], ""
    dp = precision(resolution)
    rows = []
    for p in pcts:
        applied = lo + (hi - lo) * p / 100
        equiv = ((applied - lo) / (hi - lo)) * 16 + 4 if hi != lo else None
        rows.append({
            "pct": p,
            "applied_txt": _fixed(applied, dp["applied"]) if dp else _fmt_min(applied),
            "applied_txt4": _fixed(applied, dp["applied"]) if dp else f"{round(applied, 4) + 0.0:.4f}",
            "applied_raw": format(applied, ".10g"),
            "equiv_txt": "" if equiv is None else f"{round(equiv, 4) + 0.0:.4f}",
            "equiv_raw": "" if equiv is None else format(equiv, ".10g"),
        })
    return rows, m.group(3).strip()

def mbar_tolerance(cal_range, accuracy):
    """Allowed error in mbar: accuracy (% of full scale) x upper range value of the Cal. Range.
    Returns "" when the unit is not mbar or the accuracy / range cannot be read."""
    m = _RANGE.match(cal_range or "")
    a = re.search(r"\d+(?:\.\d+)?", (accuracy or "").replace(",", "."))
    if not m or not a or m.group(3).strip().lower() != "mbar":
        return ""
    try:
        upper = max(abs(_num(m.group(1))), abs(_num(m.group(2))))
    except ValueError:
        return ""
    return format(float(a.group()) / 100 * upper, ".10g")

def ma_tolerance(cal_range, accuracy):
    """Allowed error in mA: ((accuracy% x upper range) x 16) / upper range.
    Returns "" when the accuracy or the range cannot be read."""
    m = _RANGE.match(cal_range or "")
    a = re.search(r"\d+(?:\.\d+)?", (accuracy or "").replace(",", "."))
    if not m or not a:
        return ""
    try:
        upper = max(abs(_num(m.group(1))), abs(_num(m.group(2))))
    except ValueError:
        return ""
    if upper == 0:
        return ""
    return format(((float(a.group()) / 100 * upper) * 16) / upper, ".10g")

import datetime as _dt
_NUMERIC = re.compile(r"^\s*[-+]?\d+(\.\d+)?\s*$")

def long_date(s):
    """'12/10/2026' -> '12-Oct-2026'; blank -> '-' (never '0-Jan-1900')."""
    try:
        return _dt.datetime.strptime((s or "").strip(), "%d/%m/%Y").strftime("%d-%b-%Y")
    except ValueError:
        return "-"

def test_date(s):
    """Hydrotest / VDF test date: one day before the calibration date.
    If the calibration date is a Monday, skip Sunday and use the preceding Saturday."""
    try:
        d = _dt.datetime.strptime((s or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return "-"
    d -= _dt.timedelta(days=2 if d.weekday() == 0 else 1)   # weekday(): Monday == 0
    return d.strftime("%d-%b-%Y")

def report_test_date(job):
    """Date of Test for the Hydrotest and Visual/Dimensional reports.
    Uses the 'Hydrotest & VDR, FT Date' chosen on the dashboard; if blank,
    falls back to the old rule (day before Cal Date, Monday -> Saturday)."""
    try:
        d = _dt.datetime.strptime((job.get("ht_vdr_date") or "").strip(), "%d/%m/%Y")
        return d.strftime("%d-%b-%Y")
    except ValueError:
        return test_date(job.get("cal_date"))

def certificate_view(job, unit):
    res = (job.get("resolution") or "").strip()
    if res and unit and _NUMERIC.match(res):
        res = f"{res} {unit}"
    rng = (job.get("instrument_range") or "").strip()
    rng = re.sub(r"(^|\s)-(?=\d)", lambda m: m.group(1) + "–", rng)
    return {
        "customer": " ".join((job.get("customer") or "").split()),
        "cal_date": long_date(job.get("cal_date")),
        "recal_date": long_date(job.get("due_date")),
        "resolution": res or "-",
        "instrument_range": rng or "-",
        "instrument_range_plain": (job.get("instrument_range") or "").strip() or "-",
    }

def hydrotest_view(job, default_pressure=""):
    return {
        "customer": " ".join((job.get("customer") or "").split()),
        "test_date": test_date(job.get("cal_date")),
        "instrument_range": (job.get("instrument_range") or "").strip() or "-",
        "test_pressure": (job.get("test_pressure") or "").strip() or default_pressure or "-",
    }

NO_MANIFOLD_POINT_EQUIPMENT = {
    "differential pressure transmitter + remote diaphragm seal",
    "differential pressure transmitter + integral diaphragm seal",
}

def vdf_view(job, cfg):
    """Values + the numbered 'Test Details' sentences for the VDF report."""
    equipment = " ".join((job.get("equipment") or "").split())
    main = equipment.split("+")[0].strip() or "Instrument"          # e.g. 'Pressure Transmitter'
    m = re.search(r"([\w-]+-valve)\s+manifold", equipment, re.I)    # e.g. 'Two-Valve Manifold'
    manifold = f"{m.group(1).lower()} manifold" if m else "manifold"
    has_manifold = bool(m) or "manifold" in equipment.lower()
    drawing = (job.get("ga_drawing") or "").strip() or cfg.get("ga_drawing_no", "")

    details = [
        "Instrument and accessories were visually inspected and found satisfactory.",
        f"Dimensional verification was carried out against GA Drawing No. {drawing} "
        "and found within the specified requirements.",
    ]
        # No manifold point for DP transmitters with a diaphragm seal
    eq_norm = re.sub(r"\s*\+\s*", " + ", equipment).lower()
    no_manifold_point = any(k in eq_norm for k in NO_MANIFOLD_POINT_EQUIPMENT)
    if has_manifold and not no_manifold_point:
        details.append(f"Mounting orientation and basic functionality of the {manifold} "
                       "were verified and found satisfactory.")
    details.append(f"The above mentioned instrument has been verified for power-up, display operation, process value and engineering unit "
                   "indication and found satisfactory, with no obvious fault / "
                   "alarm indication observed.")
    if (job.get("communication") or "").strip():
        details.append("Communication with the transmitter was verified and found satisfactory.")

    def dash(k):
        return (job.get(k) or "").strip() or "-"

    return {
        "customer": " ".join((job.get("customer") or "").split()),
        "date": long_date(job.get("cal_date")),
        "test_date": test_date(job.get("cal_date")),
        "instrument_range": dash("instrument_range"),
        "communication": dash("communication"),
        "fieldbus_address": dash("address"),
        "details": details,
    }


def _pkey(s):
    return "".join((s or "").lower().split())      # "100 Bar" -> "100bar"


def hydrotest_standards(pressure, cfg):
    """Working standard(s) for the chosen Hydrotest Pressure.
    Falls back to the default standard(s) when nothing matches, so old records still print."""
    key = _pkey(pressure)
    for p in cfg.get("pressure_standards", []):
        if _pkey(p["pressure"]) == key:
            return [{"name": cfg.get("standard_name", ""), "serial": p["serial"], "cert_no": p["cert_no"]}]
    return cfg.get("standards", [])


def is_fieldbus(comm):
    """True when Communication is Foundation Fieldbus (any spelling) or 'FF'."""
    c = "".join((comm or "").lower().split())
    return "fieldbus" in c or c == "ff"