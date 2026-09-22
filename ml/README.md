# Machine Learning & Demand Forecasting Subsystem

This module contains data exploration scripts, feature engineering pipelines, and forecasting models for **Jett 2 Holiday**.

## Contents
- `explore_dataset.py`: Quick command-line utility to connect to `../data/APS-02.db` and output schema definitions, row counts, and sample records.
- `dataset_exploration.ipynb`: Interactive Jupyter Notebook for exploratory data analysis (EDA).
- `requirements.txt`: Python dependencies (`pandas`, `scikit-learn`, `prophet`, `matplotlib`).

## Running the Explorer
```bash
# From workspace root
python ml/explore_dataset.py
```

## Upcoming Forecasting Pipeline (Phase 2)
1. **Outlier Filtering**: IQR clipping to cap deliberate ~1% rate outliers beyond the 99th percentile.
2. **Feature Engineering**:
   - Recency decay: $\exp(-k_r \cdot \text{days\_since\_event})$
   - Booking commitment: $\exp(-k_c \cdot \text{lead\_time\_days})$
   - Conversion-weighted aggregation of search/view/booking volumes.
3. **Forecasting Engine**:
   - Meta Prophet for seasonal baseline and day-of-week trends.
   - Linear Regression model to predict booking counts per entity per date, decomposing directly into factor contributions without needing black-box approximations.
