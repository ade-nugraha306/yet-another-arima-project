"""
app.py  —  FastAPI backend for ARIMA Dashboard (TA Final Methodology)

Endpoints:
  GET /health
  GET /families
  GET /data-acquisition?family=FOX
  GET /data-preparation?family=FOX
  GET /eda?family=FOX
  GET /modelling?family=FOX&horizon=5
  GET /evaluation?family=FOX
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from services.arima_service import (
    get_families,
    get_data_acquisition,
    get_data_preparation,
    get_eda,
    get_modelling,
    get_evaluation,
    get_data_cleaning_samples,
)

app = FastAPI(title="ARIMA Forecast API — TA Final", version="2.0.0")

# ---------------------------------------------------------------
# CORS — allow Vite dev server (5173) and Vite preview (4173)
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/families")
def list_families():
    """Return all valid product families present in the dataset."""
    try:
        return {"families": get_families()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-acquisition")
def data_acquisition(family: str = Query(..., description="Family name, e.g. FOX")):
    """
    Raw weekly sales data for a family (before cleaning).
    Returns: family, sku_count, skus, weeks, sales_raw
    """
    try:
        return get_data_acquisition(family)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-preparation")
def data_preparation(family: str = Query(..., description="Family name, e.g. FOX")):
    """
    Cleaning pipeline results for a family.
    Returns: missing/outlier counts before & after, ADF test, d order,
             sales_before, sales_after series.
    """
    try:
        return get_data_preparation(family)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/eda")
def eda(family: str = Query(..., description="Family name, e.g. FOX")):
    """
    EDA for a family: trend, distribution, rolling stats, ADF, boxplot.
    """
    try:
        return get_eda(family)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/modelling")
def modelling(
    family: str = Query(..., description="Family name, e.g. FOX"),
    horizon: int = Query(5, ge=1, le=20, description="Forecast horizon in weeks"),
):
    """
    Full ARIMA pipeline for a family.
    Returns: order (p,d,q), AIC, forecast, upper/lower CI, historical series.
    """
    try:
        return get_modelling(family, horizon)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluation")
def evaluation(family: str = Query(..., description="Family name, e.g. FOX")):
    """
    Train/test split evaluation for a family.
    Returns: MAE, RMSE, sMAPE, actual/fitted series.
    """
    try:
        return get_evaluation(family)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/data-cleaning-samples")
def data_cleaning_samples(family: str = Query(..., description="Family name")):
    """
    Contoh data untuk transparansi cleaning:
    - missing before & after (sample)
    - outliers before & after (sample)
    - sales preview family (5 baris pertama)
    """
    try:
        return get_data_cleaning_samples(family)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))