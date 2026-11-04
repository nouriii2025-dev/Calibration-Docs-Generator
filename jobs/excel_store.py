"""Excel-backed data store for the Calibration Dashboard.

The workbook is the single source of truth. Rows are identified by the
"Data sheet No" column (unique), NOT Tag No. (a few tags repeat).
Columns are located by header text, so the sheet can be re-ordered safely.
"""
import datetime as dt
import os
import shutil
import threading

from django.conf import settings
from openpyxl import load_workbook

LOCK = threading.RLock()

# key, header text in Excel, occurrence (for duplicate headers), label, section, editable
SCHEMA = [  # Excel column order (A..AC)
    ("data_sheet_no", "Data sheet No", 0, "Data Sheet No", "all", True),
    ("job_no", "Job No", 0, "Job No", "all", True),
    ("cert_no", "Cert. No", 0, "Cert. No", "all", True),
    ("ht_no", "HT", 0, "HT", "all", True),
    ("ft_no", "FT", 0, "FT", "all", True),
    ("customer", "Customer name", 0, "Customer Name", "all", True),
    ("customer_address", "Address", 0, "Address (Customer)", "all", True),
    ("tel", "Tel", 0, "Tel", "all", True),
    ("fax", "Fax", 0, "Fax", "all", True),
    ("lpo", "Lpo", 0, "LPO", "all", True),
    ("equipment", "Name of the Equipment", 0, "Name of the Equipment", "all", True),
    ("cal_range", "Cal. Range", 0, "Cal. Range", "all", True),
    ("model", "Model", 0, "Model", "all", True),
    ("make", "Make", 0, "Make", "all", True),
    ("tag_no", "Tag No.", 0, "Tag No.", "all", True),
    ("serial_no", "S.No", 0, "Serial Number", "all", True),
    ("cal_by", "Cal by", 0, "Calibrated By", "all", True),
    ("cal_date", "Cal Date", 0, "Cal Date", "all", True),
    ("due_date", "Due Date", 0, "Due Date", "all", True),
    ("resolution", "Resolution", 0, "Resolution", "all", True),
    ("accuracy", "Accuracy", 0, "Accuracy", "all", True),
    ("manifold", "Manifold", 0, "Manifold", "all", True),
    ("temp", "Temp", 0, "Temp", "all", True),
    ("humidity", "Rel. Humdity", 0, "Rel. Humidity", "all", True),
    ("atm_press", "Atm. Press", 0, "Atm. Press", "all", True),
    ("project", "Project details", 0, "Project Details", "all", True),
    ("instrument_range", "Instrument Range", 0, "Instrument Range", "all", True),
    ("communication", "Communication", 0, "Communication", "all", True),
    ("address", "Address", 1, "Address", "all", True),  # 2nd "Address" column (AC)
    ("test_pressure", "Test Pressure", 0, "Test Pressure", "all", True),
    ("ga_drawing", "GA Drawing No", 0, "GA Drawing No", "all", True),
    ("ht_vdr_date", "Hydrotest & VDR, FT Date", 0, "Hydrotest & VDR, FT Date", "all", True),
    ("status", "Status", 0, "Status", "all", True),
]
EDITABLE = [s[0] for s in SCHEMA]
LABELS = {s[0]: s[3] for s in SCHEMA}
DATE_KEYS = ("cal_date", "due_date", "ht_vdr_date")
DASHBOARD_HIDDEN = {"status"}
STATUS_CHOICES = ("Pending", "Completed")
COMMUNICATION_CHOICES = ("HART", "Foundation Fieldbus")
CAL_BY_CHOICES = ("Shibili.K", "Sarandas.K.H", "Mubasheer")
DEFAULT_STATUS = "Pending"

class StoreError(Exception):
    pass


class StoreLocked(StoreError):
    pass


class NotFound(StoreError):
    pass


def _path():
    return settings.EXCEL_PATH


def _norm(h):
    return " ".join(str(h or "").split()).lower()


