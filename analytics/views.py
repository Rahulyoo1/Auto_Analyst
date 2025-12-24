# =========================================
# IMPORTS
# =========================================
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.template.loader import get_template

from .forms import DatasetUploadForm

import pandas as pd
import plotly.express as px
import os

from xhtml2pdf import pisa
from io import BytesIO


# =========================================
# STAGE 5.5 — AUTO INSIGHTS
# =========================================
def generate_insights(df):
    insights = []

    insights.append(
        f"The dataset contains {df.shape[0]} rows and {df.shape[1]} columns."
    )

    total_missing = int(df.isnull().sum().sum())
    if total_missing == 0:
        insights.append("There are no missing values after cleaning.")
    else:
        insights.append(f"There are {total_missing} missing values remaining.")

    numeric_cols = df.select_dtypes(include="number").columns
    for col in numeric_cols:
        insights.append(
            f"'{col}' has an average of {df[col].mean():.2f}, "
            f"with values ranging from {df[col].min()} to {df[col].max()}."
        )

    categorical_cols = df.select_dtypes(include="object").columns
    for col in categorical_cols:
        top_value = df[col].value_counts().idxmax()
        insights.append(
            f"The most frequent value in '{col}' is '{top_value}'."
        )

    return insights


# =========================================
# STAGE 6 — AUTO CHART RECOMMENDATION
# =========================================
def recommend_chart(metric, dimension, numeric_cols, categorical_cols, df=None):
    if metric and not dimension:
        if metric in numeric_cols:
            return "histogram"

    if metric and dimension:

        if metric in numeric_cols and dimension in categorical_cols:

            time_keywords = ["year", "date", "month", "time"]
            if any(word in dimension.lower() for word in time_keywords):
                return "line"

            if df is not None and df[dimension].nunique() <= 10:
                return "pie"

            return "bar"

        if metric in numeric_cols and dimension in numeric_cols:
            return "scatter"

    return None


# =========================================
# UTILITY — RESTORE INTEGER COLUMNS
# =========================================
def restore_integer_columns(df):
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if not series.empty and (series % 1 == 0).all():
            df[col] = df[col].astype("Int64")
    return df


# =========================================
# STAGE 7 — DATA WARNINGS
# =========================================
def detect_data_warnings(df):
    warnings = []

    numeric_cols = df.select_dtypes(include="number").columns
    categorical_cols = df.select_dtypes(include="object").columns

    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers = series[(series < lower) | (series > upper)]
        if len(outliers) > 0:
            warnings.append(
                f"Column '{col}' contains {len(outliers)} potential outliers."
            )

        if abs(series.mean() - series.median()) > series.std():
            warnings.append(
                f"Column '{col}' appears to be skewed."
            )

    for col in categorical_cols:
        unique_count = df[col].nunique()
        if unique_count > 15:
            warnings.append(
                f"Column '{col}' has high cardinality ({unique_count} unique values)."
            )

    return warnings


