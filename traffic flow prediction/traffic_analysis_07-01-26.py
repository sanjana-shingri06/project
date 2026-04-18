import pandas as pd
from sqlalchemy import create_engine
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for Flask
import matplotlib.pyplot as plt
import os
import joblib
from sklearn.linear_model import LinearRegression
import seaborn as sns

# ----------------------------
# Database connection
# ----------------------------
DB_URI = "sqlite:///traffic.db"
engine = create_engine(DB_URI)

# ----------------------------
# Model file path
# ----------------------------
MODEL_PATH = "data/traffic_model.pkl"

# ----------------------------
# Fetch traffic data
# ----------------------------
def fetch_traffic_data():
    query = "SELECT timestamp, vehicle_count FROM traffic_data"
    df = pd.read_sql(query, con=engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df

# ----------------------------
# Latest traffic
# ----------------------------
def get_latest_traffic(df):
    if df.empty:
        return None
    latest = df.iloc[-1]['vehicle_count']
    timestamp = df.index[-1]
    return timestamp, latest

# ----------------------------
# Traffic summary
# ----------------------------
def traffic_summary(df):
    summary = {
        "total_records": len(df),
        "avg_traffic": df['vehicle_count'].mean(),
        "max_traffic": df['vehicle_count'].max(),
        "min_traffic": df['vehicle_count'].min()
    }
    return summary

# ----------------------------
# Analyze peak hours
# ----------------------------
def analyze_peak_hours(df):
    hourly_avg = df.groupby(df.index.hour).mean()
    peak_hours = hourly_avg[hourly_avg['vehicle_count'] == hourly_avg['vehicle_count'].max()].index.tolist()
    return hourly_avg, peak_hours

# ----------------------------
# Analyze daily trends
# ----------------------------
def analyze_daily_trends(df):
    daily_avg = df.groupby(df.index.date).mean()
    return daily_avg

# ----------------------------
# Traffic by weekday
# ----------------------------
def traffic_by_weekday(df):
    df['day_of_week'] = df.index.dayofweek
    weekday_avg = df.groupby('day_of_week').mean()
    return weekday_avg

# ----------------------------
# Traffic by custom hour range
# ----------------------------
def traffic_by_hour_range(df, start_hour, end_hour):
    mask = (df.index.hour >= start_hour) & (df.index.hour <= end_hour)
    return df.loc[mask]

# ----------------------------
# Weather correlation
# ----------------------------
def analyze_weather_correlation(df):
    if 'weather_main' in df.columns:
        weather_avg = df.groupby('weather_main')['vehicle_count'].mean()
        return weather_avg
    return None

# ----------------------------
# Plot hourly traffic
# ----------------------------
def plot_traffic(hourly_avg, filename="static/plots/traffic_plot.png"):
    os.makedirs("static/plots", exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(hourly_avg.index, hourly_avg['vehicle_count'], marker='o')
    plt.title("Average Vehicles per Hour")
    plt.xlabel("Hour of the Day")
    plt.ylabel("Average Vehicle Count")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[OK] Plot saved to {filename}")

# ----------------------------
# Plot weekday trends
# ----------------------------
def plot_weekday_trends(weekday_avg, filename="static/plots/weekday_plot.png"):
    os.makedirs("static/plots", exist_ok=True)
    plt.figure(figsize=(10,5))
    plt.bar(weekday_avg.index, weekday_avg['vehicle_count'], color='royalblue')
    plt.title("Average Traffic per Weekday")
    plt.xlabel("Day of Week")
    plt.ylabel("Average Vehicle Count")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[OK] Weekday plot saved to {filename}")

# ----------------------------
# Plot heatmap: hour vs day
# ----------------------------
def plot_heatmap(df, filename="static/plots/heatmap.png"):
    os.makedirs("static/plots", exist_ok=True)
    df['hour'] = df.index.hour
    df['day'] = df.index.dayofweek
    pivot = df.pivot_table(values='vehicle_count', index='day', columns='hour', aggfunc='mean')
    plt.figure(figsize=(12,6))
    sns.heatmap(pivot, cmap="YlGnBu", annot=True, fmt=".0f")
    plt.title("Traffic Heatmap: Day vs Hour")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[OK] Heatmap saved to {filename}")

# ----------------------------
# Train and save ML model
# ----------------------------
def train_and_save_model():
    df = fetch_traffic_data()
    
    # Feature engineering
    df['hour'] = df.index.hour
    df['day_of_week'] = df.index.dayofweek
    X = df[['hour', 'day_of_week']]
    y = df['vehicle_count']
    
    # Train Linear Regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Save model
    os.makedirs("data", exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"[OK] Model trained and saved to {MODEL_PATH}")
    return model

# ----------------------------
# Load ML model
# ----------------------------
def load_model():
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"[OK] Model loaded from {MODEL_PATH}")
        return model
    else:
        print("[ERROR] Model not found. Please train first.")
        return None

# ----------------------------
# Predict traffic
# ----------------------------
def predict_traffic(model, features):
    # features = [hour, day_of_week]
    if model:
        pred = model.predict([features])[0]
        return round(pred, 2)
    return None

# ----------------------------
# Main (standalone test)
# ----------------------------
if __name__ == "__main__":
    df = fetch_traffic_data()
    
    hourly_avg, peak_hours = analyze_peak_hours(df)
    print("Average traffic per hour:\n", hourly_avg)
    print(f"\nDetected peak hour(s): {peak_hours}")
    
    daily_avg = analyze_daily_trends(df)
    print("\nDaily averages:\n", daily_avg)
    
    weekday_avg = traffic_by_weekday(df)
    print("\nWeekday averages:\n", weekday_avg)
    
    weather_corr = analyze_weather_correlation(df)
    if weather_corr is not None:
        print("\nWeather correlation:\n", weather_corr)
    
    plot_traffic(hourly_avg)
    plot_weekday_trends(weekday_avg)
    plot_heatmap(df)
    
    # Train model if not exists
    model = load_model()
    if model is None:
        model = train_and_save_model()
    
    # Predict example
    print("\nPredicted traffic at 10 AM on Monday:", predict_traffic(model, [10, 0]))
