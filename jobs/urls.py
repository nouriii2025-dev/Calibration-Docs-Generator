from django.urls import path
from . import views
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("job/<str:ds>/", views.job_detail, name="job"),
    path("job/<str:ds>/save/", views.job_save, name="job_save"),
    path("job/<str:ds>/report/<str:kind>/", views.report, name="report"),
    path("job/<str:ds>/certificate/save/", views.certificate_save, name="certificate_save"),
    path("job/<str:ds>/certificate/refresh/", views.certificate_refresh, name="certificate_refresh"),
    path("export/", views.export_excel, name="export"),
    path("import/", views.import_excel, name="import"),
]
