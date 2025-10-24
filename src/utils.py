"""
Utility functions for the iHerb Sales Prediction System
"""

import os
import yaml
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler


# ============================================================================
# Project Paths
# ============================================================================

def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config file. If None, uses default config.yaml

    Returns:
        Dictionary containing configuration
    """
    if config_path is None:
        config_path = get_project_root() / "config.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def resolve_path(relative_path: str, config: Optional[Dict] = None) -> Path:
    """
    Resolve relative path to absolute path

    Args:
        relative_path: Relative path from project root
        config: Configuration dictionary (optional)

    Returns:
        Absolute Path object
    """
    return get_project_root() / relative_path


# ============================================================================
# Logging
# ============================================================================

def setup_logging(config: Optional[Dict] = None) -> logging.Logger:
    """
    Setup logging configuration

    Args:
        config: Configuration dictionary

    Returns:
        Configured logger instance
    """
    if config is None:
        config = load_config()

    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get(
        'format',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log_file = log_config.get('file', 'logs/pipeline.log')
    max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
    backup_count = log_config.get('backup_count', 5)

    # Create logs directory if it doesn't exist
    log_path = resolve_path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger('iherb_sales')
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# Data Validation
# ============================================================================

def validate_dataframe(
    df: pd.DataFrame,
    required_columns: list,
    date_column: str = 'Date',
    sku_column: str = 'SKU',
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Validate DataFrame structure and content

    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        date_column: Name of date column
        sku_column: Name of SKU column
        logger: Logger instance

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if logger is None:
        logger = logging.getLogger('iherb_sales')

    # Check if DataFrame is empty
    if df.empty:
        raise ValueError("DataFrame is empty")

    # Check required columns
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Check date column
    if date_column in df.columns:
        # Check for null dates
        null_dates = df[date_column].isna().sum()
        if null_dates > 0:
            raise ValueError(f"Found {null_dates} null dates")

        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            logger.warning(f"Converting {date_column} to datetime")
            df[date_column] = pd.to_datetime(df[date_column])

    # Check for duplicates
    if sku_column in df.columns and date_column in df.columns:
        dupes = df.duplicated(subset=[sku_column, date_column]).sum()
        if dupes > 0:
            logger.warning(f"Found {dupes} duplicate SKU-Date pairs")

    logger.info(f"✅ DataFrame validation passed: {df.shape}")
    return True


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names (replace spaces with underscores, lowercase)

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with standardized column names
    """
    df = df.copy()
    df.columns = df.columns.str.replace(' ', '_')
    # Note: We keep original case for readability in this project
    return df


# ============================================================================
# Random Seed
# ============================================================================

def set_random_seed(seed: int = 42):
    """
    Set random seed for reproducibility

    Args:
        seed: Random seed value
    """
    np.random.seed(seed)
    import random
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)


# ============================================================================
# Metrics
# ============================================================================

def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate evaluation metrics

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        Dictionary of metrics
    """
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    # Handle potential division by zero
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else 0

    metrics = {
        'mae': mean_absolute_error(y_true, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
        'mape': mape,
        'bias': np.mean(y_pred - y_true),
        'r2': np.corrcoef(y_true, y_pred)[0, 1] ** 2 if len(y_true) > 1 else 0
    }

    return metrics


def log_model_performance(
    date: str,
    model_version: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    config: Optional[Dict] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Log model performance to CSV file

    Args:
        date: Date of prediction
        model_version: Model version string
        y_true: True values
        y_pred: Predicted values
        config: Configuration dictionary
        logger: Logger instance
    """
    if config is None:
        config = load_config()
    if logger is None:
        logger = logging.getLogger('iherb_sales')

    # Calculate metrics
    metrics = calculate_metrics(y_true, y_pred)

    # Add metadata
    metrics['date'] = date
    metrics['model_version'] = model_version
    metrics['n_predictions'] = len(y_true)

    # Get log file path
    log_file = config.get('monitoring', {}).get(
        'performance_log',
        'logs/performance_tracking.csv'
    )
    log_path = resolve_path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Append to CSV
    pd.DataFrame([metrics]).to_csv(
        log_path,
        mode='a',
        header=not log_path.exists(),
        index=False
    )

    logger.info(f"📊 Performance logged: MAE={metrics['mae']:.2f}, MAPE={metrics['mape']:.2f}%")


# ============================================================================
# File Operations
# ============================================================================

def ensure_dir(directory: Path):
    """Ensure directory exists, create if not"""
    directory.mkdir(parents=True, exist_ok=True)


def list_files(directory: Path, pattern: str = "*") -> list:
    """
    List files in directory matching pattern

    Args:
        directory: Directory to search
        pattern: Glob pattern

    Returns:
        List of file paths
    """
    return sorted(directory.glob(pattern))
