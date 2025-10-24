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

    def predict_with_strategy(
        self,
        features_df: pd.DataFrame,
        abc_classification: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Predict with ABC-based strategy

        Args:
            features_df: Features DataFrame
            abc_classification: ABC classification DataFrame with columns [SKU, ABC, avg_sales]

        Returns:
            DataFrame with columns:
            - SKU
            - ABC_Category
            - Avg_Sales_6M
            - Predicted_Sales
            - Order_Qty
            - Recommendation (AUTO / MANUAL / MANUAL_REVIEW)
            - Confidence_Score
            - Anomaly_Score
            - Notes
        """
        self.logger.info("🎯 Predicting with ABC strategy...")

        # Get ABC strategy config
        strategy_config = self.config.get('prediction', {}).get('abc_strategy', {})

        # Merge ABC classification
        features_with_abc = features_df.merge(
            abc_classification[['SKU', 'ABC', 'avg_sales']],
            on='SKU',
            how='left'
        )

        # Generate base predictions
        predictions = self.predict(features_df, model_type='ensemble')

        results = []

        for idx, row in features_with_abc.iterrows():
            sku = row['SKU']
            abc_cat = row.get('ABC', 'UNKNOWN')
            avg_sales_6m = row.get('avg_sales', 0)
            pred = predictions[idx]

            # Detect anomalies
            anomaly_score = self._detect_anomaly(row)

            # Determine recommendation
            if abc_cat == 'A':
                recommendation = "MANUAL"
                confidence = 0.0
                order_qty = None
                notes = "High-volume A-Item: Manual forecasting required"

            elif abc_cat in ['B', 'C']:
                # Check for anomalies
                if anomaly_score > 0.7:
                    recommendation = "MANUAL_REVIEW"
                    confidence = 0.5
                    notes = f"⚠️ Anomaly detected (score: {anomaly_score:.2f}), review recommended"
                else:
                    recommendation = "AUTO"
                    confidence = 0.9 if abc_cat == 'B' else 0.7
                    notes = f"Reliable {abc_cat}-Item prediction"

                # Calculate order quantity
                if abc_cat == 'C':
                    # Conservative for C-Items
                    c_multiplier = strategy_config.get('c_item_multiplier', 1.2)
                    c_min_order = strategy_config.get('c_item_min_order', 5)
                    order_qty = max(pred * c_multiplier, c_min_order)
                else:
                    # Standard for B-Items
                    order_multiplier = self.config['business']['order_multiplier']
                    order_qty = pred * order_multiplier

            else:
                # Unknown ABC
                recommendation = "MANUAL"
                confidence = 0.0
                order_qty = None
                notes = "Unknown ABC category"

            results.append({
                'SKU': sku,
                'ABC_Category': abc_cat,
                'Avg_Sales_6M': avg_sales_6m,
                'Predicted_Sales': pred if recommendation != 'MANUAL' else None,
                'Order_Qty': order_qty,
                'Recommendation': recommendation,
                'Confidence_Score': confidence,
                'Anomaly_Score': anomaly_score,
                'Notes': notes
            })

        results_df = pd.DataFrame(results)

        # Log summary
        rec_counts = results_df['Recommendation'].value_counts()
        self.logger.info(f"   ✅ Prediction strategy applied:")
        self.logger.info(f"      AUTO: {rec_counts.get('AUTO', 0)} SKUs")
        self.logger.info(f"      MANUAL_REVIEW: {rec_counts.get('MANUAL_REVIEW', 0)} SKUs")
        self.logger.info(f"      MANUAL: {rec_counts.get('MANUAL', 0)} SKUs")

        return results_df

    def _detect_anomaly(self, features: pd.Series) -> float:
        """
        Detect anomaly score (0~1)

        Args:
            features: Feature row

        Returns:
            Anomaly score (0 = normal, 1 = highly anomalous)
        """
        score = 0.0

        # Get anomaly detection config
        anomaly_config = self.config.get('prediction', {}).get(
            'abc_strategy', {}
        ).get('anomaly_detection', {})

        if not anomaly_config.get('enabled', True):
            return 0.0

        # 1. PO spike
        if 'PO_Quantity' in features.index:
            po_current = features.get('PO_Quantity', 0)
            po_avg = features.get('po_rolling_mean_3', po_current)

            if po_avg > 0:
                po_spike_ratio = po_current / po_avg
                po_threshold = anomaly_config.get('po_spike_threshold', 3.0)

                if po_spike_ratio > po_threshold:
                    spike_score = min((po_spike_ratio - po_threshold) / po_threshold, 1.0) * 0.5
                    score += spike_score

        # 2. Sales volatility
        if 'sales_lag_1' in features.index:
            sales_recent = features.get('sales_lag_1', 0)
            sales_avg = features.get('sales_rolling_mean_3', sales_recent)

            if sales_avg > 0:
                sales_change = abs(sales_recent - sales_avg) / sales_avg
                change_threshold = anomaly_config.get('sales_change_threshold', 0.5)

                if sales_change > change_threshold:
                    volatility_score = min(sales_change / change_threshold - 1, 1.0) * 0.3
                    score += volatility_score

        # 3. On Sale status
        if features.get('Status_On_Sale', 0) == 1:
            on_sale_weight = anomaly_config.get('on_sale_weight', 0.2)
            score += on_sale_weight

        return min(score, 1.0)


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
