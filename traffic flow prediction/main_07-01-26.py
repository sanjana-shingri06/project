import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib
import os

# -----------------------------
# CSV path
# -----------------------------
DATA_PATH = r"C:\Users\sanja\Desktop\traffic flow prediction\data\traffic_data.csv"

def train_model():
    if not os.path.exists(DATA_PATH):
        print("❌ CSV not found at:", DATA_PATH)
        return None

    df = pd.read_csv(DATA_PATH)

    # Make all column names lowercase
    df.columns = [c.lower() for c in df.columns]

    # -----------------------------
    # Detect timestamp column
    # -----------------------------
    timestamp_cols = [col for col in df.columns if 'time' in col or 'date' in col]
    if not timestamp_cols:
        print("❌ No timestamp column found in CSV")
        return None
    ts_col = timestamp_cols[0]

    # Convert to datetime with dayfirst=True
    df['timestamp'] = pd.to_datetime(df[ts_col], dayfirst=True)

    # -----------------------------
    # Feature engineering
    # -----------------------------
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek

    # Encode weather if column exists
    if 'weather_main' in df.columns:
        weather_map = {"Clear":0, "Clouds":1, "Rain":2, "Snow":3}
        df['weather_encoded'] = df['weather_main'].map(weather_map).fillna(0)
    else:
        df['weather_encoded'] = 0

    # Ensure numeric features exist
    for col in ['temp', 'rain_1h', 'snow_1h', 'clouds_all']:
        if col not in df.columns:
            df[col] = 0

    # -----------------------------
    # Define features and target
    # -----------------------------
    feature_cols = ['hour', 'day_of_week', 'weather_encoded', 'temp', 'rain_1h', 'snow_1h', 'clouds_all']
    target_col = 'traffic_volume'
    if target_col not in df.columns:
        print(f"❌ Target column '{target_col}' not found in CSV")
        return None

    X = df[feature_cols]
    y = df[target_col]

    # Train model
    model = LinearRegression()
    model.fit(X, y)

    # Save model
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/traffic_model.pkl")
    print("✅ Model trained and saved at: models/traffic_model.pkl")

    return model

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    train_model()
