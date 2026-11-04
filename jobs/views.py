import datetime as dt
import json
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from io import BytesIO
from django.conf import settings
from . import excel_store as store
from .calc import *
import re


def _opts(rows, key):
    return sorted({r[key] for r in rows if r[key]})


def dashboard(request):
    rows = store.all_rows()
    cols = [(k, lbl) for k, lbl in store.columns() if k not in store.DASHBOARD_HIDDEN]
    keys = [k for k, _ in cols]
    for r in rows:
        r["search"] = " ".join(
            str(r.get(k, "") or "") for k in keys
        ).lower()

        r["cells"] = [
            str(r.get(k, "") or "") for k in keys
        ]
    ctx = {
        "rows": rows,
        "columns": cols,
        "total": len(rows),
        "completed": sum(r["status"] == "Completed" for r in rows),
        "pending": sum(r["status"] == "Pending" for r in rows),
        "status_opts": store.STATUS_CHOICES,
        "with_serial": sum(bool(r["serial_no"]) for r in rows),
        "equipment_opts": _opts(rows, "equipment"),
        "date_opts": sorted({r["cal_date"] for r in rows if r["cal_date"]},
                            key=lambda d: dt.datetime.strptime(d, "%d/%m/%Y"), reverse=True),
        "file_name": store._path().name,
    }
    return render(request, "jobs/dashboard.html", ctx)


def _find(ds):
    try:
        return store.get_row(ds)
    except store.NotFound:
        raise Http404("Data sheet not found")


def split_test_pressure(value):
    """Separate pressure value and unit from the Excel cell."""
    import re

    value = str(value or "").strip()

    units = ["Kg/cm^2", "MPa", "psi", "bar"]

    for unit in units:
        if value.lower().endswith(unit.lower()):
            number = value[:-len(unit)].strip()
            return number, unit

    # Existing Excel values without a unit default to bar
    return value, "bar"


def job_detail(request, ds):
    job = _find(ds)
    test_pressure_value, test_pressure_unit = split_test_pressure(
        job.get("test_pressure", "")
    )
    prev_ds, next_ds, pos, total = store.neighbours(ds)
    fields = [{"key": k, "label": lbl, "value": job.get(k, ""),
               "multiline": "\n" in job.get(k, "") or len(job.get(k, "")) > 52}
              for k, lbl in store.columns() if k != "status"]  
    comm = job.get("communication", "")
    comm_choices = list(store.COMMUNICATION_CHOICES)
    if comm and comm not in comm_choices:      # keep an older free-text value selectable
        comm_choices.append(comm)
    cal_by = job.get("cal_by", "")
    cal_by_choices = list(store.CAL_BY_CHOICES)
    if cal_by and cal_by not in cal_by_choices:
        cal_by_choices.append(cal_by)
    return render(request, "jobs/detail.html", {
        "cal_by_choices": cal_by_choices,
        "hydro_refs": [p["pressure"] for p in settings.HYDRO["pressure_standards"]],
        "hydro_default": settings.HYDRO["default_pressure"],
        "job": job, "fields": fields, "status_choices": store.STATUS_CHOICES,
        "prev_ds": prev_ds, "next_ds": next_ds, "pos": pos, "total": total,"comm_choices": comm_choices,
        "test_pressure_value": test_pressure_value,
        "test_pressure_unit": test_pressure_unit,
    })


@require_POST
def job_save(request, ds):
    _find(ds)
    try:
        payload = json.loads(request.body or "{}")

        if "test_pressure" in payload:
            pressure = str(payload["test_pressure"] or "").strip()

            if pressure:
                valid_pressure = re.fullmatch(
                    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*(?:bar|psi|MPa|Kg/cm\^2)",
                    pressure,
                    re.IGNORECASE
                )

                if not valid_pressure:
                    return JsonResponse({
                        "ok": False,
                        "error": "Enter a valid test pressure with a supported unit."
                    }, status=400)

        updates = {
            k: str(payload.get(k, ""))
            for k in store.EDITABLE
            if k in payload
        }

        job = store.update_row(ds, updates)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid request."}, status=400)
    except store.StoreLocked as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=423)
    except store.StoreError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    return JsonResponse({"ok": True, "ds": job["data_sheet_no"], "url": reverse("job", args=[job["data_sheet_no"]]),
                         "values": {k: job.get(k, "") for k in store.EDITABLE}})


REPORTS = {"hydrotest": "Hydrotest Report",
           "vdf": "Visual, Dimensional and Function Report",
           "certificate": "Calibration Certificate",
           "all": "Complete Calibration Pack"}


def report(request, ds, kind):
    if kind not in REPORTS:
        raise Http404("Unknown report")
    job = _find(ds)
    points, unit = test_points(job.get("cal_range"))
    cert_rows, cert_unit = certificate_rows(job.get("cal_range"), job.get("resolution"))
    return render(request, "reports/report.html", {
        "job": job, "kind": kind, "title": f"{REPORTS[kind]} – {job['tag_no']}",
        "show_ht": kind in ("hydrotest", "all"),
        "show_vdf": kind in ("vdf", "all"),
        "show_cert": kind in ("certificate", "all"),
        "points": points, "unit": unit,
        "autoprint": request.GET.get("print") == "1",
        "today": dt.date.today().strftime("%d/%m/%Y"),
        "cert_rows": cert_rows,
        "cert_unit": cert_unit,
        "cert_dp": precision(job.get("resolution")),
        "cert_tol": mbar_tolerance(job.get("cal_range"), job.get("accuracy")),
        "cert_tol_ma": ma_tolerance(job.get("cal_range"), job.get("accuracy")),
        "cv": certificate_view(job, cert_unit),
        "is_ff": is_fieldbus(job.get("communication")),
        "hv": hydrotest_view(job, settings.HYDRO.get("test_pressure", "")),
        "vv": vdf_view(job, settings.VDF),
        "hs": hydrotest_standards(request.GET.get("ref", ""), settings.HYDRO),
    })


def export_excel(request):
    name = f"Calibration_Job_Sheet_{dt.datetime.now():%Y%m%d_%H%M}.xlsx"
    return FileResponse(BytesIO(store.export_bytes()), as_attachment=True, filename=name,
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@require_POST
def import_excel(request):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"ok": False, "error": "Choose an Excel (.xlsx) file first."}, status=400)
    if not f.name.lower().endswith(".xlsx"):
        return JsonResponse({"ok": False, "error": "Only .xlsx files can be imported."}, status=400)
    if f.size > store.MAX_IMPORT_BYTES:
        return JsonResponse({"ok": False, "error": "File is too large (max 15 MB)."}, status=400)
    try:
        summary = store.import_workbook(f)
    except store.StoreLocked as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=423)
    except store.StoreError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    return JsonResponse({"ok": True, **summary})