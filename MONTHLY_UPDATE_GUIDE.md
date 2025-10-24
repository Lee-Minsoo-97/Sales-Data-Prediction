# 월간 데이터 업데이트 가이드

## 📅 매월 수행할 작업

새로운 월간 Sales 및 PO 데이터를 받았을 때 수행하는 전체 프로세스입니다.

---

## 🔄 Step-by-Step 프로세스

### **Step 1: 새 데이터 업로드**

#### **1.1 Sales 데이터**
```bash
# 새 월간 Sales CSV를 data/raw_sales/ 에 업로드
# 파일명 형식: YYYY.MM_BBG.csv
# 예: 2025.09_BBG.csv

cp /path/to/2025.09_BBG.csv data/raw_sales/
```

#### **1.2 PO 데이터**
```bash
# 누적 PO 데이터를 data/raw_po/ 에 업로드
# 파일명: sps_data.csv (기존 파일 덮어쓰기)

cp /path/to/updated_sps_data.csv data/raw_po/sps_data.csv
```

**⚠️ 중요:**
- Sales 파일명은 정확히 `YYYY.MM_BBG.csv` 형식을 따라야 함
- PO 데이터는 누적 데이터 (과거 모든 PO 포함)

---

### **Step 2: 데이터 파이프라인 실행**

새 데이터를 통합하고 feature engineering 수행:

```bash
cd src
python data_pipeline.py
```

**출력:**
- `data/processed/df_for_modeling.csv` (업데이트됨)
- 로그: `logs/pipeline.log`

**확인사항:**
```python
# 빠른 검증
import pandas as pd

df = pd.read_csv('data/processed/df_for_modeling.csv', parse_dates=['Date'])
print(f"Date Range: {df['Date'].min()} ~ {df['Date'].max()}")
print(f"Total Records: {len(df):,}")
print(f"Latest Month Records: {len(df[df['Date'] == df['Date'].max()]):,}")
```

---

### **Step 3: ABC 재분류** ⭐ **중요!**

최근 6개월 실적 기반으로 ABC 재분류:

```bash
python abc_classifier.py
```

**출력:**
- `logs/abc_classification_history.csv` (이력 누적)
- `logs/abc_changes_YYYYMMDD.txt` (변경 알림)

**예시 출력:**
```
======================================================================
🚨 ABC CATEGORY CHANGE ALERT
======================================================================

📈 UPGRADES (Higher Sales Volume):
----------------------------------------------------------------------
  APB68270     | C → B | Sales: 12.5 → 38.2 (+205.6%)
  NRP47936     | B → A | Sales: 45.3 → 156.8 (+246.4%)

📉 DOWNGRADES (Lower Sales Volume):
----------------------------------------------------------------------
  DMX48237     | A → B | Sales: 320.1 → 38.5 (-87.9%)

🆕 NEW SKUs (3):
----------------------------------------------------------------------
  TWA60548     | Initial: C | Avg Sales: 2.3
  PNA09240     | Initial: B | Avg Sales: 28.7
```

**⚠️ 조치 필요:**
- **UPGRADE (C→B, B→A)**: 예측 전략 자동 조정됨 (걱정 없음)
- **DOWNGRADE (A→B, B→C)**: 이전 달에 수동으로 발주했다면, 이제 AUTO로 전환 가능
- **NEW SKU**: 초기 3개월은 이력 부족으로 예측 불가 (수동 발주 필요)

---

### **Step 4: 예측 생성** (다음 달 예측)

```bash
python prediction.py
```

또는 특정 날짜 예측:

```python
from prediction import SalesPredictor
from abc_classifier import ABCClassifier

# 1. ABC 분류 로드
classifier = ABCClassifier()
df = pd.read_csv('data/processed/df_for_modeling.csv', parse_dates=['Date'])
abc_df = classifier.classify(df, lookback_months=6)

# 2. 예측 생성
predictor = SalesPredictor()
historical_df = predictor.load_historical_data()

target_date = '2025-10-01'  # 예측할 달
features_df, metadata_df = predictor.prepare_features_for_prediction(
    historical_df,
    target_date
)

# 3. ABC 전략 적용 예측
predictions = predictor.predict_with_strategy(features_df, abc_df)

# 4. 저장
predictions.to_csv(f'predictions/predictions_{target_date[:7]}.csv', index=False)
```

**출력:**
- `predictions/predictions_YYYYMM.csv`

---

### **Step 5: 예측 결과 검토**

```csv
SKU,ABC_Category,Predicted_Sales,Order_Qty,Recommendation,Confidence
NRP48814,A,N/A,N/A,MANUAL,0.0
APB68274,A,N/A,N/A,MANUAL,0.0
HBF94449,B,32,64,AUTO,0.9
LFT68101,B,420,840,MANUAL_REVIEW,0.5
DMX48237,C,7,8,AUTO,0.7
```

