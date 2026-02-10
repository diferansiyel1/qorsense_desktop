---
name: python-data-science-pro
description: Advanced Python data science for handling massive datasets and high-performance machine learning. Specializes in Polars, Dask, Ray, and advanced model optimization (XGBoost, Optuna, HPO). Use PROACTIVELY for large-scale data processing, distributed ML, or pipeline acceleration.
---

## Use this skill when

- Working with "medium to large" data that doesn't fit in standard Pandas.
- Accelerating data pipelines using `Polars` or `Dask`.
- Implementing high-performance machine learning models (GBMs, ensembles).
- Performing complex hyperparameter optimization (HPO) with `Optuna`.
- Building distributed data processing or training tasks with `Ray`.

## Instructions

- Prefer **Polars** over Pandas for performance-critical data manipulation.
- Use **Dask** or **Ray** for distributed computing beyond a single core.
- Implement **Vectorization** with NumPy for mathematical operations.
- Use **Optuna** for efficient, Bayesian-based hyperparameter tuning.
- Follow **scikit-learn** compatible patterns for custom transformers/estimators.

## Capabilities

### High-Performance Data Processing
- **Polars Mastery**: Lazy-evaluation, multi-threaded expressions, and Apache Arrow integration.
- **NumPy Expert**: Advanced indexing, broadcasting, and memory-efficient array operations.
- **Dask / Ray**: Parallelizing Python code across clusters or multiple CPUs.
- **Data Schemas**: Using `Pydantic` or `Pandera` for strict data validation and typing.

### Advanced Machine Learning
- **Gradient Boosting**: Master-level tuning of XGBoost, LightGBM, and CatBoost.
- **Hyperparameter Tuning**: `Optuna` prune-and-search strategies (TPESampler).
- **AutoML Integration**: Using `H2O`, `AutoGluon`, or `TPOT` for rapid prototyping.
- **Feature Stores**: Integration with `Feast` or `Tecton` (conceptual or actual).

### Scalability & Efficiency
- **Memory Optimization**: Efficient dtypes, generator-based processing, and chunking.
- **Serialization**: Using `Parquet`, `Avro`, or `Feather` for fast I/O.
- **Pipeline Orchestration**: Best practices for `Prefect`, `Dagster`, or `Airflow` (modular logic).

### Visualization for Data Science
- **Interactive Viz**: Using `Plotly`, `Boken`, or `Streamlit` for data apps.
- **Statistical Viz**: Advanced `Seaborn` and `Matplotlib` for publication-ready figures.

## Example Interactions
- "Convert this slow Pandas pipeline to Polars for 10x speedup."
- "Implement an Optuna study to find the best LightGBM parameters for this dataset."
- "Scale my data processing task across 8 cores using Dask."
- "Design a memory-efficient pipeline to process 50GB of CSV files using chunking and Parquet."
