# Calibration Dashboard

Django + HTML/CSS/JS dashboard that uses an Excel job sheet as its data source.

## Run
    pip install -r requirements.txt
    python manage.py runserver
    # open http://127.0.0.1:8000

## Configure (config/settings.py)
- `EXCEL_PATH` - the workbook (default `data/job_sheet.xlsx`, or env var `CAL_EXCEL_PATH`)
- `LAB` - letterhead printed on all three documents (name, address, contact, accreditation)

## Notes
- Rows are keyed by **Data sheet No** (Tag No. repeats for FT100512A/B/C).
- All 29 Excel columns are shown in the table and are editable on the details page; only changed cells are written back.
- First save creates `data/job_sheet.original.xlsx` as a safety copy.
- Close the workbook in Excel before saving from the dashboard.