def _column_map(ws):
    """key -> 1-based column index, found by header text."""
    seen, cols = {}, {}
    for c in range(1, ws.max_column + 1):
        h = _norm(ws.cell(1, c).value)
        if h:
            seen.setdefault(h, []).append(c)
    for key, header, occ, *_ in SCHEMA:
        hits = seen.get(_norm(header), [])
        if len(hits) > occ:
            cols[key] = hits[occ]
    return cols


def _display(v):
    if v is None:
        return ""
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        if v == 0:
            return ""            # stray 0s in the Address column mean "empty"
        if float(v).is_integer():
            return str(int(v))
        return ("%.10f" % v).rstrip("0").rstrip(".")
    return str(v).strip()


_cache = {"sig": None, "rows": [], "order": []}


def all_rows():
    p = _path()
    with LOCK:
        st = os.stat(p)
        sig = (st.st_mtime_ns, st.st_size)
        if _cache["sig"] == sig:
            return _cache["rows"]
        wb = load_workbook(p, data_only=True, read_only=False)
        ws = wb.active
        cols = _column_map(ws)
        rows = []
        for r in range(2, ws.max_row + 1):
            if ws.cell(r, cols["data_sheet_no"]).value in (None, ""):
                continue
            row = {k: _display(ws.cell(r, c).value) for k, c in cols.items()}
            row["_row"] = r
            row["status"] = "Completed" if _norm(row.get("status")) == "completed" else DEFAULT_STATUS
            rows.append(row)
        wb.close()
        order = [k for k, _ in sorted(cols.items(), key=lambda kv: kv[1])]   # workbook column order
        _cache.update(sig=sig, rows=rows, order=order)
        return rows


def columns():
    """Columns in the same left-to-right order as the Excel file (unknown-to-file keys go last)."""
    all_rows()                                    # make sure the cached order is current
    order = list(_cache["order"])
    order += [k for k in LABELS if k not in order]
    return [(k, LABELS[k]) for k in order]


def get_row(ds):
    for r in all_rows():
        if r["data_sheet_no"] == ds:
            return r
    raise NotFound(ds)


def neighbours(ds):
    rows = all_rows()
    for i, r in enumerate(rows):
        if r["data_sheet_no"] == ds:
            return (rows[i - 1]["data_sheet_no"] if i else None,
                    rows[i + 1]["data_sheet_no"] if i + 1 < len(rows) else None,
                    i + 1, len(rows))
    raise NotFound(ds)


def _coerce(key, val):
    val = (val or "").strip()
    if val == "":
        return None
    if key in ("job_no", "serial_no") and val.isdigit():
        return int(val)
    if key == "resolution":
        try:
            f = float(val)
            return int(f) if f.is_integer() else f
        except ValueError:
            return val
    if key in DATE_KEYS:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(val, fmt)
            except ValueError:
                pass
        raise StoreError(f"{LABELS[key]} must be a date like 31/12/2026.")
    return val

