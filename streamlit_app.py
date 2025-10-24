#!/usr/bin/env python3
"""
🌐 iHerb Sales Forecast Web Application

Streamlit-based web interface for generating sales forecasts.

Usage:
    streamlit run streamlit_app.py

Features:
    - User-friendly web interface
    - Date picker for target month
    - One-click forecast generation
    - Download Excel file
    - View summary statistics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from data_pipeline import SalesDataPipeline
from abc_classifier import ABCClassifier
from prediction import SalesPredictor
from excel_exporter import export_predictions_to_excel


# Page config
st.set_page_config(
    page_title="iHerb Sales Forecast",
    page_icon="🔮",
    layout="wide"
)


def load_data():
    """Load processed data"""
    data_file = Path('data/processed/df_for_modeling.csv')

    if not data_file.exists():
        return None

    return pd.read_csv(data_file, parse_dates=['Date'])


@st.cache_data
def run_abc_classification(df):
    """Run ABC classification"""
    classifier = ABCClassifier()
    abc_df = classifier.classify(df, lookback_months=6)
    changes = classifier.detect_category_changes(abc_df)

    return abc_df, changes


@st.cache_data
def generate_predictions(target_date, abc_df):
    """Generate predictions"""
    predictor = SalesPredictor()
    historical_df = predictor.load_historical_data()

    features_df, metadata_df = predictor.prepare_features_for_prediction(
        historical_df,
        target_date
    )

    predictions_df = predictor.predict_with_strategy(features_df, abc_df)

    return predictions_df, metadata_df


def main():
    """Main Streamlit app"""

    # Header
    st.title("🔮 iHerb Sales Forecast Generator")
    st.markdown("---")

    # Sidebar
    st.sidebar.header("⚙️ 설정")

    # Check data
    df = load_data()

    if df is None:
        st.error("❌ 데이터가 없습니다!")
        st.info("먼저 데이터 파이프라인을 실행하세요:\n```\ncd src\npython data_pipeline.py\n```")
        st.stop()

    # Show data info
    st.sidebar.success(f"✅ 데이터 로드 완료")
    st.sidebar.metric("총 레코드", f"{len(df):,}")
    st.sidebar.metric("SKU 개수", f"{df['SKU'].nunique():,}")
    st.sidebar.metric("데이터 기간",
                      f"{df['Date'].min().strftime('%Y-%m')} ~ {df['Date'].max().strftime('%Y-%m')}")

    # Date picker
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 예측 대상 월 선택")

    # Default: next month
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    default_date = next_month.replace(day=1)

    target_date = st.sidebar.date_input(
        "예측할 월의 1일을 선택하세요",
        value=default_date,
        min_value=datetime(2025, 1, 1),
        max_value=datetime(2030, 12, 1)
    )

    target_date_str = target_date.strftime('%Y-%m-01')

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"📊 예측 대상: {target_date.strftime('%Y년 %m월')}")

    with col2:
        generate_button = st.button("🚀 예측 생성", type="primary", use_container_width=True)

    st.markdown("---")

    # Generate forecast
    if generate_button:
        with st.spinner("예측 생성 중... (약 10-30초 소요)"):
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Step 1: ABC Classification
            status_text.text("Step 1/3: ABC 분류 중...")
            progress_bar.progress(33)

            abc_df, changes = run_abc_classification(df)

            # Step 2: Generate Predictions
            status_text.text("Step 2/3: AI 예측 생성 중...")
            progress_bar.progress(66)

            predictions_df, metadata_df = generate_predictions(target_date_str, abc_df)

            # Step 3: Export to Excel
            status_text.text("Step 3/3: Excel 파일 생성 중...")
            progress_bar.progress(100)

            date_str = target_date.strftime('%Y%m')
            output_file = f"sales_forecast_{date_str}.xlsx"

            output_path = export_predictions_to_excel(
                predictions_df,
                output_file,
                target_date_str
            )

            progress_bar.empty()
            status_text.empty()

        # Success message
        st.success(f"✅ 예측 생성 완료! ({len(predictions_df)} SKUs)")

        # Summary statistics
        st.subheader("📈 예측 결과 요약")

        col1, col2, col3, col4 = st.columns(4)

        rec_counts = predictions_df['Recommendation'].value_counts()

        with col1:
            st.metric("전체 SKU", len(predictions_df))

        with col2:
            auto_count = rec_counts.get('AUTO', 0)
            st.metric("✅ 자동발주", auto_count,
                      delta=f"{auto_count/len(predictions_df)*100:.1f}%")

        with col3:
            review_count = rec_counts.get('MANUAL_REVIEW', 0)
            st.metric("⚠️ 검토필요", review_count,
                      delta=f"{review_count/len(predictions_df)*100:.1f}%")

        with col4:
            manual_count = rec_counts.get('MANUAL', 0)
            st.metric("✋ 수동발주", manual_count,
                      delta=f"{manual_count/len(predictions_df)*100:.1f}%")

        # ABC breakdown chart
        st.subheader("📊 ABC 분류 분포")

        col1, col2 = st.columns(2)

        with col1:
            # ABC count chart
            abc_counts = predictions_df['ABC_Category'].value_counts()

            fig = px.pie(
                values=abc_counts.values,
                names=abc_counts.index,
                title="ABC 카테고리별 SKU 개수",
                color_discrete_map={'A': '#FF6B6B', 'B': '#FFC000', 'C': '#92D050'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Recommendation chart
            rec_counts_series = predictions_df['Recommendation'].value_counts()

            fig = px.bar(
                x=rec_counts_series.index,
                y=rec_counts_series.values,
                title="권장사항별 분포",
                labels={'x': '권장사항', 'y': 'SKU 개수'},
                color=rec_counts_series.index,
                color_discrete_map={
                    'AUTO': '#92D050',
                    'MANUAL_REVIEW': '#FFC000',
                    'MANUAL': '#FF6B6B'
                }
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # ABC changes
        if not changes.empty:
            st.subheader("🔄 ABC 카테고리 변경")

            st.warning(f"⚠️ {len(changes)}개 SKU의 ABC 카테고리가 변경되었습니다")

            # Filter significant changes
            significant_changes = changes[
                changes['change_type'].isin(['UPGRADED', 'DOWNGRADED'])
            ]

            if not significant_changes.empty:
                st.dataframe(
                    significant_changes[[
                        'SKU', 'previous_ABC', 'current_ABC', 'change_type',
                        'previous_avg_sales', 'current_avg_sales', 'sales_change_pct'
                    ]],
                    use_container_width=True
                )

        # Preview data
        st.subheader("📋 예측 데이터 미리보기")

        # Tabs for different categories
        tab1, tab2, tab3 = st.tabs(["✅ 자동발주", "⚠️ 검토필요", "✋ 수동발주"])

        with tab1:
            auto_df = predictions_df[predictions_df['Recommendation'] == 'AUTO']
            if not auto_df.empty:
                st.dataframe(
                    auto_df[[
                        'SKU', 'ABC_Category', 'Predicted_Sales', 'Order_Qty',
                        'Confidence_Score', 'Notes'
                    ]].head(20),
                    use_container_width=True
                )
            else:
                st.info("자동발주 대상 SKU가 없습니다")

        with tab2:
            review_df = predictions_df[predictions_df['Recommendation'] == 'MANUAL_REVIEW']
            if not review_df.empty:
                st.dataframe(
                    review_df[[
                        'SKU', 'ABC_Category', 'Predicted_Sales', 'Order_Qty',
                        'Anomaly_Score', 'Notes'
                    ]].head(20),
                    use_container_width=True
                )
            else:
                st.info("검토 필요 SKU가 없습니다")

        with tab3:
            manual_df = predictions_df[predictions_df['Recommendation'] == 'MANUAL']
            if not manual_df.empty:
                st.dataframe(
                    manual_df[[
                        'SKU', 'ABC_Category', 'Avg_Sales_6M', 'Notes'
                    ]].head(20),
                    use_container_width=True
                )
            else:
                st.info("수동발주 대상 SKU가 없습니다")

        # Download button
        st.markdown("---")
        st.subheader("💾 Excel 파일 다운로드")

        with open(output_path, 'rb') as f:
            st.download_button(
                label="📥 Excel 파일 다운로드",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

        st.info(f"💡 Tip: Excel 파일에는 5개 시트가 포함되어 있습니다 (요약, AUTO, REVIEW, MANUAL, 전체)")

    else:
        # Show instructions when not generated
        st.info("👈 왼쪽에서 예측 대상 월을 선택하고 '🚀 예측 생성' 버튼을 클릭하세요")

        # Show current ABC distribution
        st.subheader("📊 현재 ABC 분류 (최근 6개월 기준)")

        abc_df, _ = run_abc_classification(df)

        col1, col2, col3 = st.columns(3)

        abc_counts = abc_df['ABC'].value_counts()

        with col1:
            st.metric("A-Items (High Volume)", abc_counts.get('A', 0))

        with col2:
            st.metric("B-Items (Medium Volume)", abc_counts.get('B', 0))

        with col3:
            st.metric("C-Items (Low Volume)", abc_counts.get('C', 0))


if __name__ == '__main__':
    main()
