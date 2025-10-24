"""
Data Pipeline for iHerb Sales Prediction System

This module handles:
1. Loading and consolidating monthly sales data
2. Loading and aggregating PO data
3. Data cleaning and validation
4. Feature engineering
5. Saving processed data
"""

import pandas as pd
import numpy as np
import glob
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging

from utils import (
    load_config,
    resolve_path,
    setup_logging,
    validate_dataframe,
    set_random_seed
)


class SalesDataPipeline:
    """Pipeline for processing iHerb sales and PO data"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the data pipeline

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)
        self.logger.info("=" * 60)
        self.logger.info("🚀 Initializing Sales Data Pipeline")
        self.logger.info("=" * 60)

        # Set random seed
        seed = self.config['model']['random_state']
        set_random_seed(seed)

        # Initialize paths
        self._setup_paths()

    def _setup_paths(self):
        """Setup directory paths from config"""
        paths = self.config['paths']
        self.data_raw_sales = resolve_path(paths['data_raw_sales'])
        self.data_raw_po = resolve_path(paths['data_raw_po'])
        self.data_processed = resolve_path(paths['data_processed'])

        # Ensure directories exist
        self.data_processed.mkdir(parents=True, exist_ok=True)

    def load_sales_data(self) -> pd.DataFrame:
        """
        Load and consolidate monthly sales CSV files

        Returns:
            Consolidated sales DataFrame
        """
        self.logger.info("📂 Loading sales data...")

        # Get all sales CSV files
        sales_pattern = self.config['data']['sales_file_pattern']
        sales_files = sorted(self.data_raw_sales.glob(sales_pattern))

        if not sales_files:
            raise FileNotFoundError(
                f"No sales files found matching pattern: {sales_pattern}"
            )

        self.logger.info(f"   Found {len(sales_files)} sales files")

        all_data = []

        for file_path in sales_files:
            # Extract date from filename (e.g., "2024.05_BBG.csv" -> "2024.05")
            date_str = file_path.stem.split('_')[0]

            # Read CSV
            df = pd.read_csv(file_path)

            # Dynamically find Status and Sales columns
            status_col = [col for col in df.columns if col.endswith('_Status')]
            if status_col:
                df.rename(columns={status_col[0]: 'Status'}, inplace=True)

            # Assume last column is sales
            sales_col = df.columns[-1]
            df.rename(columns={sales_col: 'Sales'}, inplace=True)

            # Add Date column
            df['Date'] = pd.to_datetime(date_str, format='%Y.%m')

            all_data.append(df)

        # Concatenate all months
        master_df = pd.concat(all_data, ignore_index=True)

        self.logger.info(f"   ✅ Loaded {len(master_df):,} records from sales data")

        return master_df

    def load_po_data(self) -> pd.DataFrame:
        """
        Load and aggregate PO (Purchase Order) data

        Returns:
            Aggregated PO DataFrame with monthly totals per SKU
        """
        self.logger.info("📂 Loading PO data...")

        po_file = self.config['data']['po_file_name']
        po_path = self.data_raw_po / po_file

        if not po_path.exists():
            raise FileNotFoundError(f"PO file not found: {po_path}")

        # Read PO data
        df_po = pd.read_csv(po_path)

        # Select relevant columns
        df_po = df_po[['PO Date', 'SKU', 'Qty Ordered']].copy()

        # Convert PO Date to datetime
        df_po['PO_Date_dt'] = pd.to_datetime(df_po['PO Date'], errors='coerce')

        # Drop rows with invalid dates
        df_po = df_po.dropna(subset=['PO_Date_dt'])

        # Create YearMonth column for aggregation
        df_po['YearMonth'] = df_po['PO_Date_dt'].dt.to_period('M')

        # Aggregate by SKU and Month
        monthly_po = df_po.groupby(['SKU', 'YearMonth'])['Qty Ordered'].sum().reset_index()
        monthly_po.rename(columns={'Qty Ordered': 'PO_Quantity'}, inplace=True)

        # Convert YearMonth back to datetime (first day of month)
        monthly_po['YearMonth'] = monthly_po['YearMonth'].dt.to_timestamp()

        self.logger.info(f"   ✅ Aggregated {len(monthly_po):,} SKU-Month PO records")

        return monthly_po

    def clean_data(self, df_sales: pd.DataFrame) -> pd.DataFrame:
        """
        Clean sales data

        Args:
            df_sales: Raw sales DataFrame

        Returns:
            Cleaned DataFrame
        """
        self.logger.info("🧹 Cleaning data...")

        df = df_sales.copy()

        # Convert Sales to numeric
        df['Sales'] = pd.to_numeric(df['Sales'], errors='coerce').fillna(0)

        # Convert UPC Code to nullable integer
        df['UPC Code'] = pd.to_numeric(df['UPC Code'], errors='coerce')
        df['UPC Code'] = df['UPC Code'].astype('Int64')

        # Filter out invalid UPC codes (0)
        invalid_upcs = (df['UPC Code'] == 0).sum()
        if invalid_upcs > 0:
            self.logger.warning(f"   Removing {invalid_upcs} rows with UPC Code = 0")
            df = df[df['UPC Code'] != 0]

        # Sort by Date and SKU
        df = df.sort_values(['Date', 'SKU']).reset_index(drop=True)

        self.logger.info(f"   ✅ Cleaned data: {len(df):,} rows remaining")

        return df

    def merge_sales_and_po(
        self,
        df_sales: pd.DataFrame,
        df_po: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge sales and PO data

        Args:
            df_sales: Sales DataFrame
            df_po: PO DataFrame

        Returns:
            Merged DataFrame
        """
        self.logger.info("🔗 Merging sales and PO data...")

        df = df_sales.copy()

        # Create YearMonth column for merging
        df['YearMonth'] = df['Date'].dt.to_period('M').dt.to_timestamp()

        # Merge with PO data (left join)
        df = df.merge(
            df_po,
            on=['SKU', 'YearMonth'],
            how='left'
        )

        # Fill missing PO quantities with 0
        df['PO_Quantity'] = df['PO_Quantity'].fillna(0)

        # Drop temporary YearMonth column
        df = df.drop(columns=['YearMonth'])

        self.logger.info(f"   ✅ Merged data: {len(df):,} rows")

        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create engineered features

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with additional features
        """
        self.logger.info("⚙️  Engineering features...")

        df = df.copy()

        # 1. Time-based features
        df['year'] = df['Date'].dt.year
        df['month'] = df['Date'].dt.month
        df['quarter'] = df['Date'].dt.quarter
        df['week_of_year'] = df['Date'].dt.isocalendar().week

        # 2. Lag features
        lag_periods = self.config['features']['lag_periods']

        for lag in lag_periods:
            df[f'sales_lag_{lag}'] = df.groupby('SKU')['Sales'].shift(lag)
            df[f'po_quantity_lag_{lag}'] = df.groupby('SKU')['PO_Quantity'].shift(lag)

        # 3. Rolling window features
        window = self.config['features']['rolling_window']

        df['sales_rolling_mean'] = (
            df.groupby('SKU')['Sales']
            .shift(1)
            .rolling(window=window)
            .mean()
            .reset_index(level=0, drop=True)
        )

        df['po_rolling_mean'] = (
            df.groupby('SKU')['PO_Quantity']
            .shift(1)
            .rolling(window=window)
            .mean()
            .reset_index(level=0, drop=True)
        )

        # 4. Categorical features (One-Hot Encoding)
        # Status
        if 'Status' in df.columns:
            status_dummies = pd.get_dummies(df['Status'], prefix='Status', drop_first=True)
            df = pd.concat([df, status_dummies], axis=1)

        # Brand Code
        if 'Brand Code' in df.columns:
            brand_dummies = pd.get_dummies(df['Brand Code'], prefix='Brand Code', drop_first=True)
            df = pd.concat([df, brand_dummies], axis=1)

        # Fill NaN values (from lag/rolling features) with 0
        df = df.fillna(0)

        self.logger.info(f"   ✅ Feature engineering complete: {len(df.columns)} columns")

        return df

    def save_processed_data(self, df: pd.DataFrame, filename: str = 'df_for_modeling.csv'):
        """
        Save processed data to CSV

        Args:
            df: Processed DataFrame
            filename: Output filename
        """
        output_path = self.data_processed / filename

        df.to_csv(output_path, index=False)

        self.logger.info(f"💾 Saved processed data to: {output_path}")
        self.logger.info(f"   Shape: {df.shape}")

    def run(self) -> pd.DataFrame:
        """
        Run the full data pipeline

        Returns:
            Processed DataFrame ready for modeling
        """
        self.logger.info("\n" + "=" * 60)
        self.logger.info("🔄 Starting Full Data Pipeline")
        self.logger.info("=" * 60)

        # Step 1: Load sales data
        df_sales = self.load_sales_data()

        # Step 2: Load PO data
        df_po = self.load_po_data()

        # Step 3: Clean sales data
        df_sales = self.clean_data(df_sales)

        # Step 4: Merge sales and PO
        df = self.merge_sales_and_po(df_sales, df_po)

        # Step 5: Engineer features
        df = self.engineer_features(df)

        # Step 6: Save processed data
        self.save_processed_data(df)

        self.logger.info("\n" + "=" * 60)
        self.logger.info("✅ Data Pipeline Complete!")
        self.logger.info("=" * 60)

        return df


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    pipeline = SalesDataPipeline()
    df_processed = pipeline.run()

    print("\n📊 Processed Data Summary:")
    print(f"   Shape: {df_processed.shape}")
    print(f"   Date Range: {df_processed['Date'].min()} ~ {df_processed['Date'].max()}")
    print(f"   Unique SKUs: {df_processed['SKU'].nunique()}")
    print(f"   Total Sales: {df_processed['Sales'].sum():,.0f}")
