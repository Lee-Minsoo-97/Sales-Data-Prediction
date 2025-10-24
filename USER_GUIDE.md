# 📘 Sales Forecast 사용자 가이드

## 🎯 개요

iHerb 판매량 예측 시스템을 사용하여 매월 SKU별 판매 예측 및 발주량을 Excel 파일로 받을 수 있습니다.

**특징:**
- ✅ **간단한 사용법**: 명령어 하나로 Excel 생성
- ✅ **자동 분류**: AUTO (자동발주), REVIEW (검토필요), MANUAL (수동발주)
- ✅ **색상 코딩**: 시각적으로 쉽게 구분
- ✅ **한글 지원**: 한국어 컬럼명 및 설명
- ✅ **Web UI 지원**: 브라우저에서 클릭만으로 생성

---

## 🚀 빠른 시작

### **방법 1: CLI 스크립트 (추천)**

```bash
# 프로젝트 루트 디렉토리에서
python generate_forecast.py
```

**대화형 모드:**
```
======================================================================
🔮  iHerb Sales Forecast Generator
======================================================================

📅 예측할 월을 입력하세요
----------------------------------------------------------------------
   기본값: 2025-10 (다음 달)
   형식: YYYY-MM (예: 2025-10)

   입력 (Enter = 기본값): 2025-11

   ✅ 예측 대상 월: 2025-11

🔄 Step 1/5: 데이터 파이프라인 실행 중...
...
```

**자동 모드 (다음 달 자동 예측):**
```bash
python generate_forecast.py --auto
```

**특정 월 지정:**
```bash
python generate_forecast.py --target-date 2025-11-01 --output forecast_nov.xlsx
```

---

### **방법 2: Web UI (Streamlit)**

```bash
# Streamlit 실행
streamlit run streamlit_app.py
```

브라우저에서 자동으로 열립니다 (`http://localhost:8501`)

**화면 구성:**
- 📅 날짜 선택 (사이드바)
- 🚀 예측 생성 버튼
- 📊 결과 통계 및 차트
- 💾 Excel 다운로드 버튼

---

## 📊 출력 Excel 파일 구조

### **Sheet 1: 요약_Summary**

- 예측 대상 월
- 리포트 생성일
- 통계 (AUTO/REVIEW/MANUAL 개수)
- ABC 분류 분포
- 📝 사용 방법

### **Sheet 2: AUTO_자동발주** ✅

**바로 발주 진행 가능한 SKUs**

| SKU | ABC 분류 | 권장사항 | 예측판매량 | 권장발주량 | 신뢰도 | 비고 |
|-----|---------|---------|-----------|-----------|--------|------|
| HBF94449 | B | 자동발주 | 32 | 64 | 90% | Reliable B-Item prediction |
| DMX48237 | C | 자동발주 | 7 | 8 | 70% | Reliable C-Item prediction |

**조치:** 권장발주량대로 발주

---

### **Sheet 3: REVIEW_검토필요** ⚠️

**이상 징후가 감지된 SKUs (검토 필요)**

| SKU | ABC 분류 | 권장사항 | 예측판매량 | 권장발주량 | 이상징후 점수 | 비고 |
|-----|---------|---------|-----------|-----------|-------------|------|
| LFT68101 | B | 검토필요 | 420 | 840 | 80% | ⚠️ PO spike detected, review recommended |

**이상 징후 예시:**
- PO가 평균의 3배 이상 (프로모션 가능성)
- 최근 판매 급변 (50% 이상)
- On Sale 상태

**조치:** 예측값 참고하되, 담당자가 상황 검토 후 최종 발주량 결정

---

### **Sheet 4: MANUAL_수동발주** ✋

**A-Items (고판매량, 수동 예측 필요)**

| SKU | ABC 분류 | 권장사항 | 최근6개월 평균판매량 | 비고 |
|-----|---------|---------|-------------------|------|
| NRP48814 | A | 수동발주 | 3,071 | High-volume A-Item: Manual forecasting required |
| APB68274 | A | 수동발주 | 1,546 | High-volume A-Item: Manual forecasting required |

**조치:** 담당자가 직접 시장 상황, 프로모션 계획 등을 고려하여 발주량 결정

---

### **Sheet 5: ALL_전체데이터**

전체 SKU 데이터 (필터링 및 분석용)

---

## 🎨 색상 코딩

Excel 파일에서 시각적으로 쉽게 구분:

- **🟢 녹색 (AUTO)**: 자동발주 가능
- **🟡 노란색 (REVIEW)**: 검토 필요
- **🔴 빨간색 (MANUAL)**: 수동 발주

---

## 📋 컬럼 설명

