import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(filename="sample_sensor_data.csv", points=1000):
    print(f"Generating {points} sample data points...")
    
    # Time range
    start_time = datetime.now()
    timestamps = [start_time + timedelta(milliseconds=10*i) for i in range(points)]
    
    # 1. Vibration Signal (Sine wave + Noise)
    # 50Hz signal sampled at 100Hz (Nyquist limit edge, but okay for demo)
    t = np.linspace(0, 10, points)
    vibration = 2.5 * np.sin(2 * np.pi * 5 * t) + np.random.normal(0, 0.2, points)
    
    # 2. Temperature Signal (Slow Trend)
    temperature = np.linspace(45, 65, points) + np.random.normal(0, 0.05, points)
    
    # Create DataFrame
    df = pd.DataFrame({
        "timestamp": timestamps,
        "vibration_mm_s": vibration,
        "temperature_c": temperature
    })
    
    # Save
    df.to_csv(filename, index=False)
    print(f"File saved: {filename}")

if __name__ == "__main__":
    generate_sample_data()