def default_test_date(cal_value):
    """Cal Date (dd/mm/yyyy) -> Hydrotest & VDR, FT Date (dd/mm/yyyy): one day earlier, Monday -> Saturday."""
    try:
        d = dt.datetime.strptime((cal_value or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return ""
    d -= dt.timedelta(days=2 if d.weekday() == 0 else 1)
    return d.strftime("%d/%m/%Y")

def update_row(ds, updates):
    """Write only the manual-entry fields back to the original workbook."""
    updates = {k: v for k, v in updates.items() if k in EDITABLE}
    if "cal_date" in updates and "ht_vdr_date" not in updates:     # keep the test date in step with Cal Date
        updates["ht_vdr_date"] = default_test_date(updates["cal_date"])
    for k, v in updates.items():
        if len(str(v or "")) > 200:
            raise StoreError(f"{LABELS[k]} is too long (max 200 characters).")
    if "status" in updates and updates["status"] not in STATUS_CHOICES:
        raise StoreError("Status must be Pending or Completed.")
    if updates.get("communication") and updates["communication"] not in COMMUNICATION_CHOICES:
        raise StoreError("Communication must be HART or Foundation Fielbus.")
    if updates.get("communication") and updates["communication"] not in COMMUNICATION_CHOICES:
        raise StoreError("Communication must be HART or Foundation Fielbus.")
    if updates.get("cal_by") and updates["cal_by"] not in CAL_BY_CHOICES:
        raise StoreError("Calibrated By must be " + ", ".join(CAL_BY_CHOICES) + ".")
    p = _path()
    p = _path()
    with LOCK:
        backup = p.with_name(p.stem + ".original" + p.suffix)
        if not backup.exists():
            shutil.copy2(p, backup)          # one-time safety copy
        wb = load_workbook(p)                # keep formulas / styles
        ws = wb.active
        cols = _column_map(ws)
        for k in updates:                      # header missing in the workbook -> add it
            if k not in cols:
                header = next(x[1] for x in SCHEMA if x[0] == k)
                ws.cell(1, ws.max_column + 1).value = header
                cols[k] = ws.max_column
        target = next((r for r in range(2, ws.max_row + 1)
                       if str(ws.cell(r, cols["data_sheet_no"]).value or "").strip() == ds), None)
        if target is None:
            raise NotFound(ds)
        if "data_sheet_no" in updates:
            new_ds = (updates["data_sheet_no"] or "").strip()
            if not new_ds:
                raise StoreError("Data Sheet No cannot be empty.")
            if any(r != target and str(ws.cell(r, cols["data_sheet_no"]).value or "").strip() == new_ds
                   for r in range(2, ws.max_row + 1)):
                raise StoreError(f"Data Sheet No {new_ds} already exists.")
            updates["data_sheet_no"] = new_ds
        for k, v in updates.items():
            cell = ws.cell(target, cols[k])
            if _display(cell.value) == (v or "").strip():
                continue                      # unchanged: leave the cell as it is
            had_fmt = cell.number_format
            cell.value = _coerce(k, v)
            if k in DATE_KEYS and isinstance(cell.value, dt.datetime):
                cell.number_format = "dd/mm/yyyy" if had_fmt == "General" else had_fmt
        tmp = p.with_name(p.stem + ".saving" + p.suffix)
        try:
            wb.save(tmp)
            os.replace(tmp, p)
        except PermissionError:
            if tmp.exists():
                tmp.unlink()
            raise StoreLocked("The Excel file is open in another program. Close it and try again.")
        finally:
            wb.close()
        _cache["sig"] = None
        return get_row(updates.get("data_sheet_no", ds))


def export_bytes():
    with LOCK:
        return _path().read_bytes()


# ---------------------------------------------------------------------------
#  Import an updated copy of the original job sheet
# ---------------------------------------------------------------------------
class ImportFailed(StoreError):
    pass


# Columns the uploaded file must contain (everything except the dashboard-only Status).
IMPORT_REQUIRED = [s[0] for s in SCHEMA if s[0] not in ("status", "ht_vdr_date")]

# Other spellings accepted for a header on import. Matching is case/space-insensitive.
HEADER_ALIASES = {
    "test_pressure": ["test pressure"],
    "instrument_range": ["instr. range", "instr range", "instrument range"],
    "ga_drawing": ["ga drawing number", "ga drawing no.", "ga drawing no", "ga drawing"],
    "ht_vdr_date": ["hydrotest & vdr ft date", "hydrotest and vdr, ft date"],
}
MAX_IMPORT_BYTES = 15 * 1024 * 1024


def _import_columns(ws):
    """Like _column_map, but also accepts the spellings in HEADER_ALIASES."""
    cols = _column_map(ws)
    seen = {}
    for c in range(1, ws.max_column + 1):
        h = _norm(ws.cell(1, c).value)
        if h:
            seen.setdefault(h, []).append(c)
    for key, aliases in HEADER_ALIASES.items():
        if key not in cols:
            for a in aliases:
                if a in seen:
                    cols[key] = seen[a][0]
                    break
    return cols


def import_workbook(upload):
    """Replace the backend workbook with an uploaded, edited copy of the original sheet.

    * Columns are found by header text, so order does not matter.
    * Status is dashboard-only: kept from the current data for rows that already exist.
    * The current backend file is copied to data/backups/ before it is replaced.
    """
    p = _path()
    with LOCK:
        incoming = p.with_name(p.stem + ".import" + p.suffix)
        staged = p.with_name(p.stem + ".staged" + p.suffix)
        try:
            with open(incoming, "wb") as out:
                for chunk in upload.chunks():
                    out.write(chunk)
            try:
                wb = load_workbook(incoming, data_only=True)   # keep the values Excel calculated, not the formula
                wb._external_links = []                        # drop the link to the other workbook
            except Exception:
                raise ImportFailed("That file could not be read. Upload a valid .xlsx workbook.")

            # 1. find the sheet that holds the job data
            ws = cols = None
            for cand in wb.worksheets:
                c = _import_columns(cand)
                if "data_sheet_no" in c:
                    ws, cols = cand, c
                    break
            if ws is None:
                raise ImportFailed("No sheet with a 'Data sheet No' header was found.")

            # 2. every original header must be present
            missing = [LABELS[k] for k in IMPORT_REQUIRED if k not in cols]
            if missing:
                raise ImportFailed("Missing column(s): " + ", ".join(missing) +
                                   ". Keep the same headers as the original Excel file.")

            # 3. canonical header text for any alias that was used (e.g. 'GA Drawing Number')
            for k, c in cols.items():
                canon = next(x[1] for x in SCHEMA if x[0] == k)
                if _norm(ws.cell(1, c).value) != _norm(canon):
                    ws.cell(1, c).value = canon
            if "status" not in cols:
                ws.cell(1, ws.max_column + 1).value = "Status"
                cols["status"] = ws.max_column

            # 4. validate rows + carry Status over
            try:
                old = {r["data_sheet_no"]: r for r in all_rows()}
            except (FileNotFoundError, KeyError):
                old = {}
            seen, dupes, count = set(), [], 0
            for r in range(2, ws.max_row + 1):
                ds = _display(ws.cell(r, cols["data_sheet_no"]).value)
                if not ds:
                    continue
                if ds in seen:
                    dupes.append(ds)
                seen.add(ds)
                count += 1
                cell = ws.cell(r, cols["status"])
                cur = _norm(cell.value)
                if cur in ("pending", "completed"):
                    cell.value = cur.capitalize()
                else:
                    cell.value = old.get(ds, {}).get("status", DEFAULT_STATUS)
            if count == 0:
                raise ImportFailed("The file has no data rows.")
            if dupes:
                raise ImportFailed("Duplicate Data sheet No: " + ", ".join(sorted(set(dupes))[:10]) +
                                   ". Each row needs a unique Data sheet No.")
            wb.active = wb.worksheets.index(ws)

            # 5. back up the current file, then swap the new one in
            try:
                wb.save(staged)
                if p.exists():
                    bdir = p.parent / "backups"
                    bdir.mkdir(exist_ok=True)
                    shutil.copy2(p, bdir / f"{p.stem}_before_import_{dt.datetime.now():%Y%m%d_%H%M%S}{p.suffix}")
                os.replace(staged, p)
            except PermissionError:
                raise StoreLocked("The Excel file is open in another program. Close it and try again.")
        finally:
            wb_ = locals().get("wb")
            if wb_ is not None:
                wb_.close()
            for f in (incoming, staged):
                if f.exists():
                    f.unlink()

        _cache["sig"] = None
        new = {r["data_sheet_no"]: r for r in all_rows()}
        compare = [k for k in EDITABLE if k != "status"]
        return {
            "rows": len(new),
            "added": sum(ds not in old for ds in new),
            "removed": sum(ds not in new for ds in old),
            "updated": sum(ds in old and any(old[ds].get(k, "") != new[ds].get(k, "") for k in compare)
                           for ds in new),
            "with_test_pressure": sum(bool(r.get("test_pressure")) for r in new.values()),
            "with_ga_drawing": sum(bool(r.get("ga_drawing")) for r in new.values()),
        }