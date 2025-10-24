# Gemini 코드 분석 및 개선점

## 📋 Gemini 코드 분석 요약

### ✅ **잘된 점 (Strengths)**

1. **체계적인 Feature Engineering**
   - Lag features (1, 2, 3개월)
   - Rolling window features (3개월 평균)
   - 시간 기반 features (year, month, quarter, week)
   - One-hot encoding for categorical variables

2. **적절한 모델 선택**
   - LightGBM과 XGBoost - tabular data에 최적
   - Ensemble approach로 안정성 확보

3. **견고한 검증 방법**
   - Time Series Cross-Validation (5-fold)
   - Optuna를 통한 hyperparameter tuning
   - Early stopping으로 overfitting 방지

4. **비즈니스 분석**
   - Fill Rate, Stockout, Overstock 계산
   - ABC 분석
   - Brand-level 성능 평가

---

## 🔧 **개선 필요 사항 (Improvements Needed)**

### 1. **코드 구조 (Code Structure)**

**문제점:**
- 모든 코드가 Jupyter 노트북에 흩어져 있음
- 코드 중복 (데이터 로딩, 전처리 등이 여러 노트북에 반복)
- 함수화되지 않은 procedural code

**개선안:**
```
src/
├── data_pipeline.py       # 데이터 로딩, 통합, feature engineering
├── model_training.py      # 모델 학습 및 튜닝
├── prediction.py          # 예측 생성
├── evaluation.py          # 모델 평가 및 분석
└── utils.py              # 공통 유틸리티 함수
```

### 2. **하드코딩된 경로 (Hardcoded Paths)**

**문제점:**
```python
file_path = '/content/drive/MyDrive/Colab Notebooks/Data for Modeling/df_for_modeling.csv'
```
- Google Colab 전용 경로
- 다른 환경에서 실행 불가

**개선안:**
```python
# config.py
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
MODEL_DIR = PROJECT_ROOT / 'models' / 'trained'
```

### 3. **에러 처리 부족 (Error Handling)**

**문제점:**
- 파일이 없을 때 처리 로직 없음
- 데이터 검증 부족
- Silent failures

**개선안:**
```python
def load_sales_data(folder_path):
    """Load and validate sales data"""
    if not folder_path.exists():
        raise FileNotFoundError(f"Sales data folder not found: {folder_path}")

    files = list(folder_path.glob('*_BBG.csv'))
    if not files:
        raise ValueError(f"No sales CSV files found in {folder_path}")

    # ... validation logic
    return df
```

### 4. **데이터 검증 로직 부재 (Data Validation)**

**문제점:**
- 컬럼명 변경 여부 확인 안 함
- 데이터 타입 검증 부족
- 누락 데이터 처리 미흡

**개선안:**
```python
def validate_dataframe(df, expected_columns, date_column='Date'):
    """Validate DataFrame structure and content"""
    # Check required columns
    missing_cols = set(expected_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")

    # Check date range
    if df[date_column].isna().any():
        raise ValueError("Found null dates")

    # Check for duplicates
    dupes = df.duplicated(subset=['SKU', date_column]).sum()
    if dupes > 0:
        logger.warning(f"Found {dupes} duplicate SKU-Date pairs")

    return True
```

### 5. **로깅 부족 (Logging)**

**문제점:**
- print() 문만 사용
- 실행 기록이 남지 않음
- 디버깅 어려움

**개선안:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

### 6. **설정 관리 (Configuration Management)**

**문제점:**
- 매직 넘버가 코드 곳곳에 산재
  - `n_splits=5`
  - `test_start_date = '2025-07-01'`
  - `lag_periods = [1, 2, 3]`

**개선안:**
```python
# config.yaml
data:
  test_start_date: "2025-07-01"
  val_start_date: "2025-06-01"

features:
  lag_periods: [1, 2, 3]
  rolling_window: 3

model:
  n_trials: 100
  cv_splits: 5
  early_stopping_rounds: 50

ensemble:
  lgbm_weight: 0.485
  xgb_weight: 0.515
```

### 7. **재현성 (Reproducibility)**

**문제점:**
- Random seed가 일부만 설정됨
- 학습 환경 정보 저장 안 됨

