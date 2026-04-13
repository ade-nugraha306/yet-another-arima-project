from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.arima_service import get_products, run_forecast, run_evaluation, run_eda

app = FastAPI(title="ARIMA Forecast API", version="1.0.0")

# ---------------------------------------------------------------
# CORS — izinkan Vite dev server (port 5173) & prod build
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",   # fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------
# REQUEST SCHEMAS
# ---------------------------------------------------------------
class ForecastRequest(BaseModel):
    product: str
    horizon: int = 5


class EvaluationRequest(BaseModel):
    product: str


class EDARequest(BaseModel):
    product: str


# ---------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def list_products():
    """Kembalikan daftar semua nama produk dari dataset."""
    try:
        return {"products": get_products()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/forecast")
def forecast(req: ForecastRequest):
    """
    Jalankan auto-ARIMA + forecast untuk produk tertentu.
    Body: { "product": "...", "horizon": 5 }
    Returns: { forecast, upper, lower, order, aic, weeks }
    """
    try:
        return run_forecast(req.product, req.horizon)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
def evaluate(req: EvaluationRequest):
    """
    Train/test split evaluation untuk 1 produk.
    Body: { "product": "..." }
    Returns: { order, aic, mae, rmse, mape, actual_train, actual_test, fitted, dates_train, dates_test }
    """
    try:
        return run_evaluation(req.product)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/eda")
def eda(req: EDARequest):
    """
    EDA stats + rolling mean untuk 1 produk.
    Body: { "product": "..." }
    """
    try:
        return run_eda(req.product)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))