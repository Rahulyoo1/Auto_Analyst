from django.urls import path
from .views import upload_page, download_csv, download_cleaned_csv, export_report_pdf

urlpatterns = [
    path("", upload_page, name="upload"),
    path("download/raw/", download_csv, name="download_csv"),
    path("download/cleaned/", download_cleaned_csv, name="download_cleaned_csv"),
    path("export-report/pdf/", export_report_pdf, name="export_report_pdf"),
]