# =========================================
# MAIN VIEW — UPLOAD + DASHBOARD
# =========================================
def upload_page(request):

    if request.method == "GET":
        request.session.flush()

    # -------------------------------
    # FILE UPLOAD
    # -------------------------------
    if request.method == "POST" and "file" in request.FILES:
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save()

            # ✅ STORE ONLY FILE NAME (NOT ABSOLUTE PATH)
            request.session["dataset_name"] = os.path.basename(dataset.file.path)
            request.session.pop("cleaned_dataset_path", None)

    dataset_name = request.session.get("dataset_name")
    cleaned_path = request.session.get("cleaned_dataset_path")

    dataset_path = None
    if dataset_name:
        dataset_path = os.path.join(settings.MEDIA_ROOT, "datasets", dataset_name)

    if not dataset_path or not os.path.exists(dataset_path):
        return render(request, "analytics/upload.html", {
            "form": DatasetUploadForm()
        })

    if "charts" not in request.session:
        request.session["charts"] = []

    if cleaned_path and os.path.exists(cleaned_path):
        df = pd.read_csv(cleaned_path)
    else:
        df = pd.read_csv(dataset_path)

    # -------------------------------
    # DATA CLEANING
    # -------------------------------
    remove_duplicates = request.POST.get("remove_duplicates")
    fill_missing = request.POST.get("fill_missing")

    if remove_duplicates or fill_missing:
        cleaned_df = df.copy()

        if remove_duplicates:
            cleaned_df = cleaned_df.drop_duplicates()

        if fill_missing:
            for col in cleaned_df.columns:
                if cleaned_df[col].dtype == "object":
                    cleaned_df[col] = cleaned_df[col].fillna("Unknown")
                else:
                    cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].mean())

        cleaned_dir = os.path.join(settings.MEDIA_ROOT, "cleaned")
        os.makedirs(cleaned_dir, exist_ok=True)

        cleaned_file_path = os.path.join(cleaned_dir, "cleaned_dataset.csv")
        cleaned_df.to_csv(cleaned_file_path, index=False)

        request.session["cleaned_dataset_path"] = cleaned_file_path
        df = restore_integer_columns(cleaned_df)

    # -------------------------------
    # METRICS + TABLE
    # -------------------------------
    insights = generate_insights(df)
    warnings = detect_data_warnings(df)

    total_rows, total_cols = df.shape
    missing_values = int(df.isnull().sum().sum())
    df = restore_integer_columns(df)

    table_html = (
        df.head()
        .style
        .set_properties(**{"text-align": "center"})
        .hide(axis="index")
        .to_html()
    )

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include="object").columns.tolist()

    # -------------------------------
    # CHART GENERATION
    # -------------------------------
    chart_type = request.POST.get("chart_type")
    metric = request.POST.get("metric")
    dimension = request.POST.get("dimension")

    if not chart_type and metric:
        chart_type = recommend_chart(metric, dimension, numeric_cols, categorical_cols, df)

    chart_html = None

    if chart_type and metric and (dimension or chart_type == "histogram"):

        if chart_type == "bar":
            fig = px.bar(df, x=dimension, y=metric)
        elif chart_type == "line":
            fig = px.line(df, x=dimension, y=metric)
        elif chart_type == "area":
            fig = px.area(df, x=dimension, y=metric)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=metric)
        elif chart_type == "pie":
            fig = px.pie(df, names=dimension, values=metric)
        elif chart_type == "box":
            fig = px.box(df, x=dimension, y=metric)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=dimension, y=metric)

        chart_html = fig.to_html()

        charts = request.session.get("charts", [])
        idx = len(charts) + 1

        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        image_path = os.path.join(settings.MEDIA_ROOT, f"chart_{idx}.png")
        fig.write_image(image_path)

        charts.append({
            "title": f"{metric} by {dimension}" if dimension else metric,
            "chart_type": chart_type,
            "metric": metric,
            "dimension": dimension,
            "image": settings.MEDIA_URL + f"chart_{idx}.png"
        })

        request.session["charts"] = charts

    return render(request, "analytics/dashboard.html", {
        "form": DatasetUploadForm(),
        "table_html": table_html,
        "chart_html": chart_html,
        "total_rows": total_rows,
        "total_cols": total_cols,
        "missing_values": missing_values,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "insights": insights,
        "warnings": warnings,
        "charts": request.session.get("charts", []),
        "has_file": True,
        "chart_type": chart_type,
        "metric": metric,
        "dimension": dimension,
    })


# =========================================
# DOWNLOAD RAW CSV
# =========================================
def download_csv(request):
    dataset_name = request.session.get("dataset_name")
    if not dataset_name:
        return HttpResponse("No dataset available")

    path = os.path.join(settings.MEDIA_ROOT, "datasets", dataset_name)
    if not os.path.exists(path):
        return HttpResponse("No dataset available")

    with open(path, "rb") as f:
        response = HttpResponse(f.read(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="raw_dataset.csv"'
        return response


# =========================================
# DOWNLOAD CLEANED CSV
# =========================================
def download_cleaned_csv(request):
    path = request.session.get("cleaned_dataset_path")
    if not path or not os.path.exists(path):
        return HttpResponse("No cleaned dataset available")

    with open(path, "rb") as f:
        response = HttpResponse(f.read(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="cleaned_dataset.csv"'
        return response


# =========================================
# PDF IMAGE LINK FIX
# =========================================
def link_callback(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        return os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    return uri


# =========================================
# STAGE 8 → 10 — EXPORT PDF REPORT
# =========================================
def export_report_pdf(request):

    dataset_name = request.session.get("dataset_name")
    cleaned_path = request.session.get("cleaned_dataset_path")

    dataset_path = None
    if dataset_name:
        dataset_path = os.path.join(settings.MEDIA_ROOT, "datasets", dataset_name)

    if cleaned_path and os.path.exists(cleaned_path):
        df = pd.read_csv(cleaned_path)
    elif dataset_path and os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)
    else:
        return HttpResponse("No data available to export.")

    df = restore_integer_columns(df)

    total_rows, total_cols = df.shape
    missing_values = int(df.isnull().sum().sum())

    table_html = (
        df.head(20)
        .style
        .set_properties(**{"text-align": "center"})
        .hide(axis="index")
        .to_html()
    )

    insights = generate_insights(df)
    warnings = detect_data_warnings(df)

    charts = request.session.get("charts", [])

    selected_indexes = request.POST.getlist("selected_charts")
    if selected_indexes:
        charts = [
            charts[int(i)]
            for i in selected_indexes
            if i.isdigit() and int(i) < len(charts)
        ]

    template = get_template("analytics/report.html")
    html = template.render({
        "total_rows": total_rows,
        "total_cols": total_cols,
        "missing_values": missing_values,
        "table_html": table_html,
        "insights": insights,
        "warnings": warnings,
        "charts": charts,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="analysis_report.pdf"'

    pisa.CreatePDF(
        BytesIO(html.encode("UTF-8")),
        dest=response,
        link_callback=link_callback
    )

    return response
