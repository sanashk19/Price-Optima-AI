import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor

DATA_PATH = Path(__file__).parent / "dynamic_pricing (1).csv"
MODEL_PATH = Path(__file__).parent / "best_pricing_demand_model.joblib"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

# Load
df = pd.read_csv(DATA_PATH)

# Basic cleaning
df = df.drop_duplicates().copy()

# Impute missing
for col in df.columns:
    if df[col].dtype.kind in "if":
        df[col] = df[col].fillna(df[col].median())
    else:
        df[col] = df[col].fillna(df[col].mode().iloc[0])

# Feature engineering to match main.engineer_features() expectations
# 1) Derived ratios
df["Rider_Driver_Ratio"] = df["Number_of_Riders"] / df["Number_of_Drivers"].replace(0, np.nan)
df["Rider_Driver_Ratio"] = df["Rider_Driver_Ratio"].fillna(np.inf)

# 2) Cost per minute
df["Cost_per_Min"] = df["Historical_Cost_of_Ride"] / df["Expected_Ride_Duration"].replace(0, np.nan)

# 3) competitor_price (randomized during training; at inference we used 1.05x)
np.random.seed(42)
df["competitor_price"] = df["Historical_Cost_of_Ride"] * np.random.uniform(0.9, 1.1, size=len(df))

# 4) baseline_price is the dynamic price feature the model will learn against
df["baseline_price"] = df["Historical_Cost_of_Ride"]

# 5) Define a pseudo target probability p_complete (bounded [0,1])
# Use a simple proxy consistent with the notebook: min(1, drivers/riders)
ratio = (df["Number_of_Drivers"] / df["Number_of_Riders"].replace(0, np.nan)).fillna(0.0)
df["p_complete"] = np.clip(ratio, 0.0, 1.0)

# Prepare features/target
feature_columns = [
    "baseline_price",
    "Expected_Ride_Duration",
    "Number_of_Riders",
    "Number_of_Drivers",
    "Rider_Driver_Ratio",
    "Cost_per_Min",
    "competitor_price",
    "Time_of_Booking",
    "Location_Category",
    "Vehicle_Type",
    "Customer_Loyalty_Status",
]

df = df.copy()
X = df[feature_columns]
y = df["p_complete"].astype(float)

# Column types
categorical_features = X.select_dtypes(include=["object", "category"]).columns.tolist()
numerical_features = X.select_dtypes(include=[np.number]).columns.tolist()

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numerical_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ]
)

# A robust, fast default model
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=12,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1,
)

pipe = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

# Split and fit
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
pipe.fit(X_train, y_train)

# Persist
joblib.dump(pipe, MODEL_PATH)
print(f"Saved model to {MODEL_PATH}")
