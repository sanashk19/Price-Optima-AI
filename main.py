from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, conint, confloat
from typing import Literal, Optional
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
import traceback

app = FastAPI(title="PriceOptima API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Global model reference
MODEL_PIPELINE = None

# Model file path (same directory as this file)
MODEL_PATH = Path(__file__).parent / "best_pricing_demand_model.joblib"

class RideRequest(BaseModel):
    Number_of_Riders: conint(ge=0) = Field(..., description="Number of users attempting to book")
    Number_of_Drivers: conint(ge=0) = Field(..., description="Number of available drivers")
    Location_Category: Literal["Urban", "Suburban", "Rural"]
    Customer_Loyalty_Status: Literal["Gold", "Silver", "Regular"]
    Number_of_Past_Rides: conint(ge=0)
    Average_Ratings: confloat(ge=0.0, le=5.0)
    Time_of_Booking: Literal["Morning", "Afternoon", "Evening", "Night"]
    Vehicle_Type: Literal["Economy", "Premium"]
    Expected_Ride_Duration: confloat(gt=0)  # minutes
    Historical_Cost_of_Ride: confloat(gt=0)  # baseline price reference


# ====== Model loading helpers ======
def lazy_load_model() -> None:
    """Load the model into MODEL_PIPELINE if it's not already loaded.
    Does not raise during app startup; raises HTTPException with detailed info when needed.
    """
    global MODEL_PIPELINE
    if MODEL_PIPELINE is not None:
        return
    if not MODEL_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Model file missing at: {MODEL_PATH}")
    try:
        MODEL_PIPELINE = joblib.load(MODEL_PATH)
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model pipeline: {e}. Traceback: {tb}"
        )


@app.on_event("startup")
def load_model() -> None:
    """Attempt to load model on startup but don't crash the app if it fails."""
    global MODEL_PIPELINE
    try:
        if MODEL_PATH.exists():
            MODEL_PIPELINE = joblib.load(MODEL_PATH)
        else:            
            MODEL_PIPELINE = None
    except Exception:
        MODEL_PIPELINE = None


# ====== Feature engineering to match training pipeline ======
def engineer_features(req: RideRequest) -> pd.DataFrame:
    """
    Create the exact feature set used by the trained pipeline:
    ['baseline_price', 'Expected_Ride_Duration', 'Number_of_Riders', 'Number_of_Drivers',
     'Rider_Driver_Ratio', 'Cost_per_Min', 'competitor_price',
     'Time_of_Booking', 'Location_Category', 'Vehicle_Type', 'Customer_Loyalty_Status']
    """
    baseline_price = float(req.Historical_Cost_of_Ride)
    expected_ride_duration = float(req.Expected_Ride_Duration)
    number_of_riders = int(req.Number_of_Riders)
    number_of_drivers = int(req.Number_of_Drivers)    
    rider_driver_ratio = (
        number_of_riders / number_of_drivers if number_of_drivers > 0 else float("inf")
    )    
    cost_per_min = baseline_price / expected_ride_duration
    competitor_price = 1.05 * baseline_price

    # Construct feature row as the model expects
    features = {
        "baseline_price": baseline_price,
        "Expected_Ride_Duration": expected_ride_duration,
        "Number_of_Riders": number_of_riders,
        "Number_of_Drivers": number_of_drivers,
        "Rider_Driver_Ratio": rider_driver_ratio,
        "Cost_per_Min": cost_per_min,
        "competitor_price": competitor_price,
        "Time_of_Booking": req.Time_of_Booking,
        "Location_Category": req.Location_Category,
        "Vehicle_Type": req.Vehicle_Type,
        "Customer_Loyalty_Status": req.Customer_Loyalty_Status,
    }    
    return pd.DataFrame([features])

def find_optimal_price(feature_row: pd.Series, model_pipeline, hist_cost: float, price_grid_size: int = 20):
    
    base_price = float(feature_row["baseline_price"])
    cost = 0.70 * hist_cost

    price_grid = np.linspace(base_price * 0.85, base_price * 1.15, price_grid_size)

    baseline_df = pd.DataFrame([feature_row.to_dict()])
    baseline_p = float(np.clip(model_pipeline.predict(baseline_df)[0], 0.0, 1.0))
    
    scenarios = pd.DataFrame([feature_row.to_dict()] * price_grid_size)
    scenarios["baseline_price"] = price_grid
    
    preds = np.clip(model_pipeline.predict(scenarios), 0.0, 1.0)

    # Rule 1: margin >= 12% => (price - cost)/price >= 0.12  => price >= cost / (1 - 0.12)
    min_price_for_margin = cost / (1.0 - 0.12)
    margin_ok = price_grid >= min_price_for_margin

    # Rule 2: no worse completion than baseline
    completion_ok = preds >= baseline_p
    valid = margin_ok & completion_ok
    
    if not np.any(valid):        
        return base_price, baseline_p
    expected_revenue = price_grid * preds
    best_idx = int(np.argmax(np.where(valid, expected_revenue, -np.inf)))
    return float(price_grid[best_idx]), float(preds[best_idx])


# ====== Endpoints ======
@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": MODEL_PIPELINE is not None}


@app.post("/recommend_price")
def recommend_price(req: RideRequest):
    global MODEL_PIPELINE    
    if MODEL_PIPELINE is None:
        lazy_load_model()

    # Engineer features
    features_df = engineer_features(req)
    feature_row = features_df.iloc[0]

    # Compute optimal price
    recommended_price, p_complete = find_optimal_price(
        feature_row=feature_row,
        model_pipeline=MODEL_PIPELINE,
        hist_cost=float(req.Historical_Cost_of_Ride),
        price_grid_size=20,
    )
    return {
        "recommended_price": round(recommended_price, 4),
        "predicted_completion_probability": round(p_complete, 6),
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)