**개선안:**
```python
def set_seed(seed=42):
    """Set random seed for reproducibility"""
    np.random.seed(seed)
    import random
    random.seed(seed)

    # For sklearn
    import os
    os.environ['PYTHONHASHSEED'] = str(seed)

    # For LightGBM/XGBoost
    # Already handled in model params
```

### 8. **성능 모니터링 (Performance Monitoring)**

**문제점:**
- 모델 성능이 시간에 따라 어떻게 변하는지 추적 안 됨
- 실제 운영 시 drift detection 없음

**개선안:**
```python
# logs/performance_tracking.csv 자동 생성
def log_model_performance(date, predictions, actuals, model_version):
    """Log model performance metrics"""
    metrics = {
        'date': date,
        'model_version': model_version,
        'mae': mean_absolute_error(actuals, predictions),
        'rmse': np.sqrt(mean_squared_error(actuals, predictions)),
        'mape': mean_absolute_percentage_error(actuals, predictions),
        'bias': np.mean(predictions - actuals)
    }

    # Append to CSV
    pd.DataFrame([metrics]).to_csv(
        'logs/performance_tracking.csv',
        mode='a',
        header=not os.path.exists('logs/performance_tracking.csv'),
        index=False
    )
```

### 9. **Feature 이름 불일치 (Feature Name Mismatch)**

**문제점 (코드에서 발견):**
```python
# LightGBM은 공백을 '_'로 변환
# XGBoost는 공백을 그대로 유지
# -> 예측 시 KeyError 발생 가능
```

**개선안:**
```python
def standardize_column_names(df):
    """Standardize column names across models"""
    df.columns = df.columns.str.replace(' ', '_')
    df.columns = df.columns.str.lower()
    return df
```

### 10. **Prediction App의 사용성 (User Experience)**

**문제점:**
- 입력 형식이 엄격함
- 에러 메시지가 명확하지 않음
- '#N/A' 처리가 수동

**개선안:**
```python
def predict_with_validation(sku_list, target_date):
    """
    User-friendly prediction function with validation

    Args:
        sku_list: List of SKUs or DataFrame
        target_date: String 'YYYY-MM-DD' or datetime

    Returns:
        DataFrame with predictions and confidence flags
    """
    # Auto-detect input type
    # Validate SKU existence
    # Auto-fill missing history with warnings
    # Return confidence scores
```

---

## 🚀 **Migration 계획**

### Phase 1: 코드 리팩토링 ✅
1. ✅ 프로젝트 구조 생성
2. ✅ requirements.txt, .gitignore 생성
3. ⏳ `src/` 모듈로 코드 분리
4. ⏳ Config 파일 생성 (YAML)

### Phase 2: 핵심 기능 구현 ⏳
1. ⏳ Data Pipeline (01_data_pipeline.py)
2. ⏳ Model Training (02_model_training.py)
3. ⏳ Prediction App (03_prediction_app.py)

### Phase 3: 개선 기능 추가 📝
1. 📝 Logging 시스템
2. 📝 Data Validation
3. 📝 Performance Monitoring
4. 📝 Error Handling

### Phase 4: 문서화 & 테스트 📝
1. 📝 README.md 작성
2. 📝 API Documentation
3. 📝 Unit Tests
4. 📝 사용자 가이드

---

## 📊 **예상 개선 효과**

| 항목 | 기존 (Gemini Colab) | 개선 후 (Claude Code) |
|------|---------------------|----------------------|
| **실행 환경** | Google Colab 전용 | 로컬/서버 어디서나 |
| **재사용성** | 낮음 (노트북 복사) | 높음 (모듈화) |
| **유지보수** | 어려움 (코드 중복) | 쉬움 (단일 소스) |
| **에러 추적** | 어려움 (print만) | 쉬움 (logging) |
| **확장성** | 제한적 | 우수 |
| **협업** | 어려움 | 용이 (Git) |

---

## 🎯 **다음 단계**

1. **즉시 시작:** `src/` 폴더에 Python 스크립트 작성
2. **우선순위 1:** Data Pipeline (가장 기반이 되는 부분)
3. **우선순위 2:** Prediction App (사용자가 가장 많이 사용)
4. **우선순위 3:** Model Training (재학습 빈도 낮음)