**발주 프로세스:**
1. **AUTO**: 바로 발주 진행 (B, C Items)
2. **MANUAL_REVIEW**: 예측값 참고하여 담당자 검토 (이상 징후 감지됨)
3. **MANUAL**: 담당자가 직접 예측 및 발주 (A Items)

---

### **Step 6: 실제 판매량 피드백** (다음 달 초)

실제 판매량이 나오면 모델 성능 평가:

```python
from utils import log_model_performance
import pandas as pd
import numpy as np

# 예측값 로드
predictions = pd.read_csv('predictions/predictions_202509.csv')

# 실제값 로드 (최신 df_for_modeling.csv에서)
df = pd.read_csv('data/processed/df_for_modeling.csv', parse_dates=['Date'])
actuals = df[df['Date'] == '2025-09-01'][['SKU', 'Sales']]

# 병합
merged = predictions.merge(actuals, on='SKU', how='inner')

# 성능 평가 (AUTO items만)
auto_items = merged[merged['Recommendation'] == 'AUTO']

if not auto_items.empty:
    log_model_performance(
        date='2025-09-01',
        model_version='ensemble_v2.1_bc_only',
        y_true=auto_items['Sales'].values,
        y_pred=auto_items['Predicted_Sales'].values
    )

print(f"AUTO Items Performance:")
print(f"  MAE: {np.mean(np.abs(auto_items['Sales'] - auto_items['Predicted_Sales'])):.2f}")
print(f"  Count: {len(auto_items)}")
```

**출력:**
- `logs/performance_tracking.csv` (누적)

---

## 📊 정기 모니터링 (분기별)

### **분기마다 확인할 지표:**

```python
import pandas as pd

# 성능 이력 로드
perf = pd.read_csv('logs/performance_tracking.csv')

# 최근 3개월 성능
recent = perf.tail(3)
print(recent[['date', 'mae', 'mape', 'bias']])

# Drift 확인
mae_trend = recent['mae'].diff().mean()
if mae_trend > 5:
    print("⚠️ WARNING: MAE is increasing. Consider retraining.")
```

### **재학습 필요 신호:**
- MAE가 3개월 연속 상승
- Bias가 ±50 초과
- 새로운 A-Item이 5개 이상 생김

---

## 🔧 트러블슈팅

### **문제 1: 새 Sales 파일이 컬럼 형식이 다름**

**증상:**
```
KeyError: 'Sales'
```

**해결:**
```python
# data_pipeline.py가 자동으로 처리하지만, 수동 확인:
import pandas as pd

df = pd.read_csv('data/raw_sales/2025.09_BBG.csv')
print(df.columns.tolist())

# Status 컬럼: *_Status로 끝나야 함
# Sales 컬럼: 마지막 컬럼이어야 함
```

### **문제 2: ABC 재분류 후 이전 예측과 차이**

**정상입니다!**
- ABC는 매월 변경될 수 있음
- 예측 전략도 그에 따라 자동 조정

### **문제 3: 새 SKU가 예측 안 됨**

**정상입니다!**
- 최소 3개월 이력 필요
- `#N/A` 또는 `MANUAL` 권장으로 표시됨
- 3개월 후 자동으로 예측 가능

---

## 📝 체크리스트

### **매월 필수 작업:**
- [ ] 새 Sales CSV 업로드 (`YYYY.MM_BBG.csv`)
- [ ] 누적 PO 데이터 업로드 (`sps_data.csv`)
- [ ] Data Pipeline 실행 (`python data_pipeline.py`)
- [ ] ABC 재분류 (`python abc_classifier.py`)
- [ ] ABC 변경 알림 검토 (`logs/abc_changes_*.txt`)
- [ ] 예측 생성 (`python prediction.py`)
- [ ] 예측 결과 배포 (담당자에게 CSV 전달)

### **다음 달 초 작업:**
- [ ] 실제 판매량 피드백 (성능 평가)
- [ ] 성능 로그 확인 (`logs/performance_tracking.csv`)

### **분기별 작업:**
- [ ] 성능 트렌드 분석
- [ ] 재학습 필요성 검토
- [ ] A-Items 리스트 업데이트

---

## 🚀 자동화 (선택사항)

### **Cron Job 설정 (Linux/Mac)**

```bash
# 매월 1일 오전 9시에 자동 실행
0 9 1 * * cd /path/to/Sales-Data-Prediction/src && python abc_classifier.py
```

### **Windows Task Scheduler**

1. 작업 스케줄러 열기
2. "기본 작업 만들기"
3. 트리거: 매월
4. 작업: Python 스크립트 실행
5. 프로그램: `python`
6. 인수: `C:\path\to\Sales-Data-Prediction\src\abc_classifier.py`

---

## 📞 문제 발생 시

1. **로그 확인**: `logs/pipeline.log`
2. **데이터 검증**: Step 2의 검증 코드 실행
3. **ABC 이력 확인**: `logs/abc_classification_history.csv`
4. **이슈 보고**: GitHub Issues 또는 담당자 연락

---

**Last Updated**: 2025-10-24
