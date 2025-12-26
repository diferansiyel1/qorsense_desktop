import os
import tempfile
import uuid
from datetime import datetime

import numpy as np
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# --- Chart Generator Class ---
class ChartGenerator:
    """Generates technical analysis charts using Plotly."""

    @staticmethod
    def generate_all_charts(data: list, metrics: dict) -> dict:
        """
        Generates Trend, Hysteresis, DFA, and Radar charts.
        Returns a dictionary of temp file paths.
        """
        paths = {}
        try:
            # 1. Trend Analysis Diagram
            paths['trend'] = ChartGenerator._create_trend_chart(data, metrics.get("slope", 0))

            # 2. Hysteresis Loop (Phase Plot)
            hyst_x = metrics.get("hysteresis_x")
            hyst_y = metrics.get("hysteresis_y")
            if hyst_x and hyst_y:
                paths['hysteresis'] = ChartGenerator._create_hysteresis_chart(hyst_x, hyst_y, metrics.get("hysteresis", 0))

            # 3. DFA Log-Log Plot
            scales = metrics.get("dfa_scales")
            flucts = metrics.get("dfa_fluctuations")
            if scales and flucts:
                paths['dfa'] = ChartGenerator._create_dfa_chart(scales, flucts, metrics.get("hurst", 0.5))

            # 4. Radar Chart
            paths['radar'] = ChartGenerator._create_radar_chart(metrics)

        except Exception as e:
            print(f"Chart generation error: {e}")

        return paths

    @staticmethod
    def _create_trend_chart(data, slope):
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=data, mode='lines', name='Sensor Signal',
                               line=dict(color='#7F007F', width=1.5))) # Logo Purple

        x = np.arange(len(data))
        trend = np.poly1d(np.polyfit(x, data, 1))(x)
        fig.add_trace(go.Scatter(x=x, y=trend, mode='lines', name=f'Trend (m={slope:.4f})',
                               line=dict(color='#EF4444', width=2, dash='dash')))

        fig.update_layout(
            title="Signal Trend & Drift Analysis",
            xaxis_title="Time Step (n)",
            yaxis_title="Amplitude",
            template="plotly_white",
            width=800, height=350,
            margin=dict(l=40, r=40, t=50, b=40),
            showlegend=True
        )
        return ChartGenerator._save_fig(fig, "trend")

    @staticmethod
    def _create_hysteresis_chart(x_data, y_data, area):
        fig = go.Figure()
        # Scatter Plot: Logo Purple
        fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='markers', name='Hysteresis Loop',
                               marker=dict(color='#7F007F', size=4, opacity=0.6)))

        fig.update_layout(
            title=f"Hysteresis Phase Plot (Area={area:.4f})",
            xaxis_title="Input Signal (t)",
            yaxis_title="Output Response (t+1)",
            template="plotly_white",
            width=400, height=350,
            margin=dict(l=40, r=40, t=50, b=40),
            showlegend=False
        )
        return ChartGenerator._save_fig(fig, "hyst")

    @staticmethod
    def _create_dfa_chart(scales, flucts, hurst):
        log_scales = np.log10(scales)
        log_flucts = np.log10(flucts)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=log_scales, y=log_flucts, mode='markers', name='DFA Points',
                               marker=dict(color='#F59E0B', size=8))) # Orange for contrast

        fit = np.poly1d(np.polyfit(log_scales, log_flucts, 1))(log_scales)
        fig.add_trace(go.Scatter(x=log_scales, y=fit, mode='lines', name=f'Fit (H={hurst:.2f})',
                               line=dict(color='#36246D', width=2))) # Deep Brand Purple

        fig.update_layout(
            title="DFA Fractal Analysis (Log-Log)",
            xaxis_title="Log(Scale)",
            yaxis_title="Log(Fluctuation)",
            template="plotly_white",
            width=400, height=350,
            margin=dict(l=40, r=40, t=50, b=40)
        )
        return ChartGenerator._save_fig(fig, "dfa")

    @staticmethod
    def _create_radar_chart(metrics: dict):
        # 5 Axes: Bias, Slope, Noise, Hysteresis, DFA
        # Normalize to 0-100 where 100 is HIT LIMIT (Bad)
        def norm(val, threshold):
            return min(100, (abs(val) / threshold) * 100)

        bias = metrics.get('bias', 0)
        slope = metrics.get('slope', 0)
        noise = metrics.get('noise_std', 0)
        hyst = metrics.get('hysteresis', 0)
        hurst_dev = abs(0.5 - metrics.get('hurst', 0.5))

        values = [
            norm(bias, 2.0),
            norm(slope, 0.1),
            norm(noise, 1.5),
            norm(hyst, 0.5),
            norm(hurst_dev, 0.3)
        ]

        categories = ['Bias', 'Slope', 'Noise', 'Hysteresis', 'DFA Dev']

        fig = go.Figure()

        # Risk Polygon
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            fillcolor='rgba(127, 0, 127, 0.2)', # Logo Purple 0.2
            line=dict(color='#7F007F', width=2),
            name='Risk Profile'
        ))

        # Limit Line (100)
        fig.add_trace(go.Scatterpolar(
            r=[100]*5,
            theta=categories,
            mode='lines',
            line=dict(color='#EF4444', width=1, dash='dot'),
            name='Critical Limit'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            template="plotly_white",
            width=400, height=350,
            margin=dict(l=40, r=40, t=20, b=20),
            showlegend=False
        )
        return ChartGenerator._save_fig(fig, "radar")

    @staticmethod
    def _save_fig(fig, prefix):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{prefix}.png")
        fig.write_image(temp.name, scale=2)
        return temp.name


class QorSenseReportGenerator:
    def __init__(self, filename):
        self.filename = filename
        self.doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=15*mm, leftMargin=15*mm,
            topMargin=35*mm, bottomMargin=20*mm
        )
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        self.report_id = str(uuid.uuid4()).split('-')[0].upper()

    def _create_custom_styles(self):
        self.brand_primary = colors.HexColor('#7F007F') # Logo Purple
        self.brand_dark = colors.HexColor('#36246D') # Logo Deep Blue/Purple
        self.dark_gray = colors.HexColor('#222831')
        self.light_gray = colors.HexColor('#f3f4f6')

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=14,
            leading=18,
            textColor=self.brand_primary,
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='NormalSmall',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.dark_gray
        ))

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # --- Header ---
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
             canvas.drawImage(logo_path, 15*mm, 272*mm, width=35*mm, height=12*mm, preserveAspectRatio=True, mask='auto')
        else:
             canvas.setFont('Helvetica-Bold', 18)
             canvas.setFillColor(self.brand_primary)
             canvas.drawString(15*mm, 275*mm, "QorSense")

        canvas.setFont('Helvetica-Bold', 14)
        canvas.setFillColor(self.dark_gray)
        canvas.drawRightString(195*mm, 280*mm, "Predictive Maintenance Certificate of Analysis")

        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.gray)
        date_str = datetime.now().strftime("%d %b %Y")
        canvas.drawRightString(195*mm, 275*mm, f"Report ID: {self.report_id} | Date: {date_str} | Page {doc.page}")

        canvas.setStrokeColor(self.brand_primary)
        canvas.setLineWidth(3)
        canvas.line(15*mm, 268*mm, 195*mm, 268*mm)

        # --- Footer ---
        canvas.setLineWidth(0.5)
        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(15*mm, 15*mm, 195*mm, 15*mm)

        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.gray)
        canvas.drawString(15*mm, 10*mm, "Generated by QorSense AI Engine.")
        canvas.drawRightString(195*mm, 10*mm, "Produced by Pikolab Ar&Ge Ltd.")

        canvas.restoreState()

    def generate(self, metrics: dict, raw_data: list, diagnosis: str, health_score: float):
        story = []

        # 1. Executive Summary & Asset Info
        sensor_id = metrics.get('sensor_id', 'Unknown')

        if health_score >= 80:
            status_text = "OPTIMAL"
            status_color = colors.HexColor('#10b981')
            rec_action = "No Action Required"
        elif health_score >= 50:
            status_text = "WARNING"
            status_color = colors.HexColor('#f59e0b')
            rec_action = "Schedule Calibration"
        else:
            status_text = "CRITICAL"
            status_color = colors.HexColor('#ef4444')
            rec_action = "Maintenance Required"

        # Top Table: Asset Info (Left) | Health Score (Right)
        asset_info = [
            [Paragraph("<b>Asset Name:</b>", self.styles['NormalSmall']), Paragraph(metrics.get('name', 'N/A'), self.styles['NormalSmall'])],
            [Paragraph("<b>Sensor ID:</b>", self.styles['NormalSmall']), Paragraph(sensor_id, self.styles['NormalSmall'])],
            [Paragraph("<b>Location:</b>", self.styles['NormalSmall']), Paragraph(metrics.get('location', 'N/A'), self.styles['NormalSmall'])],
            [Paragraph("<b>Type:</b>", self.styles['NormalSmall']), Paragraph(metrics.get('source_type', 'N/A'), self.styles['NormalSmall'])]
        ]

        t_asset = Table(asset_info, colWidths=[30*mm, 60*mm])
        t_asset.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (0,-1), self.light_gray),
        ]))

        # Score Box
        score_data = [
            [Paragraph("<b>HEALTH SCORE</b>", ParagraphStyle('SL', alignment=1, fontSize=8, textColor=colors.white))],
            [Paragraph(f"<font size=20><b>{health_score:.1f}</b></font>", ParagraphStyle('SV', alignment=1, textColor=colors.white))],
            [Paragraph(f"<b>{status_text}</b>", ParagraphStyle('XV', alignment=1, fontSize=10, textColor=colors.white))]
        ]
        t_score = Table(score_data, colWidths=[50*mm])
        t_score.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), status_color),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('ROUNDEDCORNERS', [6,6,6,6]),
        ]))

        # Summary Header Wrapper
        main_header_data = [[t_asset, t_score]]
        t_main = Table(main_header_data, colWidths=[110*mm, 60*mm])
        t_main.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        story.append(t_main)
        story.append(Spacer(1, 10*mm))

        # Generate Charts
        chart_paths = ChartGenerator.generate_all_charts(raw_data, metrics)

        # 2. Detailed Technical Analysis (Left) vs Radar Chart (Right)
        story.append(Paragraph("Technical Metrics & Risk Profile", self.styles['SectionHeader']))

        def get_icon(val, metric_type):
            if metric_type == 'slope': return "!" if abs(val) > 0.1 else "OK"
            if metric_type == 'noise': return "!" if val > 1.5 else "OK"
            if metric_type == 'bias': return "!" if abs(val) > 2.0 else "OK"
            return "OK"

        metric_rows = [
            ["Metric", "Value", "Limit", "St"],
            ["Bias", f"{metrics.get('bias',0):.3f}", "+/-2.0", get_icon(metrics.get('bias',0), 'bias')],
            ["Slope", f"{metrics.get('slope',0):.4f}", "+/-0.1", get_icon(metrics.get('slope',0), 'slope')],
            ["Noise", f"{metrics.get('noise_std',0):.3f}", "< 1.5", get_icon(metrics.get('noise_std',0), 'noise')],
            ["Hysteresis", f"{metrics.get('hysteresis',0):.3f}", "< 0.5", "OK"],
            ["DFA (Hurst)", f"{metrics.get('hurst',0.5):.2f}", "0.5+/-", "OK"],
        ]

        t_metrics = Table(metric_rows, colWidths=[30*mm, 25*mm, 20*mm, 15*mm])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.brand_primary),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, self.light_gray]),
        ]))

        # Radar Chart
        radar_img = None
        if 'radar' in chart_paths:
            radar_img = Image(chart_paths['radar'], width=85*mm, height=75*mm)
        else:
            radar_img = Paragraph("No Radar Data", self.styles['Normal'])

        # Side by Side
        t_mid = Table([[t_metrics, radar_img]], colWidths=[95*mm, 85*mm])
        t_mid.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
        ]))
        story.append(t_mid)

        # AI Diagnosis
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph(f"<b>Diagnosis:</b> {diagnosis}", self.styles['Normal']))
        if metrics.get('recommendation'):
             story.append(Paragraph(f"<b>Recommendation:</b> {metrics.get('recommendation')}", self.styles['Normal']))

        # 3. Visual Evidence
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph("Signal Analysis Evidence", self.styles['SectionHeader']))

        if 'trend' in chart_paths:
            story.append(Image(chart_paths['trend'], width=170*mm, height=75*mm))
            story.append(Paragraph("Figure 1: Raw Signal Trend and Drift Line", self.styles['NormalSmall']))

        # Side by Side: Hysteresis & DFA
        charts_row = []
        if 'hysteresis' in chart_paths:
             img_hyst = Image(chart_paths['hysteresis'], width=85*mm, height=75*mm)
             charts_row.append(img_hyst)

        if 'dfa' in chart_paths:
             img_dfa = Image(chart_paths['dfa'], width=85*mm, height=75*mm)
             charts_row.append(img_dfa)

        if charts_row:
            story.append(Spacer(1, 5*mm))
            t_charts = Table([charts_row], colWidths=[85*mm] * len(charts_row))
            t_charts.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            story.append(t_charts)

            # Captions
            captions = []
            if 'hysteresis' in chart_paths: captions.append("Fig 2: Hysteresis (Phase Plot)")
            if 'dfa' in chart_paths: captions.append("Fig 3: DFA (Fractal Analysis)")

            t_caps = Table([captions], colWidths=[85*mm] * len(captions))
            t_caps.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 9), ('TEXTCOLOR', (0,0), (-1,-1), self.dark_gray)]))
            story.append(t_caps)

        story.append(Spacer(1, 10*mm))

        # 4. Sign-off
        story.append(Paragraph("Approval", self.styles['SectionHeader']))
        sign_data = [
            ["Automated Analysis Verified", "Maintenance Supervisor"],
            [f"ID: QOR-AI-v2\nTime: {datetime.now().strftime('%H:%M:%S')}", "Signature:"],
        ]
        t_sign = Table(sign_data, colWidths=[90*mm, 90*mm])
        t_sign.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('LINEABOVE', (0,2), (-1,2), 1, colors.black),
            ('TOPPADDING', (0,1), (-1,1), 15),
        ]))
        story.append(t_sign)

        self.doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)


def create_pdf(metrics: dict, raw_data: list, diagnosis: str, health_score: float) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    generator = QorSenseReportGenerator(temp_file.name)
    generator.generate(metrics, raw_data, diagnosis, health_score)
    return temp_file.name
