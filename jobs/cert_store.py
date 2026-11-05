"""Saved Calibration Certificates.

A certificate is "generated" the first time it is opened. At that moment the
job data it prints (customer, range, serial number ...) is copied into
data/certificates/<data sheet no>.json together with everything typed on it
(measured readings, calculated averages / deviations, ticked notes, engineer name).

After that the certificate is rendered from this saved copy, NOT from the Excel
sheet, so importing a new Excel file cannot overwrite or reset it. It changes only when

  * the user types in the certificate (readings, notes, engineer name)  -> save_state()
  * the user edits that record on the dashboard and saves               -> apply_edits()
  * the user clicks "Refresh from Excel" on the certificate             -> refresh()
"""
import datetime as dt
import hashlib
import json
import os
import re
import threading

from django.conf import settings

LOCK = threading.RLock()

# Job fields printed on the Calibration Certificate (HART and Foundation Fieldbus layouts).
CERT_KEYS = (
    "data_sheet_no", "job_no", "cert_no", "customer", "customer_address", "project", "lpo",
    "equipment", "make", "model", "serial_no", "tag_no", "cal_range", "resolution", "accuracy",
    "instrument_range", "communication", "cal_by", "cal_date", "due_date",
    "temp", "humidity", "atm_press",
)
LABELS = {
    "data_sheet_no": "Data Sheet No", "job_no": "Job No", "cert_no": "Cert. No", "customer": "Customer",
    "customer_address": "Customer address", "project": "Project", "lpo": "PO No.", "equipment": "Instrument",
    "make": "Manufacturer", "model": "Model", "serial_no": "Serial Number", "tag_no": "Tag Number",
    "cal_range": "Cal. Range", "resolution": "Resolution", "accuracy": "Accuracy",
    "instrument_range": "Instr. Range", "communication": "Communication", "cal_by": "Calibrated By",
    "cal_date": "Date of Calibration", "due_date": "Re-Calibration Date", "temp": "Lab. Temperature",
    "humidity": "Lab. Humidity", "atm_press": "Amb. Pressure",
}
READING_KEYS = ("up_u", "dn_u", "up_m", "dn_m")
CALC_KEYS = ("avg_u", "avg_m", "dev_u", "dev_m")
CHECK_KEYS = ("received", "adjusted", "noadj")
MAX_ROWS = 20


class CertError(Exception):
    pass


def _dir():
    d = getattr(settings, "CERT_DIR", None) or (settings.EXCEL_PATH.parent / "certificates")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file(ds):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", ds).strip("._") or "ds"
    return _dir() / f"{safe[:60]}-{hashlib.sha1(ds.encode()).hexdigest()[:8]}.json"


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def pick(row):
    """The certificate fields of a job-sheet row (plain strings)."""
    return {k: str(row.get(k, "") or "") for k in CERT_KEYS}


def _read(ds):
    try:
        with open(_file(ds), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and isinstance(data.get("job"), dict) else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write(ds, snap):
    p = _file(ds)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def exists(ds):
    return _file(ds).exists()


def count():
    return len(list(_dir().glob("*.json")))


def get_or_create(ds, row):
    """Saved certificate for ds; generated from the current Excel row the first time."""
    with LOCK:
        snap = _read(ds)
        if snap is None:
            snap = {"version": 1, "ds": ds, "generated_at": _now(), "refreshed_at": None,
                    "updated_at": _now(), "job": pick(row),
                    "readings": None, "calc": None, "checks": None, "sign": {}}
            _write(ds, snap)
        return snap


def changes(snap, row):
    """Printed fields whose Excel value now differs from the saved certificate."""
    live = pick(row)
    return [{"label": LABELS[k], "saved": snap["job"].get(k, ""), "excel": live[k]}
            for k in CERT_KEYS if snap["job"].get(k, "") != live[k]]


def refresh(ds, row):
    """Explicit 'Refresh from Excel': copy the current Excel values into the certificate.
    Typed readings, notes and engineer name are kept."""
    with LOCK:
        snap = get_or_create(ds, row)
        old = snap["job"]
        snap["job"] = pick(row)
        snap["refreshed_at"] = snap["updated_at"] = _now()
        _write(ds, snap)
        return {"changed": [LABELS[k] for k in CERT_KEYS if old.get(k, "") != snap["job"][k]],
                "range_changed": old.get("cal_range", "") != snap["job"]["cal_range"]}


def apply_edits(ds, new_ds, values):
    """A record was edited and saved on the dashboard: carry those edits (only) into its certificate.
    Never called by the Excel import."""
    with LOCK:
        if new_ds != ds and exists(ds) and not exists(new_ds):
            snap = _read(ds)
            snap["ds"] = new_ds
            _write(new_ds, snap)
            _file(ds).unlink()
        snap = _read(new_ds)
        if snap is None:
            return                      # certificate not generated yet: it will be, from the saved row
        edited = {k: str(v or "") for k, v in values.items() if k in CERT_KEYS}
        if edited:
            snap["job"].update(edited)
            snap["updated_at"] = _now()
            _write(new_ds, snap)


def _clean_rows(rows, keys):
    if rows is None:
        return None
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise CertError("Invalid readings.")
    out = []
    for r in rows:
        if not isinstance(r, dict):
            raise CertError("Invalid readings.")
        out.append({k: str(r.get(k, ""))[:32] for k in keys if r.get(k) is not None})
    return out


def save_state(ds, payload):
    """Autosave from the certificate page: readings, calculated values, ticked notes, engineer name."""
    with LOCK:
        snap = _read(ds)
        if snap is None:
            raise CertError("Certificate has not been generated yet.")
        if "readings" in payload:
            snap["readings"] = _clean_rows(payload["readings"], READING_KEYS)
        if "calc" in payload:
            snap["calc"] = _clean_rows(payload["calc"], CALC_KEYS)
        if isinstance(payload.get("checks"), dict):
            snap["checks"] = {k: bool(payload["checks"].get(k)) for k in CHECK_KEYS if k in payload["checks"]}
        if isinstance(payload.get("sign"), dict) and "cert" in payload["sign"]:
            name = str(payload["sign"]["cert"] or "").strip()[:100]
            if name:
                snap["sign"]["cert"] = name
            else:
                snap["sign"].pop("cert", None)
        snap["updated_at"] = _now()
        _write(ds, snap)
        return snap["updated_at"]


def shown(ts):
    try:
        return dt.datetime.fromisoformat(ts).strftime("%d-%b-%Y %H:%M")
    except (TypeError, ValueError):
        return ""