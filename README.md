# iHerb Sales Forecasting System

End-to-end machine learning system for predicting monthly SKU-level sales using historical sales data and purchase order (PO) information.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Model Performance](#model-performance)
- [Improvements from Gemini Version](#improvements-from-gemini-version)

---

## 🎯 Overview

This system predicts future monthly sales quantities for individual SKUs by combining:
- **Historical Sales Data**: Monthly sales records per SKU
- **Purchase Order (PO) Data**: iHerb's ordering history
- **Ensemble ML Models**: LightGBM + XGBoost for robust predictions

### Key Capabilities
- ✅ Automated data pipeline for processing sales and PO data
- ✅ Advanced feature engineering (lag, rolling, categorical)
- ✅ Ensemble predictions using optimized LightGBM & XGBoost models
- ✅ Business insights (Fill Rate, Stockout, Overstock analysis)
- ✅ ABC classification for inventory management

---

## 🚀 Features

### Data Pipeline
- Automated consolidation of monthly sales CSV files
- PO data aggregation by SKU and month
- Data validation and cleaning
- Feature engineering:
  - Lag features (1, 2, 3 months)
  - Rolling averages (3 months)
  - Time-based features (year, month, quarter, week)
  - One-hot encoded categorical variables

### Prediction System
- **Ensemble Model**: Weighted combination of LightGBM (48.5%) + XGBoost (51.5%)
- **Individual Models**: Use LightGBM or XGBoost separately if needed
- **Confidence Handling**: Automatically flags SKUs with insufficient history
- **Business Rules**: Configurable order multipliers and ABC thresholds

### Analysis Tools
- Fill Rate calculation
- Stockout/Overstock identification
- ABC classification (Pareto analysis)
- Performance tracking and logging

---

## 📁 Project Structure

```
Sales-Data-Prediction/
├── config.yaml                    # Configuration file
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
├── IMPROVEMENTS.md                # Detailed improvement documentation
│
├── data/
│   ├── raw_sales/                 # Monthly sales CSV files (YYYY.MM_BBG.csv)
│   ├── raw_po/                    # PO data (sps_data.csv)
│   └── processed/                 # Processed data (df_for_modeling.csv)
│
├── models/
│   └── trained/                   # Trained model files (.pkl)
│       ├── lgbm_model_v1.2.pkl
│       └── xgb_model_v2_0.pkl
│
├── src/
│   ├── utils.py                   # Utility functions
│   ├── data_pipeline.py           # Data processing pipeline
│   └── prediction.py              # Prediction module
│
├── logs/                          # Log files (auto-generated)
├── predictions/                   # Prediction outputs (auto-generated)
│
└── notebooks/                     # Original Gemini Colab notebooks (reference)
    ├── iHerb_Sales_Pred_ML_Project_v1_0.ipynb
    ├── iHerb_Sales_Pred_ML_Project_v2_0.ipynb
    ├── iHerb_Sales_Pred_ML_Project_Ensemble.ipynb
    ├── Forecasting_EDA.ipynb
    └── Valuation.ipynb
```

---

## 💻 Installation

### Prerequisites
- Python 3.8+
- pip

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Lee-Minsoo-97/Sales-Data-Prediction.git
   cd Sales-Data-Prediction
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**
   ```bash
   python -c "import pandas, lightgbm, xgboost; print('✅ All packages installed successfully!')"
   ```

---

## ⚡ Quick Start

### 1. Run Data Pipeline

Process raw sales and PO data:

```bash
cd src
python data_pipeline.py
```

**Output**: `data/processed/df_for_modeling.csv`

### 2. Generate Predictions

Predict sales for a future month:

```bash
python prediction.py
```

**Output**: `predictions/predictions_YYYYMM.csv`

---

## 📖 Usage Guide

### A. Data Pipeline

```python
from src.data_pipeline import SalesDataPipeline

# Initialize pipeline
pipeline = SalesDataPipeline()

# Run full pipeline
df_processed = pipeline.run()
```

### B. Prediction

```python
from src.prediction import SalesPredictor

# Initialize predictor
predictor = SalesPredictor()

# Load historical data
historical_df = predictor.load_historical_data()

# Prepare features for specific date
target_date = '2025-09-01'
features_df, metadata_df = predictor.prepare_features_for_prediction(
    historical_df,
    target_date
)

# Generate predictions (ensemble)
predictions = predictor.predict(features_df, model_type='ensemble')
```

---

## ⚙️ Configuration

Edit `config.yaml` to customize settings.

---

## 📊 Model Performance

### Test Set Performance (July-August 2025)

| Model | MAE |
|-------|-----|
| **Ensemble (Weighted)** | **38.00** |
| LightGBM v1.2 | 40.81 |
| XGBoost v2.0 | 35.79 |

### Business Metrics

- **Fill Rate**: 89.19%
- **Total Stockout**: ~7,400 units
- **Total Overstock**: ~37,900 units

---

## 🔧 Improvements from Gemini Version

✅ **Modular Architecture**: Separated into utils, data_pipeline, prediction
✅ **Error Handling**: Comprehensive validation and logging
✅ **Configuration Management**: Centralized YAML config
✅ **Environment Agnostic**: Runs locally, on servers, anywhere

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for details.

---

## 📈 Next Steps

1. **Promotion Data Integration** - Improve A-Item accuracy
2. **Automated Retraining** - Monthly model updates
3. **Web Interface** - User-friendly prediction app

---

**Last Updated**: 2025-10-24