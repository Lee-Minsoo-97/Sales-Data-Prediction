# iHerb Sales Forecasting System 🚀

AI 기반 월간 SKU 판매량 예측 시스템

> **쉽고 빠른 Setup 가이드** - 처음 사용자도 10분 안에 시작할 수 있습니다!

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📋 목차

1. [시스템 개요](#-시스템-개요)
2. [빠른 시작 (5분)](#-빠른-시작-5분)
3. [상세 설치 가이드](#-상세-설치-가이드)
4. [사용 방법](#-사용-방법)
5. [월간 업데이트](#-월간-업데이트)
6. [주요 기능](#-주요-기능)
7. [프로젝트 구조](#-프로젝트-구조)
8. [문서](#-문서)
9. [성능](#-성능)
10. [트러블슈팅](#-트러블슈팅)

---

## 🎯 시스템 개요

**무엇을 하나요?**

iHerb의 제품 판매량을 AI로 예측하여 최적의 발주량을 제시합니다.

**주요 특징:**
- 📊 **AI 예측**: LightGBM + XGBoost 앙상블 모델
- 🎨 **3가지 인터페이스**: CLI, Web UI, Excel 다운로드
- 🔄 **ABC 분류**: 자동으로 제품을 중요도별로 분류
- ⚡ **자동화**: B+C 제품은 AI가 자동 예측, A 제품만 수동 관리
- 📈 **성능**: MAE 38.00, Fill Rate 89.19%

**비즈니스 가치:**
- ⏱️ 시간 절약: 월 67.6시간 → 76% 업무 시간 단축
- 💰 재고 최적화: Stockout과 Overstock 감소
- 🎯 집중 가능: 중요한 A-Items에 집중

---

## ⚡ 빠른 시작 (5분)

### **Step 1: 프로젝트 다운로드**

```bash
# Git Clone
git clone https://github.com/Lee-Minsoo-97/Sales-Data-Prediction.git
cd Sales-Data-Prediction
```

### **Step 2: 의존성 설치**

```bash
# Python 패키지 설치
pip install -r requirements.txt
```

**설치 확인:**
```bash
python -c "import pandas, lightgbm, xgboost, streamlit; print('✅ 설치 완료!')"
```

### **Step 3: 첫 예측 생성**

```bash
# CLI로 다음 달 예측
python generate_forecast.py --auto
```

**출력:**
- `predictions/forecast_YYYYMM.xlsx` - Excel 파일 생성됨!

**또는 Web UI 사용:**
```bash
# Web 브라우저에서 실행
streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8501` 열기 → 날짜 선택 → "예측 생성" 클릭!

---

## 📦 상세 설치 가이드

### **시스템 요구사항**

| 항목 | 요구사항 | 권장사항 |
|------|----------|----------|
| **운영체제** | Windows 10+, macOS 10.14+, Linux | 어떤 OS든 OK |
| **Python** | 3.8 이상 | 3.10 권장 |
| **RAM** | 최소 4GB | 8GB 이상 |
| **디스크** | 500MB 이상 | 1GB 이상 |
| **인터넷** | 초기 설치 시만 필요 | - |

### **설치 방법**

#### **방법 1: Git Clone (권장)**

```bash
# 1. 저장소 클론
git clone https://github.com/Lee-Minsoo-97/Sales-Data-Prediction.git
cd Sales-Data-Prediction

# 2. 가상환경 생성 (선택사항이지만 권장)
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 설치 확인
python -c "import pandas, lightgbm, xgboost; print('✅ 모든 패키지 설치 완료!')"
```

#### **방법 2: ZIP 다운로드**

1. GitHub에서 "Code" → "Download ZIP" 클릭
2. 압축 해제
3. 터미널에서 해당 폴더로 이동
4. `pip install -r requirements.txt` 실행

### **의존성 목록**

주요 라이브러리:

```
pandas>=2.0.0          # 데이터 처리
numpy>=1.24.0          # 수치 연산
scikit-learn>=1.3.0    # ML 도구
lightgbm>=4.0.0        # 예측 모델 1
xgboost>=2.0.0         # 예측 모델 2
streamlit>=1.28.0      # Web UI
openpyxl>=3.1.0        # Excel 출력
plotly>=5.17.0         # 차트
joblib>=1.3.0          # 모델 로딩
pyyaml>=6.0.0          # 설정 파일
```

### **초기 데이터 확인**

설치 후 데이터가 제대로 있는지 확인:

```bash
# 데이터 파일 확인
ls data/raw_sales/*.csv    # 월간 판매 데이터 (16개 파일 예상)
ls data/raw_po/*.csv        # PO 데이터 (1개 파일 예상)
ls models/trained/*.pkl     # 학습된 모델 (2개 파일 예상)
```

**예상 출력:**
```
data/raw_sales/2024.05_BBG.csv
data/raw_sales/2024.06_BBG.csv
...
data/raw_sales/2025.08_BBG.csv

data/raw_po/sps_data.csv

models/trained/lgbm_model_v1.2.pkl
models/trained/xgb_model_v2_0.pkl
```

---

## 🚀 사용 방법

### **방법 1: CLI (커맨드라인) - 가장 빠름**

#### **자동 모드 (다음 달 예측):**

```bash
python generate_forecast.py --auto
```

#### **인터랙티브 모드 (날짜 선택):**

```bash
python generate_forecast.py
```

대화형으로 날짜 입력:
```
예측 대상 월을 입력하세요 (YYYY-MM-DD 형식, 예: 2025-09-01):
기본값 [2025-11-01]: 2025-12-01  ← 원하는 날짜 입력
```

#### **특정 날짜 직접 지정:**

```bash
python generate_forecast.py --target-date 2025-12-01 --output forecast_dec.xlsx
```

### **방법 2: Web UI (가장 쉬움)**

#### **Web 앱 실행:**

```bash
streamlit run streamlit_app.py
```

브라우저가 자동으로 열립니다 (또는 `http://localhost:8501` 접속)

#### **사용 방법:**

1. 📅 **날짜 선택**: 사이드바에서 예측할 월 선택
2. 🔘 **예측 생성 버튼** 클릭
3. ⏳ **진행 상황** 확인 (3단계)
   - Step 1: ABC 분류
   - Step 2: AI 예측 생성
   - Step 3: Excel 파일 생성
4. 📊 **결과 확인**:
   - 요약 통계 (카드)
   - 차트 (원형, 막대)
   - 데이터 미리보기 (탭)
5. 📥 **Excel 다운로드** 버튼 클릭

### **방법 3: Python 스크립트 (프로그래밍)**

```python
from src.prediction import SalesPredictor
from src.abc_classifier import ABCClassifier
from src.excel_exporter import export_predictions_to_excel
import pandas as pd

# 1. 데이터 로드
predictor = SalesPredictor()
historical_df = predictor.load_historical_data()

# 2. ABC 분류
classifier = ABCClassifier()
abc_df = classifier.classify(historical_df, lookback_months=6)

# 3. 예측 Feature 준비
target_date = '2025-12-01'
features_df, metadata_df = predictor.prepare_features_for_prediction(
    historical_df, target_date
)

# 4. ABC 전략 적용 예측
predictions_df = predictor.predict_with_strategy(features_df, abc_df)

# 5. Excel 출력
output_path = export_predictions_to_excel(
    predictions_df,
    output_file='my_forecast.xlsx',
    target_date=target_date
)

print(f"✅ 예측 완료: {output_path}")
```

### **Excel 출력 파일 구조**

생성된 Excel 파일은 **5개 시트**로 구성:

| 시트 이름 | 색상 | 내용 | 사용법 |
|-----------|------|------|--------|
| **요약_Summary** | - | 전체 통계 및 사용 설명 | 먼저 읽기 |
| **AUTO_자동발주** | 🟢 녹색 | B+C 제품 자동 예측 | 바로 발주 진행 |
| **REVIEW_검토필요** | 🟡 노랑 | 이상 징후 감지된 제품 | 예측값 참고하여 검토 |
| **MANUAL_수동발주** | 🔴 빨강 | A-Items (고가치 제품) | 수동으로 예측 및 발주 |
| **ALL_전체데이터** | - | 모든 SKU 통합 데이터 | 분석 및 참고용 |

**Excel 파일 열 설명:**
- **SKU**: 제품 코드
- **ABC_Category**: A/B/C 분류
- **평균판매량_6개월**: 최근 6개월 평균
- **AI예측판매량**: AI가 예측한 다음 달 판매량
- **권장발주량**: 2배 안전재고 포함 (C-Items는 1.2배)
- **권장사항**: AUTO / MANUAL_REVIEW / MANUAL
- **신뢰도**: 0~1 (높을수록 신뢰)
- **이상징후점수**: 0~1 (높을수록 주의 필요)

---

## 📅 월간 업데이트

매월 새로운 판매 데이터가 나오면 다음 절차를 따르세요:

### **Step 1: 새 데이터 업로드**

```bash
# 1. 새 월간 판매 데이터 업로드
cp /path/to/2025.09_BBG.csv data/raw_sales/

# 2. 최신 PO 데이터 업로드 (누적 데이터)
cp /path/to/updated_sps_data.csv data/raw_po/sps_data.csv
```

### **Step 2: 데이터 파이프라인 실행**

```bash
cd src
python data_pipeline.py
```

이 명령은:
- 새 데이터 통합
- Feature 생성
- `data/processed/df_for_modeling.csv` 업데이트

### **Step 3: ABC 재분류**

```bash
python abc_classifier.py
```

최근 6개월 판매 실적 기반으로 ABC 재분류 (C→B, B→A 변화 감지)

### **Step 4: 다음 달 예측 생성**

```bash
python ../generate_forecast.py --auto
```

또는 Streamlit:
```bash
streamlit run ../streamlit_app.py
```

**전체 과정 소요 시간:** 약 2~3분

**자세한 가이드:** [MONTHLY_UPDATE_GUIDE.md](MONTHLY_UPDATE_GUIDE.md)

---

## 🔄 모델 재학습 (분기별)

3개월마다 또는 성능 저하 시 모델을 재학습하세요:

```bash
cd src
python retrain_model.py
```

**재학습 프로세스:**
1. 최신 데이터로 LightGBM, XGBoost 재학습
2. 이전 모델 자동 백업
3. 성능 비교 (Old vs New MAE)
4. 새 모델로 교체
5. Ensemble 가중치 업데이트

**출력 예시:**
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

재학습 후 `config.yaml`의 ensemble weights를 출력값으로 업데이트하세요.

**자세한 가이드:** [RETRAIN_GUIDE.md](RETRAIN_GUIDE.md)

---

## ⭐ 주요 기능

### **1. 자동 ABC 분류**

제품을 판매량 기준으로 자동 분류:
- **A-Items** (21%): 매출의 80% 차지 → 수동 발주
- **B-Items** (27%): 매출의 15% 차지 → 자동 예측
- **C-Items** (52%): 매출의 5% 차지 → 자동 예측

**매월 자동 재분류**되어 제품 이동 추적 (C→B, B→A)

### **2. ABC 전략 기반 예측**

| 카테고리 | 전략 | 신뢰도 | 발주량 계산 |
|----------|------|--------|------------|
| **A-Items** | MANUAL | 0.0 | 담당자가 직접 결정 |
| **B-Items** | AUTO | 0.9 | 예측값 × 2.0 |
| **C-Items** | AUTO | 0.7 | 예측값 × 1.2 (보수적) |
| **이상 징후** | MANUAL_REVIEW | 0.5 | 검토 후 결정 |

### **3. 이상 징후 감지**

AI가 자동으로 이상 패턴을 감지:
- 🔺 **PO 급증**: 평소보다 3배 이상 발주
- 📊 **판매 변동**: 50% 이상 급변
- 🏷️ **프로모션**: On Sale 상태

이상 점수 > 0.7 이면 MANUAL_REVIEW 권장

### **4. 3가지 사용 인터페이스**

| 방법 | 장점 | 사용자 |
|------|------|--------|
| **CLI** | 빠르고 자동화 가능 | 개발자, 파워유저 |
| **Web UI** | 가장 쉬움, 시각적 | 일반 사용자 |
| **Python API** | 커스터마이징 가능 | 개발자 |

### **5. 종합 Excel 보고서**

- 색상 코딩 (녹색/노랑/빨강)
- 한글/영어 이중 컬럼명
- 필터링 가능
- 피벗 테이블 준비됨

---

## 📁 프로젝트 구조

```
Sales-Data-Prediction/
│
├── 📄 README.md                          ← 이 문서
├── 📄 MONTHLY_UPDATE_GUIDE.md            ← 월간 업데이트 가이드
├── 📄 USER_GUIDE.md                      ← 사용자 매뉴얼
├── 📄 RETRAIN_GUIDE.md                   ← 재학습 가이드
├── 📄 IMPROVEMENTS.md                    ← Gemini 대비 개선사항
│
├── ⚙️  config.yaml                       ← 설정 파일
├── ⚙️  requirements.txt                  ← Python 의존성
├── ⚙️  .gitignore                        ← Git 제외 파일
│
├── 🎯 generate_forecast.py               ← CLI 예측 생성기
├── 🎯 streamlit_app.py                   ← Web UI
│
├── 📂 src/                               ← 소스 코드
│   ├── utils.py                          ← 유틸리티 함수
│   ├── data_pipeline.py                  ← 데이터 파이프라인
│   ├── prediction.py                     ← 예측 엔진
│   ├── abc_classifier.py                 ← ABC 분류
│   ├── excel_exporter.py                 ← Excel 출력
│   └── retrain_model.py                  ← 모델 재학습
│
├── 📂 data/                              ← 데이터
│   ├── raw_sales/                        ← 월간 판매 데이터
│   │   ├── 2024.05_BBG.csv
│   │   ├── 2024.06_BBG.csv
│   │   └── ... (16개 파일)
│   ├── raw_po/
│   │   └── sps_data.csv                  ← PO 데이터
│   └── processed/
│       └── df_for_modeling.csv           ← 전처리된 데이터
│
├── 📂 models/                            ← ML 모델
│   └── trained/
│       ├── lgbm_model_v1.2.pkl           ← LightGBM 모델
│       └── xgb_model_v2_0.pkl            ← XGBoost 모델
│
├── 📂 logs/                              ← 로그 (자동 생성)
│   ├── pipeline.log                      ← 실행 로그
│   ├── abc_classification_history.csv    ← ABC 이력
│   └── performance_tracking.csv          ← 성능 추적
│
└── 📂 predictions/                       ← 예측 결과 (자동 생성)
    └── forecast_YYYYMM.xlsx              ← Excel 예측 파일
```

---

## 📚 문서

| 문서 | 내용 | 대상 |
|------|------|------|
| **README.md** | Setup 및 빠른 시작 | 처음 사용자 |
| **USER_GUIDE.md** | Excel 사용법, 컬럼 설명 | 일반 사용자 |
| **MONTHLY_UPDATE_GUIDE.md** | 월간 데이터 업데이트 절차 | 관리자 |
| **RETRAIN_GUIDE.md** | 모델 재학습 방법 | 기술 담당자 |
| **IMPROVEMENTS.md** | Gemini 대비 개선사항 | 개발자 |

---

## 📊 성능

### **예측 성능 (Test Set: 2025.07-08)**

| 모델 | MAE | RMSE | MAPE |
|------|-----|------|------|
| **Ensemble (LightGBM + XGBoost)** | **38.00** | 78.4 | 42.1% |
| LightGBM v1.2 | 40.81 | 82.3 | 44.8% |
| XGBoost v2.0 | 35.79 | 74.2 | 39.5% |

### **비즈니스 성과**

| 지표 | 값 | 의미 |
|------|-----|------|
| **Fill Rate** | 89.19% | 수요의 89%를 충족 |
| **Stockout** | 7,400 units | 재고 부족 |
| **Overstock** | 37,900 units | 과잉 재고 |
| **시간 절약** | 67.6시간/월 | 76% 업무 시간 단축 |

### **ABC별 성능**

| 카테고리 | SKU 수 | 평균 MAE | 전략 |
|----------|--------|----------|------|
| **A-Items** | 114 (21%) | 347 | 수동 (AI 예측 안 함) |
| **B-Items** | 142 (27%) | 18 | 자동 예측 (높은 정확도) |
| **C-Items** | 279 (52%) | 9 | 자동 예측 (보수적 발주) |

---

## 🔧 트러블슈팅

### **문제 1: 패키지 설치 오류**

**증상:**
```
ERROR: Could not find a version that satisfies the requirement lightgbm>=4.0.0
```

**해결:**
```bash
# Python 버전 확인 (3.8 이상 필요)
python --version

# pip 업그레이드
pip install --upgrade pip

# 다시 설치
pip install -r requirements.txt
```

### **문제 2: 데이터 파일 없음**

**증상:**
```
FileNotFoundError: No such file or directory: 'data/raw_sales/2024.05_BBG.csv'
```

**해결:**
- Git LFS가 필요할 수 있습니다:
```bash
git lfs install
git lfs pull
```

또는 데이터를 수동으로 다운로드하여 `data/` 폴더에 배치

### **문제 3: 모델 파일 없음**

**증상:**
```
FileNotFoundError: models/trained/lgbm_model_v1.2.pkl not found
```

**해결:**
```bash
# Git LFS로 모델 다운로드
git lfs pull

# 또는 GitHub Releases에서 다운로드
```

### **문제 4: Streamlit 실행 안 됨**

**증상:**
```
streamlit: command not found
```

**해결:**
```bash
# Streamlit 재설치
pip install streamlit

# 또는 Python 모듈로 실행
python -m streamlit run streamlit_app.py
```

### **문제 5: Feature Mismatch 오류**

**증상:**
```
LightGBMError: The number of features in data (35) is not the same as it was in training data (32)
```

**해결:**
- 최신 코드로 업데이트:
```bash
git pull origin main
```

이 문제는 이미 수정되었습니다 (Commit: 0af05ed)

### **문제 6: Excel 한글 깨짐**

**증상:**
Excel에서 한글이 깨져 보임

**해결:**
- Excel 열기 옵션에서 **UTF-8 인코딩** 선택
- 또는 Google Sheets로 열기 (자동 인코딩)

---

## 🤝 기여하기

버그 리포트, 기능 제안, Pull Request 환영합니다!

**GitHub Issues:** [Issues 페이지](https://github.com/Lee-Minsoo-97/Sales-Data-Prediction/issues)

---

## 📞 문의

문제가 해결되지 않으면:
1. [GitHub Issues](https://github.com/Lee-Minsoo-97/Sales-Data-Prediction/issues)에 문의
2. 문서 확인: `USER_GUIDE.md`, `MONTHLY_UPDATE_GUIDE.md`
3. 로그 파일 확인: `logs/pipeline.log`

---

## 📜 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🎉 시작하기

```bash
# 1단계: 클론
git clone https://github.com/Lee-Minsoo-97/Sales-Data-Prediction.git
cd Sales-Data-Prediction

# 2단계: 설치
pip install -r requirements.txt

# 3단계: 실행!
python generate_forecast.py --auto
```

**또는 Web UI로:**
```bash
streamlit run streamlit_app.py
```

**첫 예측 결과가 궁금하신가요? 지금 시작하세요!** 🚀

---

**Last Updated:** 2025-10-27
**Version:** 2.0
**Authors:** Lee-Minsoo-97 & Claude Code
