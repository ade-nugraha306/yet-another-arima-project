# 📈 Yet Another ARIMA Project

> A web-based sales forecasting application using the ARIMA (AutoRegressive Integrated Moving Average) model, developed as a Final Project (Tugas Akhir).

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![React](https://img.shields.io/badge/React-Frontend-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6.svg)
![Bun](https://img.shields.io/badge/Bun-Runtime-black.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 📖 About

Yet Another ARIMA Project is a web application developed to forecast product sales using the **ARIMA (AutoRegressive Integrated Moving Average)** time series forecasting method.

This project was created as a Final Project (Tugas Akhir) and uses historical sales data to predict future demand. The application also provides exploratory data analysis (EDA), model evaluation, and interactive visualizations through a modern web interface.

---

## ✨ Features

- 📊 Interactive dashboard
- 📈 Sales forecasting using ARIMA
- 🧹 Data preprocessing
- 🔍 Exploratory Data Analysis (EDA)
- 📉 Model evaluation
- 📦 REST API with FastAPI
- ⚡ Modern React + TypeScript frontend
- 🎨 Responsive UI

---

## 🛠 Tech Stack

### Backend

- Python
- FastAPI
- Pandas
- NumPy
- Statsmodels
- pmdarima
- Scikit-learn
- Matplotlib

### Frontend

- React
- TypeScript
- Vite
- Bun
- Tailwind CSS
- shadcn/ui
- Recharts

---

## 📂 Project Structure

```text
yet-another-arima-project/
│
├── backend/
│   ├── services/
│   ├── README.md
│   └── requirements.txt
│
├── frontend/
│   ├── images/
│   ├── public/
│   ├── src/
│   └── package.json
│
├── README.md
└── LICENSE
```

---

## 🚀 Getting Started

### Clone Repository

```bash
git clone https://github.com/<your-username>/yet-another-arima-project.git

cd yet-another-arima-project
```

---

## Backend Setup

Create virtual environment

```bash
python -m venv .venv
```

Activate

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run FastAPI

```bash
uvicorn app.main:app --reload
```

Backend will be available at

```
http://127.0.0.1:8000
```

API documentation

```
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Install dependencies

```bash
bun install
```

Run development server

```bash
bun run dev
```

Open

```
http://localhost:5173
```

---

## 📊 Workflow

```
Historical Sales Data
          │
          ▼
 Data Preprocessing
          │
          ▼
 Exploratory Data Analysis
          │
          ▼
 Stationarity Test (ADF)
          │
          ▼
 ARIMA Modeling
          │
          ▼
 Forecasting
          │
          ▼
 Model Evaluation
```

---

## 📈 Evaluation Metrics

The forecasting performance is evaluated using:

- MAE (Mean Absolute Error)
- RMSE (Root Mean Square Error)
- sMAPE (Symmetric Mean Absolute Percentage Error)

---

## 📚 References

- Hyndman, R. J., & Khandakar, Y. (2008). Automatic Time Series Forecasting: The forecast Package for R.
- Box, G. E. P., Jenkins, G. M., Reinsel, G. C., & Ljung, G. M. Time Series Analysis: Forecasting and Control.

---

## 🎓 Academic Information

**Final Project**

**Title**

> Sales Forecasting Using ARIMA Model

Developed as part of the undergraduate final project requirement.

---

## 🤝 Contributing

Contributions are welcome.

Feel free to open an Issue or submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.
