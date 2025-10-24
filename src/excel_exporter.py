"""
Excel Exporter for Sales Predictions

Creates user-friendly Excel files with:
- Multiple sheets (AUTO, MANUAL_REVIEW, MANUAL, Summary)
- Color coding and conditional formatting
- Korean/English column names
- Ready-to-use format for business users
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

from utils import load_config, resolve_path, setup_logging


class ExcelExporter:
    """Export predictions to user-friendly Excel format"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Excel Exporter"""
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)

        # Colors
        self.colors = {
            'header': 'FF4472C4',      # Blue
            'auto': 'FF92D050',        # Green
            'manual_review': 'FFFFC000',  # Yellow
            'manual': 'FFFF6B6B',      # Red
            'high_confidence': 'FFE2EFDA',  # Light green
            'low_confidence': 'FFFFF2CC',   # Light yellow
        }

    def export_predictions(
        self,
        predictions_df: pd.DataFrame,
        output_path: str,
        target_date: str
    ):
        """
        Export predictions to formatted Excel file

        Args:
            predictions_df: Predictions DataFrame from predict_with_strategy()
            output_path: Output Excel file path
            target_date: Target prediction date (YYYY-MM-DD)
        """
        self.logger.info(f"📊 Exporting predictions to Excel: {output_path}")

        # Prepare data
        df = predictions_df.copy()

        # Add Korean column names
        df_display = self._prepare_display_dataframe(df)

        # Split by recommendation type
        auto_df = df_display[df_display['권장사항_EN'] == 'AUTO'].copy()
        review_df = df_display[df_display['권장사항_EN'] == 'MANUAL_REVIEW'].copy()
        manual_df = df_display[df_display['권장사항_EN'] == 'MANUAL'].copy()

        # Create Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Summary
            self._write_summary_sheet(writer, df_display, target_date)

            # Sheet 2: AUTO (자동 발주)
            if not auto_df.empty:
                self._write_data_sheet(
                    writer,
                    auto_df,
                    sheet_name='AUTO_자동발주',
                    color=self.colors['auto']
                )

            # Sheet 3: MANUAL_REVIEW (검토 필요)
            if not review_df.empty:
                self._write_data_sheet(
                    writer,
                    review_df,
                    sheet_name='REVIEW_검토필요',
                    color=self.colors['manual_review']
                )

            # Sheet 4: MANUAL (수동 발주)
            if not manual_df.empty:
                self._write_data_sheet(
                    writer,
                    manual_df,
                    sheet_name='MANUAL_수동발주',
                    color=self.colors['manual']
                )

            # Sheet 5: All Data (전체)
            self._write_data_sheet(
                writer,
                df_display,
                sheet_name='ALL_전체데이터',
                color=self.colors['header']
            )

        # Apply additional formatting
        self._apply_excel_formatting(output_path)

        self.logger.info(f"   ✅ Excel export complete!")
        self.logger.info(f"      AUTO: {len(auto_df)} SKUs")
        self.logger.info(f"      REVIEW: {len(review_df)} SKUs")
        self.logger.info(f"      MANUAL: {len(manual_df)} SKUs")

    def _prepare_display_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare user-friendly display DataFrame"""
        display_df = df.copy()

        # Keep English version for filtering
        display_df['권장사항_EN'] = display_df['Recommendation']

        # Add Korean column names
        column_mapping = {
            'SKU': 'SKU',
            'ABC_Category': 'ABC 분류',
            'Avg_Sales_6M': '최근6개월\n평균판매량',
            'Predicted_Sales': '예측판매량\n(다음달)',
            'Order_Qty': '권장발주량',
            'Recommendation': '권장사항',
            'Confidence_Score': '신뢰도',
            'Anomaly_Score': '이상징후\n점수',
            'Notes': '비고'
        }

        # Rename columns
        display_df = display_df.rename(columns=column_mapping)

        # Translate Recommendation
        rec_translation = {
            'AUTO': '자동발주',
            'MANUAL_REVIEW': '검토필요',
            'MANUAL': '수동발주'
        }
        display_df['권장사항'] = display_df['권장사항'].map(rec_translation)

        # Format numbers
        numeric_cols = ['최근6개월\n평균판매량', '예측판매량\n(다음달)', '권장발주량']
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A"
                )

        # Format scores
        score_cols = ['신뢰도', '이상징후\n점수']
        for col in score_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"{x:.0%}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                )

        # Select and reorder columns
        final_cols = [
            'SKU', 'ABC 분류', '권장사항',
            '최근6개월\n평균판매량', '예측판매량\n(다음달)', '권장발주량',
            '신뢰도', '이상징후\n점수', '비고', '권장사항_EN'
        ]

        display_df = display_df[[col for col in final_cols if col in display_df.columns]]

        return display_df

    def _write_summary_sheet(
        self,
        writer: pd.ExcelWriter,
        df: pd.DataFrame,
        target_date: str
    ):
        """Write summary sheet"""
        ws = writer.book.create_sheet('요약_Summary', 0)

        # Title
        ws['A1'] = f'📊 판매량 예측 리포트 (Sales Forecast Report)'
        ws['A1'].font = Font(size=16, bold=True, color='FF4472C4')
        ws.merge_cells('A1:D1')

        # Date info
        ws['A3'] = '예측 대상 월 (Target Month):'
        ws['B3'] = target_date[:7]
        ws['A4'] = '리포트 생성일 (Generated Date):'
        ws['B4'] = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Statistics
        ws['A6'] = '📈 통계 (Statistics)'
        ws['A6'].font = Font(size=12, bold=True)

        stats = [
            ['구분', 'SKU 개수', '비율'],
            ['전체 SKU', len(df), '100%'],
            ['자동발주 (AUTO)', len(df[df['권장사항_EN'] == 'AUTO']),
             f"{len(df[df['권장사항_EN'] == 'AUTO'])/len(df)*100:.1f}%"],
            ['검토필요 (REVIEW)', len(df[df['권장사항_EN'] == 'MANUAL_REVIEW']),
             f"{len(df[df['권장사항_EN'] == 'MANUAL_REVIEW'])/len(df)*100:.1f}%"],
            ['수동발주 (MANUAL)', len(df[df['권장사항_EN'] == 'MANUAL']),
             f"{len(df[df['권장사항_EN'] == 'MANUAL'])/len(df)*100:.1f}%"],
        ]

        for i, row in enumerate(stats, start=7):
            for j, value in enumerate(row, start=1):
                cell = ws.cell(row=i, column=j, value=value)
                if i == 7:  # Header
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color='FFD9E1F2', fill_type='solid')

        # ABC breakdown
        ws['A13'] = '📊 ABC 분류 (ABC Classification)'
        ws['A13'].font = Font(size=12, bold=True)

        abc_stats = df['ABC 분류'].value_counts().sort_index()
        abc_data = [['ABC 분류', 'SKU 개수', '비율']]

        for abc_cat, count in abc_stats.items():
            abc_data.append([
                abc_cat,
                count,
                f"{count/len(df)*100:.1f}%"
            ])

        for i, row in enumerate(abc_data, start=14):
            for j, value in enumerate(row, start=1):
                cell = ws.cell(row=i, column=j, value=value)
                if i == 14:  # Header
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color='FFE2EFDA', fill_type='solid')

        # Instructions
        ws['A20'] = '📝 사용 방법 (Instructions)'
        ws['A20'].font = Font(size=12, bold=True)

        instructions = [
            '',
            '1️⃣  AUTO_자동발주 시트: 바로 발주 진행하세요 (추가 검토 불필요)',
            '2️⃣  REVIEW_검토필요 시트: 이상 징후 감지됨, 예측값 참고하여 검토 후 발주',
            '3️⃣  MANUAL_수동발주 시트: A-Items, 담당자가 직접 예측 및 발주',
            '',
            '⚠️  권장발주량 = 예측판매량 × 2 (B-Items) 또는 × 1.2 (C-Items)',
            '⚠️  이상징후 점수가 높을수록 주의 필요',
        ]

        for i, text in enumerate(instructions, start=21):
            ws[f'A{i}'] = text

        # Set column widths
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15

    def _write_data_sheet(
        self,
        writer: pd.ExcelWriter,
        df: pd.DataFrame,
        sheet_name: str,
        color: str
    ):
        """Write data sheet with formatting"""
        # Remove English helper column
        display_df = df.drop(columns=['권장사항_EN'], errors='ignore')

        # Write to Excel
        display_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Get worksheet
        ws = writer.sheets[sheet_name]

        # Format header
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFFFF')
            cell.fill = PatternFill(start_color=color, fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 40)
            ws.column_dimensions[column_letter].width = adjusted_width

        # Center align specific columns
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            for idx, cell in enumerate(row):
                if idx in [1, 2, 6, 7]:  # ABC, 권장사항, 신뢰도, 이상징후
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                else:
                    cell.alignment = Alignment(vertical='center')

        # Freeze first row
        ws.freeze_panes = 'A2'

    def _apply_excel_formatting(self, file_path: str):
        """Apply additional Excel formatting"""
        wb = load_workbook(file_path)

        # Add borders to all sheets
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            for row in ws.iter_rows():
                for cell in row:
                    cell.border = thin_border

        wb.save(file_path)


# ============================================================================
# Convenience Function
# ============================================================================

def export_predictions_to_excel(
    predictions_df: pd.DataFrame,
    output_file: str,
    target_date: str
):
    """
    Convenience function to export predictions to Excel

    Args:
        predictions_df: Predictions DataFrame
        output_file: Output Excel file name (without path)
        target_date: Target prediction date

    Returns:
        Path to generated Excel file
    """
    from pathlib import Path

    exporter = ExcelExporter()

    # Determine output path
    config = load_config()
    predictions_dir = resolve_path(config['paths']['predictions'])
    predictions_dir.mkdir(parents=True, exist_ok=True)

    output_path = predictions_dir / output_file

    # Export
    exporter.export_predictions(predictions_df, str(output_path), target_date)

    return output_path
