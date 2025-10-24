#!/usr/bin/env python3
"""
🔮 iHerb Sales Forecast Generator (User-Friendly Version)

간단한 대화형 스크립트로 월간 판매 예측 Excel 파일을 생성합니다.

사용법:
    python generate_forecast.py

또는 인자 전달:
    python generate_forecast.py --target-date 2025-10-01 --output forecast_202510.xlsx
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import pandas as pd
from data_pipeline import SalesDataPipeline
from abc_classifier import ABCClassifier
from prediction import SalesPredictor
from excel_exporter import export_predictions_to_excel


def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("🔮  iHerb Sales Forecast Generator")
    print("=" * 70)
    print()


def get_target_date_interactive():
    """Get target date from user interactively"""
    print("📅 예측할 월을 입력하세요")
    print("-" * 70)

    # Default: next month
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)

    default_date = next_month.strftime('%Y-%m-01')

    print(f"   기본값: {default_date[:7]} (다음 달)")
    print(f"   형식: YYYY-MM (예: 2025-10)")
    print()

    user_input = input("   입력 (Enter = 기본값): ").strip()

    if not user_input:
        target_date = default_date
    else:
        try:
            # Parse user input
            if len(user_input) == 7:  # YYYY-MM
                target_date = f"{user_input}-01"
            else:
                target_date = user_input

            # Validate
            pd.to_datetime(target_date)
        except:
            print(f"   ❌ 잘못된 형식입니다. 기본값({default_date[:7]})을 사용합니다.")
            target_date = default_date

    print(f"   ✅ 예측 대상 월: {target_date[:7]}")
    print()
    return target_date


def run_forecast_pipeline(target_date: str, output_file: Optional[str] = None):
    """Run the full forecast pipeline"""

    print("🔄 Step 1/5: 데이터 파이프라인 실행 중...")
    print("-" * 70)

    # Check if data exists
    data_processed = Path('data/processed/df_for_modeling.csv')

    if not data_processed.exists():
        print("   ⚠️  처리된 데이터가 없습니다. 데이터 파이프라인을 실행합니다...")
        pipeline = SalesDataPipeline()
        df = pipeline.run()
    else:
        print(f"   ✅ 기존 데이터 사용: {data_processed}")
        df = pd.read_csv(data_processed, parse_dates=['Date'])

    print(f"   📊 데이터: {len(df):,} 레코드, {df['SKU'].nunique()} SKUs")
    print()

    # Step 2: ABC Classification
    print("🔄 Step 2/5: ABC 분류 중...")
    print("-" * 70)

    classifier = ABCClassifier()
    abc_df = classifier.classify(df, lookback_months=6)

    # Detect changes
    changes = classifier.detect_category_changes(abc_df)

    if not changes.empty:
        print(f"   ⚠️  {len(changes)}개 SKU의 ABC 카테고리 변경 감지됨")
        print(f"       → 자세한 내용: logs/abc_changes_{datetime.now().strftime('%Y%m%d')}.txt")
        classifier.generate_alert_report(
            changes,
            output_file=f"abc_changes_{datetime.now().strftime('%Y%m%d')}.txt"
        )
    else:
        print("   ✅ ABC 카테고리 변경 없음")

    # Save classification
    classifier.save_classification(abc_df)

    abc_counts = abc_df['ABC'].value_counts()
    print(f"   📊 A-Items: {abc_counts.get('A', 0)}, "
          f"B-Items: {abc_counts.get('B', 0)}, "
          f"C-Items: {abc_counts.get('C', 0)}")
    print()

    # Step 3: Prepare Features
    print("🔄 Step 3/5: 예측 Feature 준비 중...")
    print("-" * 70)

    predictor = SalesPredictor()
    historical_df = predictor.load_historical_data()

    features_df, metadata_df = predictor.prepare_features_for_prediction(
        historical_df,
        target_date
    )

    insufficient = len(metadata_df[metadata_df['status'] == 'insufficient_history'])
    if insufficient > 0:
        print(f"   ⚠️  {insufficient}개 SKU는 이력 부족으로 예측 불가 (수동 발주 필요)")

    print(f"   ✅ {len(features_df)} SKUs 예측 준비 완료")
    print()

    # Step 4: Generate Predictions
    print("🔄 Step 4/5: AI 예측 생성 중...")
    print("-" * 70)

    predictions_df = predictor.predict_with_strategy(features_df, abc_df)

    # Print summary
    rec_counts = predictions_df['Recommendation'].value_counts()
    print(f"   📊 예측 결과:")
    print(f"      ✅ 자동발주 (AUTO): {rec_counts.get('AUTO', 0)} SKUs")
    print(f"      ⚠️  검토필요 (REVIEW): {rec_counts.get('MANUAL_REVIEW', 0)} SKUs")
    print(f"      ✋ 수동발주 (MANUAL): {rec_counts.get('MANUAL', 0)} SKUs")
    print()

    # Step 5: Export to Excel
    print("🔄 Step 5/5: Excel 파일 생성 중...")
    print("-" * 70)

    if output_file is None:
        date_str = pd.to_datetime(target_date).strftime('%Y%m')
        output_file = f"sales_forecast_{date_str}.xlsx"

    output_path = export_predictions_to_excel(
        predictions_df,
        output_file,
        target_date
    )

    print(f"   ✅ Excel 파일 생성 완료!")
    print()

    return output_path


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate sales forecast Excel file'
    )
    parser.add_argument(
        '--target-date',
        type=str,
        help='Target prediction date (YYYY-MM-01)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output Excel file name'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Run in automatic mode (use next month as default)'
    )

    args = parser.parse_args()

    print_banner()

    # Get target date
    if args.auto:
        # Automatic mode: next month
        today = datetime.now()
        next_month = today.replace(day=1) + timedelta(days=32)
        target_date = next_month.replace(day=1).strftime('%Y-%m-01')
        print(f"🤖 자동 모드: 다음 달 예측 ({target_date[:7]})")
        print()
    elif args.target_date:
        target_date = args.target_date
        if len(target_date) == 7:  # YYYY-MM
            target_date = f"{target_date}-01"
        print(f"📅 예측 대상 월: {target_date[:7]}")
        print()
    else:
        # Interactive mode
        target_date = get_target_date_interactive()

    # Run pipeline
    try:
        output_path = run_forecast_pipeline(target_date, args.output)

        # Success message
        print("=" * 70)
        print("🎉 완료!")
        print("=" * 70)
        print()
        print(f"📁 생성된 파일: {output_path}")
        print()
        print("📊 Excel 파일에 포함된 시트:")
        print("   1. 요약_Summary: 통계 및 사용 방법")
        print("   2. AUTO_자동발주: 바로 발주 가능한 SKUs")
        print("   3. REVIEW_검토필요: 이상 징후 감지, 검토 후 발주")
        print("   4. MANUAL_수동발주: A-Items, 수동 예측 필요")
        print("   5. ALL_전체데이터: 전체 데이터")
        print()
        print("💡 Tip: Excel 파일을 열어서 각 시트를 확인하세요!")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ 오류 발생")
        print("=" * 70)
        print(f"   오류 내용: {e}")
        print()
        print("📋 해결 방법:")
        print("   1. logs/pipeline.log 파일 확인")
        print("   2. 데이터 파일이 올바른 위치에 있는지 확인")
        print("      - data/raw_sales/*.csv")
        print("      - data/raw_po/sps_data.csv")
        print("   3. MONTHLY_UPDATE_GUIDE.md 참고")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()
