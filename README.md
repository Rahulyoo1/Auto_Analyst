# AutoAnalyst — AI-Powered Data Analytics Dashboard

AutoAnalyst is a web-based data analytics application built with **Django**, **Pandas**, and **Plotly** that allows users to upload CSV datasets, clean data, generate insights, visualize data, and export reports — all from an interactive dashboard.

---

## 🚀 Features

### 📁 Dataset Upload
- Upload CSV files through a modern, styled UI
- Selected file name is displayed instantly
- Supports large datasets

### 🧹 Data Cleaning
- Remove duplicate rows
- Fill missing values automatically
- Download cleaned dataset as CSV

### 📈 Data Visualization
- Generate multiple charts:
  - Bar Chart
  - Line Chart
  - Area Chart
  - Histogram
  - Pie Chart
  - Box Plot
  - Scatter Plot
- Automatic chart recommendation based on selected columns
- Multiple charts stored per dataset

### 📊 Dashboard
- Dataset metrics
- Data preview table
- Generated charts section with titles

### 🧠 Auto Insights
- Dataset summary
- Numeric column statistics
- Most frequent categorical values

### ⚠️ Data Warnings
- Outlier detection
- Skewed distributions
- High-cardinality categorical columns

### 📄 PDF Report Export
- Clean, readable PDF
- Includes dataset summary, preview, insights, warnings, and charts

---

## 🛠️ Tech Stack

- Django 5
- Pandas
- Plotly
- xhtml2pdf
- Tailwind CSS
- SQLite

---
## 📂 Project Structure

```text
AutoDA/
├── analytics/
│   ├── templates/
│   │   └── analytics/
│   │       ├── base.html
│   │       ├── upload.html
│   │       ├── dashboard.html
│   │       └── report.html
│   ├── views.py
│   ├── forms.py
│   └── static/
├── media/
│   ├── cleaned/
│   └── chart_*.png
├── db.sqlite3
├── manage.py
└── README.md

## ⚙️ Setup

```bash
git clone https://github.com/your-username/AutoAnalyst.git
cd AutoAnalyst
python -m venv venv
source venv/bin/activate
pip install django pandas plotly xhtml2pdf kaleido
python manage.py migrate
python manage.py runserver
```

---

## 👨‍💻 Author

Rahul Yadav  
B.Tech CSE (Data Science)
email- ryadav7991642288@gmail.com

---

## 📜 License

Educational & learning purpose.
