# 모델 재학습 가이드

## 🎯 목적

새로운 판매 데이터가 축적되면 모델을 재학습하여 예측 성능을 최신 상태로 유지합니다.

---

## 📋 재학습 시기

### **권장 주기:**
- **분기마다 (3개월)**: 정기 재학습
- **성능 저하 시**: MAE가 3개월 연속 상승하거나 Bias > ±50
- **데이터 패턴 변화**: 신규 A-Item 5개 이상, ABC 대폭 재편

---

## 🚀 사용 방법

### **1. 최신 데이터 준비**

재학습 전에 반드시 최신 데이터로 파이프라인을 실행하세요:

```bash
cd src
python data_pipeline.py
```

### **2. 재학습 실행**

```bash
python retrain_model.py
```

**확인 메시지:**
```
iHerb Sales Prediction - Model Retraining
======================================================================

This will:
  1. Retrain LightGBM and XGBoost with latest data
  2. Backup current models
  3. Replace models with new versions
  4. Provide performance comparison

Proceed with retraining? (yes/no): yes
```

**`yes` 입력 후 재학습 시작 (5~10분 소요)**

---

## 📊 출력 해석

### **성능 비교 예시:**

```
======================================================================
📈 PERFORMANCE COMPARISON
======================================================================

Model                    Old MAE      New MAE  Improvement
----------------------------------------------------------------------
LightGBM                   40.81        33.21        7.60
XGBoost                    35.79        30.12        5.67
----------------------------------------------------------------------

Ensemble Weights:
  Old: LightGBM 0.485, XGBoost 0.515
  New: LightGBM 0.476, XGBoost 0.524
```

**해석:**
- **Improvement > 0**: 새 모델이 더 좋음 ✅
- **Improvement < 0**: 새 모델이 더 나쁨 ⚠️ (원인 분석 필요)
- **MAE 차이 < 3**: 큰 차이 없음 (재학습 불필요했을 수도)

---

## 📝 재학습 후 작업

### **Step 1: config.yaml 업데이트**

재학습 출력에 나온 새로운 가중치를 `config.yaml`에 반영:

```yaml
# config.yaml
ensemble:
  weights:
    lightgbm: 0.476  # 스크립트 출력에서 복사
    xgboost: 0.524   # 스크립트 출력에서 복사
```

### **Step 2: 새 모델 테스트**

```bash
# 다음 달 예측 생성
python generate_forecast.py --auto
```

**Excel 파일 확인:**
- 예측값이 합리적인지 검토
- 이전 예측과 비교 (큰 차이 확인)
- 몇 개 SKU 샘플 검증

### **Step 3: 배포 (선택)**

테스트 후 문제없으면 Git 커밋:

```bash
git add models/trained/*.pkl config.yaml
git commit -m "Retrain models with data up to 2025-08"
git push
```

---

## 💾 백업 및 롤백

### **자동 백업:**

재학습 스크립트는 자동으로 이전 모델을 백업합니다:

```
models/trained/
├── lgbm_model_v1.2.pkl                      ← 현재 모델 (재학습 후 새 버전)
├── xgb_model_v2_0.pkl                       ← 현재 모델 (재학습 후 새 버전)
├── lgbm_model_v1.2_backup_20251027.pkl      ← 백업 (이전 버전)
├── xgb_model_v2_0_backup_20251027.pkl       ← 백업 (이전 버전)
├── lgbm_model_retrained_20251027.pkl        ← 타임스탬프 버전
└── xgb_model_retrained_20251027.pkl         ← 타임스탬프 버전
```

### **롤백 방법:**

문제 발생 시 이전 모델로 복구:

```bash
cd models/trained

# 백업 파일 확인
ls -lh *backup*

# 최신 백업으로 복구
cp lgbm_model_v1.2_backup_20251027.pkl lgbm_model_v1.2.pkl
cp xgb_model_v2_0_backup_20251027.pkl xgb_model_v2_0.pkl
```

`config.yaml`도 이전 가중치로 되돌려야 합니다.

---

## ⚠️ 주의사항

### **1. 데이터 검증**

재학습 전에 반드시 확인:
- 최신 Sales, PO 데이터가 업로드되었는가?
- `df_for_modeling.csv`에 새 데이터가 반영되었는가?

```python
import pandas as pd
df = pd.read_csv('data/processed/df_for_modeling.csv', parse_dates=['Date'])
print(f"최신 날짜: {df['Date'].max()}")
print(f"총 레코드: {len(df):,}")
```

### **2. 성능 저하 시**

새 모델 MAE가 이전보다 나쁘면:
- 데이터 품질 확인 (누락, 이상치)
- 최근 월 데이터 검증
- 롤백 고려

### **3. 점진적 배포**

재학습 후 바로 전체 배포하지 말고:
- 1~2주 테스트 기간
- 소수 SKU부터 적용
- 실제 성능 모니터링 후 확대

---

## 🔍 트러블슈팅

### **문제: "Processed data not found"**

```
FileNotFoundError: Processed data not found: data/processed/df_for_modeling.csv
Please run data_pipeline.py first!
```

**해결:**
```bash
cd src
python data_pipeline.py
```

---

### **문제: 메모리 부족**

```
MemoryError: Unable to allocate array
```

**해결:**
- 더 큰 메모리 환경에서 실행
- 또는 `test_months` 파라미터 조정 (코드 수정 필요)

---

### **문제: Feature mismatch**

```
ValueError: feature_names mismatch
```

**해결:**
- 이전 모델과 새 데이터의 Feature가 다름
- `data_pipeline.py`에서 Feature 생성 로직 확인
- 동일한 Feature를 생성하는지 검증

---

## 📞 도움말

**자세한 내용:**
- `MONTHLY_UPDATE_GUIDE.md` - 월간 업데이트 전체 프로세스
- `logs/pipeline.log` - 재학습 로그

**문제 발생 시:**
1. 로그 파일 확인
2. 백업 모델로 롤백
3. GitHub Issues 또는 담당자 문의

---

**Last Updated:** 2025-10-27
