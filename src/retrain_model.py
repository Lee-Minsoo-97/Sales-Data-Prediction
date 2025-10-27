"""
Model Retraining Script for iHerb Sales Prediction

Usage:
    python retrain_model.py

This script will:
1. Load the latest processed data
2. Retrain LightGBM and XGBoost models
3. Backup old models
4. Save new models
5. Provide performance comparison and recommendations
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime
import lightgbm as lgb
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from utils import (
    load_config,
    resolve_path,
    setup_logging,
    calculate_metrics
)


class ModelRetrainer:
    """Handle model retraining with latest data"""

    def __init__(self, config_path=None):
        """Initialize retrainer"""
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)

        # Paths
        self.data_processed = resolve_path(self.config['paths']['data_processed'])
        self.models_dir = resolve_path(self.config['paths']['models_trained'])

        # Load data
        df_path = self.data_processed / 'df_for_modeling.csv'

        if not df_path.exists():
            raise FileNotFoundError(
                f"Processed data not found: {df_path}\n"
                f"Please run data_pipeline.py first!"
            )

        self.df = pd.read_csv(df_path, parse_dates=['Date'])

        self.logger.info("=" * 70)
        self.logger.info(f"📂 Loaded {len(self.df):,} records for retraining")
        self.logger.info(f"📅 Date range: {self.df['Date'].min().date()} ~ {self.df['Date'].max().date()}")
        self.logger.info(f"🏷️  Unique SKUs: {self.df['SKU'].nunique()}")
        self.logger.info("=" * 70)

    def prepare_train_test_split(self, test_months=2):
        """
        Time-based train/test split

        Args:
            test_months: Number of recent months for testing

        Returns:
            X_train, X_test, y_train, y_test
        """
        self.logger.info(f"\n📊 Preparing train/test split (last {test_months} months for testing)...")

        max_date = self.df['Date'].max()
        test_start = max_date - pd.DateOffset(months=test_months)

        train_df = self.df[self.df['Date'] < test_start].copy()
        test_df = self.df[self.df['Date'] >= test_start].copy()

        # Remove rows with insufficient history (first few months per SKU)
        train_df = train_df.dropna(subset=['sales_lag_1', 'po_quantity_lag_1'])
        test_df = test_df.dropna(subset=['sales_lag_1', 'po_quantity_lag_1'])

        self.logger.info(f"   Train: {len(train_df):,} rows ({train_df['Date'].min().date()} ~ {train_df['Date'].max().date()})")
        self.logger.info(f"   Test:  {len(test_df):,} rows ({test_df['Date'].min().date()} ~ {test_df['Date'].max().date()})")

        # Prepare features
        exclude_cols = self.config['features']['exclude_columns']
        feature_cols = [col for col in self.df.columns if col not in exclude_cols]

        # Additional columns to exclude (added during processing)
        additional_exclude = ['year', 'month', 'quarter', 'week_of_year',
                             'sales_rolling_mean', 'po_rolling_mean']
        feature_cols = [col for col in feature_cols if col not in additional_exclude]

        X_train = train_df[feature_cols]
        y_train = train_df['Sales']
        X_test = test_df[feature_cols]
        y_test = test_df['Sales']

        self.logger.info(f"   Features: {len(feature_cols)} columns")
        self.logger.info(f"   First 10 features: {feature_cols[:10]}")

        return X_train, X_test, y_train, y_test, feature_cols

    def train_lightgbm(self, X_train, y_train, X_test, y_test):
        """Train LightGBM model"""
        self.logger.info("\n🚀 Training LightGBM...")

        # Best hyperparameters (from original training)
        params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': 6,
            'min_child_samples': 20,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1
        }

        # Standardize column names (all underscores)
        X_train_std = X_train.copy()
        X_test_std = X_test.copy()
        X_train_std.columns = [col.replace('Brand Code_', 'Brand_Code_').replace(' ', '_')
                               for col in X_train_std.columns]
        X_test_std.columns = [col.replace('Brand Code_', 'Brand_Code_').replace(' ', '_')
                              for col in X_test_std.columns]

        train_data = lgb.Dataset(X_train_std, label=y_train)
        test_data = lgb.Dataset(X_test_std, label=y_test, reference=train_data)

        model = lgb.train(
            params,
            train_data,
            num_boost_round=1000,
            valid_sets=[test_data],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)]
        )

        # Evaluate
        y_pred = model.predict(X_test_std)
        metrics = calculate_metrics(y_test, y_pred)

        self.logger.info(f"   ✅ LightGBM Performance:")
        self.logger.info(f"      MAE:  {metrics['MAE']:.2f}")
        self.logger.info(f"      RMSE: {metrics['RMSE']:.2f}")
        self.logger.info(f"      MAPE: {metrics['MAPE']:.2f}%")
        self.logger.info(f"      R²:   {metrics['R2']:.4f}")

        return model, metrics

    def train_xgboost(self, X_train, y_train, X_test, y_test):
        """Train XGBoost model"""
        self.logger.info("\n🚀 Training XGBoost...")

        params = {
            'objective': 'reg:absoluteerror',
            'eval_metric': 'mae',
            'learning_rate': 0.05,
            'max_depth': 6,
            'min_child_weight': 3,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'random_state': 42,
            'n_jobs': -1
        }

        model = xgb.XGBRegressor(**params, n_estimators=1000)

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=50,
            verbose=100
        )

        # Evaluate
        y_pred = model.predict(X_test)
        metrics = calculate_metrics(y_test, y_pred)

        self.logger.info(f"   ✅ XGBoost Performance:")
        self.logger.info(f"      MAE:  {metrics['MAE']:.2f}")
        self.logger.info(f"      RMSE: {metrics['RMSE']:.2f}")
        self.logger.info(f"      MAPE: {metrics['MAPE']:.2f}%")
        self.logger.info(f"      R²:   {metrics['R2']:.4f}")

        return model, metrics

    def compare_with_old_models(self, new_lgbm_mae, new_xgb_mae, X_test, y_test):
        """Compare new models with old models"""
        self.logger.info("\n📊 Comparing with old models...")

        old_lgbm_path = self.models_dir / 'lgbm_model_v1.2.pkl'
        old_xgb_path = self.models_dir / 'xgb_model_v2_0.pkl'

        if not old_lgbm_path.exists() or not old_xgb_path.exists():
            self.logger.warning("   Old models not found. Skipping comparison.")
            return

        # Load old models
        old_lgbm = joblib.load(old_lgbm_path)
        old_xgb = joblib.load(old_xgb_path)

        # Predict with old models
        # LightGBM: standardize column names
        X_test_lgbm = X_test.copy()
        X_test_lgbm.columns = [col.replace('Brand Code_', 'Brand_Code_').replace(' ', '_')
                               for col in X_test_lgbm.columns]

        old_lgbm_pred = old_lgbm.predict(X_test_lgbm[old_lgbm.feature_name_])
        old_xgb_pred = old_xgb.predict(X_test)

        old_lgbm_mae = mean_absolute_error(y_test, old_lgbm_pred)
        old_xgb_mae = mean_absolute_error(y_test, old_xgb_pred)

        # Calculate ensemble
        old_weights = self.config['ensemble']['weights']
        old_ensemble_pred = (old_weights['lightgbm'] * old_lgbm_pred +
                            old_weights['xgboost'] * old_xgb_pred)
        old_ensemble_mae = mean_absolute_error(y_test, old_ensemble_pred)

        # Calculate new ensemble
        new_lgbm_weight = (1/new_lgbm_mae) / ((1/new_lgbm_mae) + (1/new_xgb_mae))
        new_xgb_weight = (1/new_xgb_mae) / ((1/new_lgbm_mae) + (1/new_xgb_mae))

        self.logger.info("\n" + "=" * 70)
        self.logger.info("📈 PERFORMANCE COMPARISON")
        self.logger.info("=" * 70)
        self.logger.info(f"\n{'Model':<20} {'Old MAE':>12} {'New MAE':>12} {'Improvement':>12}")
        self.logger.info("-" * 70)
        self.logger.info(f"{'LightGBM':<20} {old_lgbm_mae:>12.2f} {new_lgbm_mae:>12.2f} {old_lgbm_mae - new_lgbm_mae:>12.2f}")
        self.logger.info(f"{'XGBoost':<20} {old_xgb_mae:>12.2f} {new_xgb_mae:>12.2f} {old_xgb_mae - new_xgb_mae:>12.2f}")
        self.logger.info("-" * 70)

        # Show ensemble weights
        self.logger.info(f"\nEnsemble Weights:")
        self.logger.info(f"  Old: LightGBM {old_weights['lightgbm']:.3f}, XGBoost {old_weights['xgboost']:.3f}")
        self.logger.info(f"  New: LightGBM {new_lgbm_weight:.3f}, XGBoost {new_xgb_weight:.3f}")

        return new_lgbm_weight, new_xgb_weight

    def backup_old_models(self):
        """Backup existing models"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        old_lgbm = self.models_dir / 'lgbm_model_v1.2.pkl'
        old_xgb = self.models_dir / 'xgb_model_v2_0.pkl'

        if old_lgbm.exists():
            backup_name = f'lgbm_model_v1.2_backup_{timestamp}.pkl'
            backup_path = self.models_dir / backup_name
            joblib.dump(joblib.load(old_lgbm), backup_path)
            self.logger.info(f"   📦 Backed up LightGBM → {backup_name}")

        if old_xgb.exists():
            backup_name = f'xgb_model_v2_0_backup_{timestamp}.pkl'
            backup_path = self.models_dir / backup_name
            joblib.dump(joblib.load(old_xgb), backup_path)
            self.logger.info(f"   📦 Backed up XGBoost → {backup_name}")

    def save_new_models(self, lgbm_model, xgb_model):
        """Save newly trained models"""
        timestamp = datetime.now().strftime('%Y%m%d')

        # Save with timestamp
        lgbm_path = self.models_dir / f'lgbm_model_retrained_{timestamp}.pkl'
        xgb_path = self.models_dir / f'xgb_model_retrained_{timestamp}.pkl'

        joblib.dump(lgbm_model, lgbm_path)
        joblib.dump(xgb_model, xgb_path)

        # Also save as current version (overwrite)
        current_lgbm = self.models_dir / 'lgbm_model_v1.2.pkl'
        current_xgb = self.models_dir / 'xgb_model_v2_0.pkl'

        joblib.dump(lgbm_model, current_lgbm)
        joblib.dump(xgb_model, current_xgb)

        self.logger.info(f"\n💾 Models saved:")
        self.logger.info(f"   ✅ {lgbm_path.name}")
        self.logger.info(f"   ✅ {xgb_path.name}")
        self.logger.info(f"   ✅ lgbm_model_v1.2.pkl (current)")
        self.logger.info(f"   ✅ xgb_model_v2_0.pkl (current)")

    def run(self, test_months=2):
        """
        Run full retraining pipeline

        Args:
            test_months: Number of recent months to use for testing
        """
        self.logger.info("\n" + "=" * 70)
        self.logger.info("🔄 STARTING MODEL RETRAINING")
        self.logger.info("=" * 70)

        # 1. Prepare data
        X_train, X_test, y_train, y_test, feature_cols = self.prepare_train_test_split(test_months)

        # 2. Train models
        lgbm_model, lgbm_metrics = self.train_lightgbm(X_train, y_train, X_test, y_test)
        xgb_model, xgb_metrics = self.train_xgboost(X_train, y_train, X_test, y_test)

        # 3. Compare with old models
        new_weights = self.compare_with_old_models(
            lgbm_metrics['MAE'],
            xgb_metrics['MAE'],
            X_test,
            y_test
        )

        # 4. Backup old models
        self.logger.info("\n📦 Backing up old models...")
        self.backup_old_models()

        # 5. Save new models
        self.save_new_models(lgbm_model, xgb_model)

        # 6. Provide recommendations
        self.logger.info("\n" + "=" * 70)
        self.logger.info("📋 NEXT STEPS")
        self.logger.info("=" * 70)

        if new_weights:
            new_lgbm_weight, new_xgb_weight = new_weights
            self.logger.info("\n1️⃣  Update config.yaml ensemble weights:")
            self.logger.info(f"   ensemble:")
            self.logger.info(f"     weights:")
            self.logger.info(f"       lightgbm: {new_lgbm_weight:.3f}")
            self.logger.info(f"       xgboost: {new_xgb_weight:.3f}")

        self.logger.info("\n2️⃣  Test new models:")
        self.logger.info("   python generate_forecast.py --auto")

        self.logger.info("\n3️⃣  Compare predictions with old models before deploying")

        self.logger.info("\n" + "=" * 70)
        self.logger.info("✅ RETRAINING COMPLETE!")
        self.logger.info("=" * 70)


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("iHerb Sales Prediction - Model Retraining")
    print("=" * 70)

    # Confirm with user
    print("\nThis will:")
    print("  1. Retrain LightGBM and XGBoost with latest data")
    print("  2. Backup current models")
    print("  3. Replace models with new versions")
    print("  4. Provide performance comparison")

    response = input("\nProceed with retraining? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("❌ Retraining cancelled.")
        return

    # Run retraining
    try:
        retrainer = ModelRetrainer()
        retrainer.run(test_months=2)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
