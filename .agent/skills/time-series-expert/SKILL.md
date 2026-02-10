---
name: time-series-expert
description: Master time series analysis, forecasting, and temporal data engineering. Handles decomposition, stationarity, seasonal adjustment, and advanced modeling with Statistical, Machine Learning, and Deep Learning approaches. Use PROACTIVELY for demand forecasting, financial analysis, anomaly detection, or IoT sensor data processing.
---

## Use this skill when

- Analyzing data with a temporal component (timestamped data).
- Performing forecasting (predicting future values based on history).
- Detecting anomalies or change points in time-evolving systems.
- Engineering features from time series (lags, windows, Fourier transforms).
- Dealing with stationarity, trend, and seasonality issues.

## Instructions

- Check for **stationarity** (ADF, KPSS tests) before applying linear models.
- Use **Cross-Validation** specifically designed for time series (TimeSeriesSplit).
- Account for **Seasonality** (Daily, Weekly, Yearly) and **Holidays**.
- Prefer **ensemble methods** or **hybrid models** for complex real-world data.
- Evaluate models using temporal-specific metrics like **MAE**, **RMSE**, **MAPE**, and **MASE**.

## Capabilities

### Traditional Statistical Models
- **ARIMA/SARIMA/SARIMAX**: Classical linear forecasting.
- **Exponential Smoothing**: ETS, Holt-Winters for trend and seasonality.
- **VAR/VECM**: Multivariate time series and cointegration analysis.
- **GARCH**: Modeling volatility in financial time series.

### Modern Forecasting Frameworks
- **Prophet (Meta)**: Automatic forecasting for business data with holiday effects.
- **NeuralProphet**: Hybrid Prophet/PyTorch models.
- **sktime / Darts**: Unified APIs for time series machine learning.
- **StatsForecast / Nixtla**: High-performance statistical forecasting at scale.

### Machine Learning & Deep Learning
- **Gradient Boosting**: Using XGBoost, LightGBM, or CatBoost with lag features.
- **Recurrent Neural Networks**: LSTM, GRU for long-range dependencies.
- **Temporal Fusion Transformers (TFT)**: Advanced multi-horizon forecasting.
- **DeepAR**: Probabilistic forecasting with Deep Learning.

### Temporal Feature Engineering
- **Lag Features**: Creating shifted data points (L1, L7, L30).
- **Rolling/Expanding Windows**: Mean, Std, Max over time intervals.
- **Fourier Transforms**: Converting time domain to frequency domain for seasonality.
- **Calendar Features**: Extracting day of week, month, payday, etc.

## Example Interactions
- "Analyze this sensor data for anomalies and forecast the next 24 hours."
- "Build a Prophet model to predict retail sales, accounting for Black Friday."
- "Perform a stationarity test and decompose this series into trend and noise."
- "Convert this multivariate time series into a supervised learning problem for XGBoost."
