"""
ABC Classification Module with Dynamic Re-classification

This module handles:
1. Monthly ABC classification based on recent sales
2. Category change detection
3. Historical tracking
4. Alerting for significant changes
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
from datetime import datetime

from utils import (
    load_config,
    resolve_path,
    setup_logging
)


class ABCClassifier:
    """Dynamic ABC Classification System"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ABC Classifier

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)

        # Setup paths
        self.data_processed = resolve_path(self.config['paths']['data_processed'])
        self.logs_dir = resolve_path(self.config['paths']['logs'])
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # ABC history file
        self.abc_history_file = self.logs_dir / 'abc_classification_history.csv'

    def classify(
        self,
        df: pd.DataFrame,
        lookback_months: int = 6,
        reference_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Classify SKUs into ABC categories

        Args:
            df: DataFrame with Sales data
            lookback_months: Number of recent months to consider
            reference_date: Date to calculate from (default: latest date)

        Returns:
            DataFrame with columns [SKU, avg_sales, ABC]
        """
        self.logger.info(f"🏷️  Classifying SKUs into ABC categories...")

        # Determine reference date
        if reference_date:
            ref_date = pd.to_datetime(reference_date)
        else:
            ref_date = df['Date'].max()

        # Calculate lookback start date
        lookback_start = ref_date - pd.DateOffset(months=lookback_months)

        # Filter recent data
        recent_df = df[
            (df['Date'] > lookback_start) & (df['Date'] <= ref_date)
        ].copy()

        if recent_df.empty:
            self.logger.warning(f"No data in lookback period: {lookback_start} ~ {ref_date}")
            return pd.DataFrame(columns=['SKU', 'avg_sales', 'ABC'])

        # Calculate SKU-level average sales
        sku_avg = recent_df.groupby('SKU')['Sales'].mean().reset_index()
        sku_avg.columns = ['SKU', 'avg_sales']

        # Sort by sales (descending)
        sku_avg = sku_avg.sort_values('avg_sales', ascending=False).reset_index(drop=True)

        # Calculate cumulative percentage
        total_sales = sku_avg['avg_sales'].sum()

        if total_sales == 0:
            self.logger.warning("Total sales is 0, all SKUs classified as C")
            sku_avg['ABC'] = 'C'
            return sku_avg

        sku_avg['cumulative_sales'] = sku_avg['avg_sales'].cumsum()
        sku_avg['cumulative_pct'] = sku_avg['cumulative_sales'] / total_sales

        # Apply thresholds from config
        thresholds = self.config['business']['abc_thresholds']

        sku_avg['ABC'] = 'C'
        sku_avg.loc[sku_avg['cumulative_pct'] <= thresholds['B'], 'ABC'] = 'B'
        sku_avg.loc[sku_avg['cumulative_pct'] <= thresholds['A'], 'ABC'] = 'A'

        # Drop temporary columns
        sku_avg = sku_avg.drop(columns=['cumulative_sales', 'cumulative_pct'])

        # Log statistics
        abc_counts = sku_avg['ABC'].value_counts()
        self.logger.info(f"   ✅ ABC Classification complete:")
        self.logger.info(f"      A-Items: {abc_counts.get('A', 0)} SKUs")
        self.logger.info(f"      B-Items: {abc_counts.get('B', 0)} SKUs")
        self.logger.info(f"      C-Items: {abc_counts.get('C', 0)} SKUs")

        return sku_avg

    def detect_category_changes(
        self,
        current_abc: pd.DataFrame,
        previous_abc: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Detect SKUs that changed ABC category

        Args:
            current_abc: Current ABC classification
            previous_abc: Previous ABC classification (if None, load from history)

        Returns:
            DataFrame with category changes
        """
        self.logger.info("🔍 Detecting category changes...")

        # Load previous classification if not provided
        if previous_abc is None:
            previous_abc = self._load_previous_classification()

        if previous_abc is None or previous_abc.empty:
            self.logger.info("   No previous classification found. Skipping change detection.")
            return pd.DataFrame(columns=[
                'SKU', 'previous_ABC', 'current_ABC', 'change_type',
                'previous_avg_sales', 'current_avg_sales', 'sales_change_pct'
            ])

        # Merge current and previous
        merged = current_abc.merge(
            previous_abc[['SKU', 'ABC', 'avg_sales']],
            on='SKU',
            how='outer',
            suffixes=('_current', '_previous')
        )

        # Fill NaN for new/removed SKUs
        merged['ABC_previous'] = merged['ABC_previous'].fillna('NEW')
        merged['ABC_current'] = merged['ABC_current'].fillna('REMOVED')

        # Detect changes
        changes = merged[merged['ABC_current'] != merged['ABC_previous']].copy()

        if changes.empty:
            self.logger.info("   ✅ No category changes detected")
            return changes

        # Classify change type
        def classify_change(row):
            prev, curr = row['ABC_previous'], row['ABC_current']

            if prev == 'NEW':
                return 'NEW_SKU'
            elif curr == 'REMOVED':
                return 'REMOVED_SKU'
            elif (prev == 'C' and curr == 'B') or (prev == 'B' and curr == 'A'):
                return 'UPGRADED'
            elif (prev == 'A' and curr == 'B') or (prev == 'B' and curr == 'C'):
                return 'DOWNGRADED'
            else:
                return 'OTHER'

        changes['change_type'] = changes.apply(classify_change, axis=1)

        # Calculate sales change percentage
        changes['sales_change_pct'] = (
            (changes['avg_sales_current'] - changes['avg_sales_previous']) /
            changes['avg_sales_previous'] * 100
        ).fillna(0)

        # Rename columns for clarity
        changes = changes.rename(columns={
            'ABC_previous': 'previous_ABC',
            'ABC_current': 'current_ABC',
            'avg_sales_previous': 'previous_avg_sales',
            'avg_sales_current': 'current_avg_sales'
        })

        # Log summary
        change_counts = changes['change_type'].value_counts()
        self.logger.info(f"   📊 Category changes detected:")
        for change_type, count in change_counts.items():
            self.logger.info(f"      {change_type}: {count}")

        return changes[[
            'SKU', 'previous_ABC', 'current_ABC', 'change_type',
            'previous_avg_sales', 'current_avg_sales', 'sales_change_pct'
        ]]

    def save_classification(
        self,
        abc_df: pd.DataFrame,
        classification_date: Optional[str] = None
    ):
        """
        Save ABC classification to history

        Args:
            abc_df: ABC classification DataFrame
            classification_date: Date of classification (default: today)
        """
        if classification_date is None:
            classification_date = datetime.now().strftime('%Y-%m-%d')

        # Add timestamp
        abc_with_date = abc_df.copy()
        abc_with_date['classification_date'] = classification_date

        # Append to history file
        if self.abc_history_file.exists():
            # Load existing history
            history = pd.read_csv(self.abc_history_file)

            # Remove old entries for the same date (if re-running)
            history = history[history['classification_date'] != classification_date]

            # Append new classification
            history = pd.concat([history, abc_with_date], ignore_index=True)
        else:
            history = abc_with_date

        # Save
        history.to_csv(self.abc_history_file, index=False)
        self.logger.info(f"💾 ABC classification saved to: {self.abc_history_file}")

    def _load_previous_classification(self) -> Optional[pd.DataFrame]:
        """Load the most recent ABC classification from history"""
        if not self.abc_history_file.exists():
            return None

        history = pd.read_csv(self.abc_history_file)

        if history.empty:
            return None

        # Get the most recent date
        latest_date = history['classification_date'].max()

        # Filter for that date
        latest = history[history['classification_date'] == latest_date]

        return latest[['SKU', 'ABC', 'avg_sales']]

    def generate_alert_report(
        self,
        changes: pd.DataFrame,
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate alert report for significant category changes

        Args:
            changes: Category changes DataFrame
            output_file: Optional file path to save report

        Returns:
            Alert report as string
        """
        if changes.empty:
            return "No category changes detected."

        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("🚨 ABC CATEGORY CHANGE ALERT")
        report_lines.append("=" * 70)
        report_lines.append("")

        # Upgrades (C→B, B→A)
        upgrades = changes[changes['change_type'] == 'UPGRADED']
        if not upgrades.empty:
            report_lines.append("📈 UPGRADES (Higher Sales Volume):")
            report_lines.append("-" * 70)
            for _, row in upgrades.iterrows():
                report_lines.append(
                    f"  {row['SKU']:12s} | {row['previous_ABC']} → {row['current_ABC']} | "
                    f"Sales: {row['previous_avg_sales']:.1f} → {row['current_avg_sales']:.1f} "
                    f"({row['sales_change_pct']:+.1f}%)"
                )
            report_lines.append("")

        # Downgrades (A→B, B→C)
        downgrades = changes[changes['change_type'] == 'DOWNGRADED']
        if not downgrades.empty:
            report_lines.append("📉 DOWNGRADES (Lower Sales Volume):")
            report_lines.append("-" * 70)
            for _, row in downgrades.iterrows():
                report_lines.append(
                    f"  {row['SKU']:12s} | {row['previous_ABC']} → {row['current_ABC']} | "
                    f"Sales: {row['previous_avg_sales']:.1f} → {row['current_avg_sales']:.1f} "
                    f"({row['sales_change_pct']:+.1f}%)"
                )
            report_lines.append("")

        # New SKUs
        new_skus = changes[changes['change_type'] == 'NEW_SKU']
        if not new_skus.empty:
            report_lines.append(f"🆕 NEW SKUs ({len(new_skus)}):")
            report_lines.append("-" * 70)
            for _, row in new_skus.head(10).iterrows():
                report_lines.append(
                    f"  {row['SKU']:12s} | Initial: {row['current_ABC']} | "
                    f"Avg Sales: {row['current_avg_sales']:.1f}"
                )
            if len(new_skus) > 10:
                report_lines.append(f"  ... and {len(new_skus) - 10} more")
            report_lines.append("")

        report_lines.append("=" * 70)

        report_text = "\n".join(report_lines)

        # Print to console
        print(report_text)

        # Save to file if specified
        if output_file:
            output_path = self.logs_dir / output_file
            with open(output_path, 'w') as f:
                f.write(report_text)
            self.logger.info(f"📄 Alert report saved to: {output_path}")

        return report_text


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    # Example usage
    classifier = ABCClassifier()

    # Load data
    df = pd.read_csv('data/processed/df_for_modeling.csv', parse_dates=['Date'])

    # Classify
    current_abc = classifier.classify(df, lookback_months=6)

    # Detect changes
    changes = classifier.detect_category_changes(current_abc)

    # Generate alert
    if not changes.empty:
        classifier.generate_alert_report(
            changes,
            output_file=f'abc_changes_{datetime.now().strftime("%Y%m%d")}.txt'
        )

    # Save classification
    classifier.save_classification(current_abc)

    print("\n📊 ABC Classification Summary:")
    print(current_abc.groupby('ABC').agg({
        'SKU': 'count',
        'avg_sales': ['mean', 'min', 'max']
    }))
