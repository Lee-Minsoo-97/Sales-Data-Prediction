"""
Prediction Module for iHerb Sales Forecasting

This module handles:
1. Loading trained models
2. Preparing features for future predictions
3. Generating predictions (ensemble or individual models)
4. Business analysis (Fill Rate, Stockout, Overstock)
5. ABC classification
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime

from utils import (
    load_config,
    resolve_path,
    setup_logging,
    calculate_metrics
)


class SalesPredictor:
    """Predict future sales using trained models"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the predictor

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)
        self.logger.info("=" * 60)
        self.logger.info("🔮 Initializing Sales Predictor")
        self.logger.info("=" * 60)

        # Setup paths
        self._setup_paths()

        # Load models
        self.models = {}
        self._load_models()

    def _setup_paths(self):
        """Setup directory paths"""
        paths = self.config['paths']
        self.data_processed = resolve_path(paths['data_processed'])
        self.models_dir = resolve_path(paths['models_trained'])
        self.predictions_dir = resolve_path(paths['predictions'])
        self.predictions_dir.mkdir(parents=True, exist_ok=True)

    def _load_models(self):
        """Load trained models"""
        self.logger.info("📦 Loading trained models...")

        # Load LightGBM
        lgbm_path = self.models_dir / 'lgbm_model_v1.2.pkl'
        if lgbm_path.exists():
            self.models['lightgbm'] = joblib.load(lgbm_path)
            self.logger.info(f"   ✅ LightGBM loaded from {lgbm_path.name}")
        else:
            self.logger.warning(f"   ⚠️  LightGBM model not found at {lgbm_path}")

        # Load XGBoost
        xgb_path = self.models_dir / 'xgb_model_v2_0.pkl'
        if xgb_path.exists():
            self.models['xgboost'] = joblib.load(xgb_path)
            self.logger.info(f"   ✅ XGBoost loaded from {xgb_path.name}")
        else:
            self.logger.warning(f"   ⚠️  XGBoost model not found at {xgb_path}")

    def load_historical_data(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load historical data for feature generation

        Args:
            filepath: Path to processed data file

        Returns:
            Historical DataFrame
        """
        if filepath is None:
            filepath = self.data_processed / 'df_for_modeling.csv'

        df = pd.read_csv(filepath, parse_dates=['Date'])
        self.logger.info(f"📂 Loaded historical data: {df.shape}")

        return df

    def prepare_features_for_prediction(
        self,
        historical_df: pd.DataFrame,
        target_date: str,
        sku_list: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare features for prediction on a specific date

        Args:
            historical_df: Historical data DataFrame
            target_date: Target prediction date (YYYY-MM-DD)
            sku_list: List of SKUs to predict for (None = all SKUs)

        Returns:
            Tuple of (features_df, metadata_df)
        """
        self.logger.info(f"⚙️  Preparing features for {target_date}...")

        target_dt = pd.to_datetime(target_date)
        min_history = self.config['prediction']['min_history_months']

        # Filter SKUs if provided
        if sku_list:
            historical_df = historical_df[historical_df['SKU'].isin(sku_list)]

        # Get unique SKUs
        all_skus = historical_df['SKU'].unique()

        features_list = []
        metadata_list = []

        for sku in all_skus:
            sku_data = historical_df[historical_df['SKU'] == sku].copy()
            sku_data = sku_data.sort_values('Date')

            # Get recent history (last 3 months for lag features)
            recent_data = sku_data[sku_data['Date'] < target_dt].tail(3)

            # Check if sufficient history exists
            if len(recent_data) < min_history:
                metadata_list.append({
                    'SKU': sku,
                    'status': 'insufficient_history',
                    'available_months': len(recent_data)
                })
                continue

            # Create feature row for target date
            feature_row = {'SKU': sku, 'Date': target_dt}

            # Time-based features
            feature_row['year'] = target_dt.year
            feature_row['month'] = target_dt.month
            feature_row['quarter'] = target_dt.quarter
            feature_row['week_of_year'] = target_dt.isocalendar()[1]

            # Lag features (1, 2, 3 months)
            lag_periods = self.config['features']['lag_periods']
            for i, lag in enumerate(lag_periods):
                if i < len(recent_data):
                    row_idx = -(i + 1)
                    feature_row[f'sales_lag_{lag}'] = recent_data.iloc[row_idx]['Sales']
                    feature_row[f'po_quantity_lag_{lag}'] = recent_data.iloc[row_idx]['PO_Quantity']
                else:
                    feature_row[f'sales_lag_{lag}'] = 0
                    feature_row[f'po_quantity_lag_{lag}'] = 0

            # Rolling features (3-month average)
            if len(recent_data) >= 3:
                feature_row['sales_rolling_mean'] = recent_data['Sales'].mean()
                feature_row['po_rolling_mean'] = recent_data['PO_Quantity'].mean()
            else:
                feature_row['sales_rolling_mean'] = recent_data['Sales'].mean()
                feature_row['po_rolling_mean'] = recent_data['PO_Quantity'].mean()

            # Categorical features (copy from most recent record)
            latest_record = recent_data.iloc[-1]

            # Status dummies
            status_cols = [col for col in latest_record.index if col.startswith('Status_')]
            for col in status_cols:
                feature_row[col] = latest_record[col]

            # Brand Code dummies
            brand_cols = [col for col in latest_record.index if col.startswith('Brand Code_')]
            for col in brand_cols:
                feature_row[col] = latest_record[col]

            features_list.append(feature_row)
            metadata_list.append({
                'SKU': sku,
                'status': 'ready',
                'available_months': len(recent_data)
            })

        # Create DataFrames
        features_df = pd.DataFrame(features_list).fillna(0)
        metadata_df = pd.DataFrame(metadata_list)

        self.logger.info(f"   ✅ Prepared features for {len(features_df)} SKUs")
        insufficient = len(metadata_df[metadata_df['status'] == 'insufficient_history'])
        if insufficient > 0:
            self.logger.warning(f"   ⚠️  {insufficient} SKUs skipped (insufficient history)")

        return features_df, metadata_df

    def predict(
        self,
        features_df: pd.DataFrame,
        model_type: str = 'ensemble'
    ) -> np.ndarray:
        """
        Generate predictions

        Args:
            features_df: Features DataFrame
            model_type: 'ensemble', 'lightgbm', or 'xgboost'

        Returns:
            Array of predictions
        """
        # Get feature columns (exclude SKU, Date, etc.)
        exclude_cols = self.config['features']['exclude_columns']
        feature_cols = [col for col in features_df.columns
                       if col not in exclude_cols]

        X = features_df[feature_cols]

        if model_type == 'ensemble':
            # Ensemble prediction
            weights = self.config['ensemble']['weights']

            lgbm_pred = self.models['lightgbm'].predict(X)
            xgb_pred = self.models['xgboost'].predict(X)

            predictions = (
                weights['lightgbm'] * lgbm_pred +
                weights['xgboost'] * xgb_pred
            )

        elif model_type == 'lightgbm':
            predictions = self.models['lightgbm'].predict(X)

        elif model_type == 'xgboost':
            predictions = self.models['xgboost'].predict(X)

        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        return predictions

    def generate_business_insights(
        self,
        predictions_df: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate business insights from predictions

        Args:
            predictions_df: DataFrame with columns [SKU, Actual_Sales, Predicted_Sales]

        Returns:
            Dictionary of insight DataFrames
        """
        self.logger.info("📊 Generating business insights...")

        order_multiplier = self.config['business']['order_multiplier']

        df = predictions_df.copy()

        # Calculate order quantity
        df['Order_Quantity'] = df['Predicted_Sales'] * order_multiplier

        # Calculate met demand
        df['Met_Demand'] = np.minimum(df['Actual_Sales'], df['Order_Quantity'])

        # Calculate stockout
        df['Stockout_Quantity'] = np.maximum(0, df['Actual_Sales'] - df['Order_Quantity'])

        # Calculate overstock
        df['Overstock_Quantity'] = np.maximum(0, df['Order_Quantity'] - df['Actual_Sales'])

        # Fill Rate
        total_sales = df['Actual_Sales'].sum()
        total_met = df['Met_Demand'].sum()
        fill_rate = (total_met / total_sales * 100) if total_sales > 0 else 0

        # Top stockouts
        top_stockouts = df.nlargest(10, 'Stockout_Quantity')[
            ['SKU', 'Actual_Sales', 'Order_Quantity', 'Stockout_Quantity']
        ]

        # Top overstocks
        top_overstocks = df.nlargest(10, 'Overstock_Quantity')[
            ['SKU', 'Actual_Sales', 'Order_Quantity', 'Overstock_Quantity']
        ]

        self.logger.info(f"   📈 Fill Rate: {fill_rate:.2f}%")
        self.logger.info(f"   📉 Total Stockout: {df['Stockout_Quantity'].sum():,.0f}")
        self.logger.info(f"   📦 Total Overstock: {df['Overstock_Quantity'].sum():,.0f}")

        return {
            'summary': df,
            'fill_rate': fill_rate,
            'top_stockouts': top_stockouts,
            'top_overstocks': top_overstocks
        }

    def abc_classification(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify SKUs into ABC categories based on sales volume

        Args:
            df: DataFrame with 'SKU' and 'Actual_Sales' columns

        Returns:
            DataFrame with 'ABC_Category' column added
        """
        df = df.copy()

        # Sort by sales (descending)
        df = df.sort_values('Actual_Sales', ascending=False)

        # Calculate cumulative percentage
        df['cumulative_sales'] = df['Actual_Sales'].cumsum()
        total_sales = df['Actual_Sales'].sum()
        df['cumulative_pct'] = df['cumulative_sales'] / total_sales

        # Classify
        thresholds = self.config['business']['abc_thresholds']

        df['ABC_Category'] = 'C'
        df.loc[df['cumulative_pct'] <= thresholds['B'], 'ABC_Category'] = 'B'
        df.loc[df['cumulative_pct'] <= thresholds['A'], 'ABC_Category'] = 'A'

        # Drop temporary columns
        df = df.drop(columns=['cumulative_sales', 'cumulative_pct'])

        # Log counts
        abc_counts = df['ABC_Category'].value_counts()
        self.logger.info(f"   📊 ABC Classification: A={abc_counts.get('A', 0)}, "
                        f"B={abc_counts.get('B', 0)}, C={abc_counts.get('C', 0)}")

        return df

    def save_predictions(
        self,
        df: pd.DataFrame,
        target_date: str,
        prefix: str = 'predictions'
    ):
        """
        Save predictions to CSV

        Args:
            df: Predictions DataFrame
            target_date: Target prediction date
            prefix: Filename prefix
        """
        date_str = pd.to_datetime(target_date).strftime('%Y%m')
        filename = f"{prefix}_{date_str}.csv"
        output_path = self.predictions_dir / filename

        decimal_places = self.config['prediction']['decimal_places']
        df = df.round(decimal_places)

        df.to_csv(output_path, index=False)

        self.logger.info(f"💾 Predictions saved to: {output_path}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    # Example usage
    predictor = SalesPredictor()

    # Load historical data
    historical_df = predictor.load_historical_data()

    # Prepare features for September 2025
    target_date = '2025-09-01'
    features_df, metadata_df = predictor.prepare_features_for_prediction(
        historical_df,
        target_date
    )

    # Generate predictions
    predictions = predictor.predict(features_df, model_type='ensemble')

    # Create results DataFrame
    results_df = pd.DataFrame({
        'SKU': features_df['SKU'],
        'Predicted_Sales': predictions
    })

    print("\n🔮 Prediction Results:")
    print(results_df.head(10))

    # Save predictions
    predictor.save_predictions(results_df, target_date)