### **공통 컬럼**

| 컬럼명 | 설명 | 예시 |
|-------|------|------|
| **SKU** | 제품 코드 | APB68267 |
| **ABC 분류** | 판매량 기준 분류 | A, B, C |
| **권장사항** | 발주 방법 | 자동발주, 검토필요, 수동발주 |
| **최근6개월 평균판매량** | 최근 6개월 월평균 판매량 | 175.7 |

### **예측 관련 컬럼 (AUTO, REVIEW만)**

| 컬럼명 | 설명 | 예시 |
|-------|------|------|
| **예측판매량 (다음달)** | AI 모델 예측값 | 420 |
| **권장발주량** | 예측×2 (B) 또는 예측×1.2 (C) | 840 |
| **신뢰도** | 예측 신뢰도 (0-100%) | 90% |
| **이상징후 점수** | 비정상 패턴 감지 점수 | 0% (정상) ~ 100% (높음) |

### **비고**

예측 근거 또는 주의사항 설명

---

## 🔄 월간 업데이트 프로세스

### **매월 초 (새 데이터 도착 시)**

1. **데이터 업로드**
   ```bash
   # 새 Sales CSV
   cp 2025.10_BBG.csv data/raw_sales/

   # 업데이트된 누적 PO 데이터
   cp updated_sps_data.csv data/raw_po/sps_data.csv
   ```

2. **데이터 파이프라인 실행**
   ```bash
   cd src
   python data_pipeline.py
   ```

3. **예측 생성**
   ```bash
   cd ..
   python generate_forecast.py --auto
   ```

4. **Excel 파일 확인 및 배포**
   ```
   predictions/sales_forecast_YYYYMM.xlsx
   ```

**소요 시간: 약 5-10분**

---

## 💡 사용 팁

### **Tip 1: 발주량 조정**

Excel에서 권장발주량을 기준으로 조정 가능:
- 보수적: × 0.8
- 공격적: × 1.2

### **Tip 2: 필터링**

- Excel 필터 기능으로 특정 Brand, ABC 분류별 확인
- 피벗 테이블로 집계 분석

### **Tip 3: ABC 변경 모니터링**

```bash
# ABC 변경 이력 확인
cat logs/abc_changes_YYYYMMDD.txt
```

**주요 확인 사항:**
- C → B 승격: 판매 증가, AUTO 유지
- B → A 승격: 높은 판매량, MANUAL로 전환
- A → B 하락: 판매 감소, AUTO 전환 가능

### **Tip 4: 성능 모니터링**

```python
# 실제 판매량과 비교 (다음 달)
import pandas as pd

predictions = pd.read_csv('predictions/sales_forecast_202510.csv')
actuals = pd.read_csv('data/raw_sales/2025.10_BBG.csv')

# 정확도 평가
# ...
```

---

## 🛠️ 트러블슈팅

### **문제 1: "데이터가 없습니다" 오류**

**원인:** 데이터 파이프라인 미실행

**해결:**
```bash
cd src
python data_pipeline.py
```

---

### **문제 2: Excel 파일이 열리지 않음**

**원인:** openpyxl 미설치

**해결:**
```bash
pip install openpyxl
```

---

### **문제 3: 특정 SKU가 예측 안 됨**

**원인:** 이력 부족 (3개월 미만)

**해결:**
- 정상입니다
- 해당 SKU는 MANUAL로 표시됨
- 3개월 후 자동으로 예측 가능

---

### **문제 4: 예측값이 이상함**

**확인사항:**
1. 최근 프로모션 있었나? → REVIEW 참고
2. PO가 급증했나? → 이상징후 점수 확인
3. ABC 카테고리 변경됐나? → ABC 변경 로그 확인

**조치:**
- REVIEW 시트 확인
- 비고 컬럼 읽기
- 필요시 수동 조정

---

## 📞 문의

- **기술적 문의**: logs/pipeline.log 확인
- **사용법 문의**: 이 가이드 참조
- **버그 리포트**: GitHub Issues

---

## 🎯 요약

### **일반 사용자용 (담당자)**

1. `python generate_forecast.py` 실행
2. 날짜 선택 (Enter = 다음 달)
3. Excel 파일 다운로드
4. AUTO 시트 → 바로 발주
5. REVIEW 시트 → 검토 후 발주
6. MANUAL 시트 → 수동 예측

**완료! 🎉**

### **고급 사용자용**

- Web UI: `streamlit run streamlit_app.py`
- CLI 자동화: `python generate_forecast.py --auto`
- 월간 업데이트: `MONTHLY_UPDATE_GUIDE.md` 참조

---

**Last Updated**: 2025-10-24
