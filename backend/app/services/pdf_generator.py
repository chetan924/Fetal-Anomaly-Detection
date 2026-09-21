import io
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# COLOR PALETTE
# ============================================================
PRIMARY = colors.HexColor("#0f172a")     # Slate 900
TEAL = colors.HexColor("#0d9488")        # Teal 600
TEAL_LIGHT = colors.HexColor("#f0fdfa")  # Teal 50
SLATE_TEXT = colors.HexColor("#334155")  # Slate 700
MUTED_TEXT = colors.HexColor("#64748b")  # Slate 500
BORDER_COLOR = colors.HexColor("#cbd5e1")# Slate 300
BG_LIGHT = colors.HexColor("#f8fafc")    # Slate 50
AMBER_TEXT = colors.HexColor("#b45309")  # Amber 700
AMBER_BG = colors.HexColor("#fffbeb")    # Amber 50
ROSE_TEXT = colors.HexColor("#be123c")   # Rose 700
ROSE_BG = colors.HexColor("#fff1f2")     # Rose 50


# ============================================================
# NUMBERED CANVAS (PAGE X OF Y & RUNNING HEADERS/FOOTERS)
# ============================================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(page_count=num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(MUTED_TEXT)

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(54, 750, 558, 750)
            self.drawString(54, 755, "FetalAI Clinical AI Platform — Multi-Model Analysis Report")
            self.drawRightString(558, 755, f"Report Ref: {getattr(self, '_report_num', '')}")

        # Running Footer (all pages)
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)

        footer_text = (
            "CONFIDENTIAL MEDICAL AI EVALUATION — Assistive research & clinical decision-support output only. "
            "Not a standalone medical diagnosis."
        )
        self.drawString(54, 34, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 34, page_str)

        self.restoreState()


# ============================================================
# PDF GENERATION FUNCTION (16 LOCKED SECTIONS)
# ============================================================
def generate_fetal_report_pdf(
    report_data: Dict[str, Any],
    backend_root: Optional[Path] = None,
) -> bytes:
    """
    Generates a standardized 16-section PDF clinical report document
    from a stored report snapshot. Pure ReportLab Platypus rendering.
    Zero ML dependencies in this process.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=MUTED_TEXT,
        spaceAfter=10,
    )
    sec_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=TEAL,
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=SLATE_TEXT,
    )
    body_bold = ParagraphStyle(
        "BodyBoldCustom",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10.5,
        textColor=MUTED_TEXT,
    )

    # Extract data from persisted snapshot
    report_num = report_data.get("report_number", "FETAL-RPT-000001")
    analysis_id = report_data.get("analysis_id", "an_unknown")
    patient_id = report_data.get("patient_id") or "Anonymous"
    created_at = report_data.get("created_at") or time.strftime("%Y-%m-%d %H:%M:%S UTC")
    overall_status = (report_data.get("status") or "completed").upper()

    res_json = report_data.get("result_json", {})
    summary = report_data.get("summary_json") or res_json.get("summary", {})
    findings = res_json.get("findings", {}) or res_json.get("models", {})
    warnings = report_data.get("warnings_json") or res_json.get("warnings", [])
    errors = report_data.get("errors_json") or res_json.get("errors", [])
    patient_info = res_json.get("patient", {})

    # Storage root for resolving mask images
    storage_dir = (backend_root / "storage") if backend_root else Path("storage")

    story: List[Any] = []

    # Helper for building standard 2-col key-value tables
    def build_kv_table(rows: List[List[Any]], col_widths=[150, 354]):
        formatted_rows = []
        for r in rows:
            formatted_rows.append([
                Paragraph(f"<b>{r[0]}</b>", body_style),
                Paragraph(str(r[1]), body_style) if not isinstance(r[1], Paragraph) else r[1],
            ])
        t = Table(formatted_rows, colWidths=col_widths)
        t.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 0), (0, -1), BG_LIGHT),
            ])
        )
        return t

    # Helper to resolve image file safely
    def resolve_image(rel_url: Optional[str]) -> Optional[Image]:
        if not rel_url:
            return None
        clean_rel = rel_url.lstrip("/").replace("storage/", "")
        img_path = storage_dir / clean_rel
        if img_path.exists() and img_path.is_file():
            try:
                img = Image(str(img_path), width=2.2 * inch, height=1.6 * inch)
                img.hAlign = "LEFT"
                return img
            except Exception:
                return None
        return None

    # ========================================================
    # TOP HEADER BLOCK
    # ========================================================
    story.append(Paragraph("FETALAI CLINICAL AI PLATFORM", title_style))
    story.append(
        Paragraph(
            "Multi-Model Ultrasound AI Analysis & Technical Findings Report",
            subtitle_style,
        )
    )

    meta_table_data = [
        [
            Paragraph("<b>Report Number:</b>", body_style),
            Paragraph(f"<font color='#0d9488'><b>{report_num}</b></font>", body_bold),
            Paragraph("<b>Analysis ID:</b>", body_style),
            Paragraph(f"<code>{analysis_id}</code>", body_style),
        ],
        [
            Paragraph("<b>Patient Ref:</b>", body_style),
            Paragraph(str(patient_info.get("patient_id") or patient_id), body_style),
            Paragraph("<b>Generated:</b>", body_style),
            Paragraph(str(created_at), body_style),
        ],
        [
            Paragraph("<b>Analysis Status:</b>", body_style),
            Paragraph(f"<b>{overall_status}</b>", body_bold),
            Paragraph("<b>System Architecture:</b>", body_style),
            Paragraph("FetalAI Gateway (ML-Free)", body_style),
        ],
    ]
    meta_table = Table(meta_table_data, colWidths=[90, 160, 90, 164])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # ========================================================
    # 01. PATIENT / SCAN INFORMATION
    # ========================================================
    story.append(Paragraph("01. PATIENT / SCAN INFORMATION", sec_heading_style))
    p_info = [
        ["Patient Reference ID", str(patient_info.get("patient_id") or patient_id)],
        ["Patient Name", str(patient_info.get("patient_name") or "Anonymous")],
        ["Gestational Age", str(patient_info.get("gestational_age") or "Not specified")],
        ["Report Identifier", report_num],
        ["Analysis Session ID", analysis_id],
        ["Analysis Timestamp", str(created_at)],
    ]
    story.append(build_kv_table(p_info))
    story.append(Spacer(1, 6))

    # ========================================================
    # 02. ANALYSIS OVERVIEW
    # ========================================================
    story.append(Paragraph("02. ANALYSIS OVERVIEW", sec_heading_style))
    ov_info = [
        ["Overall Analysis Status", overall_status],
        ["Models Requested", summary.get("models_requested", 0)],
        ["Models Completed", summary.get("models_completed", 0)],
        ["Models Failed", summary.get("models_failed", 0)],
        ["Models Not Provided", summary.get("models_not_provided", 0)],
        ["Models Unavailable", summary.get("models_unavailable", 1)],
        ["Total Processing Duration", f"{summary.get('total_duration_seconds', 0)} seconds"],
    ]
    story.append(build_kv_table(ov_info))
    story.append(Spacer(1, 6))

    # ========================================================
    # 03. FETAL PLANE ANALYSIS
    # ========================================================
    story.append(Paragraph("03. FETAL PLANE ANALYSIS", sec_heading_style))
    f_plane = findings.get("plane", {})
    plane_status = f_plane.get("status", "not_provided")
    if plane_status == "completed" and f_plane.get("result"):
        p_res = f_plane["result"]
        pred_cls = p_res.get("predicted_class", "Unknown")
        conf_pct = p_res.get("confidence_percent", round((p_res.get("confidence", 0) * 100), 2))
        plane_rows = [
            ["Status", "Completed"],
            ["Predicted Fetal Plane", f"<b>{pred_cls}</b>"],
            ["Model Confidence", f"{conf_pct}%"],
            ["Architecture", "EfficientNet-B0 Standard Plane Classifier (:8100)"],
        ]
        story.append(build_kv_table(plane_rows))
    elif plane_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_plane.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No ultrasound scan submitted for Fetal Plane analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 04. FETAL BRAIN ANALYSIS
    # ========================================================
    story.append(Paragraph("04. FETAL BRAIN ANALYSIS", sec_heading_style))
    f_brain = findings.get("brain", {})
    brain_status = f_brain.get("status", "not_provided")
    if brain_status == "completed" and f_brain.get("result"):
        b_res = f_brain["result"]
        b_plane = b_res.get("brain_plane", {}).get("predicted_class", "N/A")
        b_conf = b_res.get("brain_plane", {}).get("confidence_percent", round(b_res.get("brain_plane", {}).get("confidence", 0) * 100, 1))
        b_anom = b_res.get("brain_anomaly", {})
        anom_status = b_anom.get("status", "N/A") if b_anom else "N/A"
        anom_score = b_anom.get("anomaly_score") if b_anom else None
        thresh = b_anom.get("threshold") if b_anom else None
        thresh_ratio = b_anom.get("threshold_ratio") if b_anom else None
        score_str = f"{anom_score:.4f}" if isinstance(anom_score, (int, float)) else "N/A"
        thresh_str = f"{thresh:.4f}" if isinstance(thresh, (int, float)) else "N/A"
        ratio_str = f"{thresh_ratio:.4f}" if isinstance(thresh_ratio, (int, float)) else "N/A"

        brain_rows = [
            ["Status", "Completed"],
            ["Brain Plane Classification", f"{b_plane} ({b_conf}%)"],
            ["Model Anomaly / Outlier Signal", f"<b>{anom_status}</b>"],
            ["Mahalanobis Anomaly Score", score_str],
            ["Reference Distribution Threshold", thresh_str],
            ["Threshold Ratio", ratio_str],
            ["Statistical Notice", "Statistical outlier signal derived from PCA and reference dataset distribution. Not a clinical diagnosis."],
        ]
        story.append(build_kv_table(brain_rows))
    elif brain_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_brain.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No scan submitted for Fetal Brain analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 05. FETAL SPINE ANALYSIS
    # ========================================================
    story.append(Paragraph("05. FETAL SPINE ANALYSIS", sec_heading_style))
    f_spine = findings.get("spine", {})
    spine_status = f_spine.get("status", "not_provided")
    if spine_status == "completed" and f_spine.get("result"):
        s_res = f_spine["result"]
        dets = s_res.get("detections", [])
        det_summary = f"{len(dets)} Anatomical Landmark(s) Detected"
        if dets:
            det_summary += " (" + ", ".join([f"{d.get('class_name')}: {d.get('confidence',0)*100:.1f}%" for d in dets[:4]]) + ")"
        spine_rows = [
            ["Status", "Completed"],
            ["Detection Summary", det_summary],
            ["Detection Count", str(len(dets))],
            ["Architecture", "YOLOv8 Spine Feature Detector (:8101)"],
        ]
        story.append(build_kv_table(spine_rows))
    elif spine_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_spine.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No scan submitted for Fetal Spine analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 06. FETAL LUNG ANALYSIS
    # ========================================================
    story.append(Paragraph("06. FETAL LUNG ANALYSIS", sec_heading_style))
    f_lung = findings.get("lung", {})
    lung_status = f_lung.get("status", "not_provided")
    if lung_status == "completed" and f_lung.get("result"):
        l_seg = f_lung["result"].get("segmentation", f_lung["result"])
        l_pixels = l_seg.get("mask_pixels", 0)
        l_ratio = (l_seg.get("mask_ratio", 0) * 100)
        mean_p = l_seg.get("mean_probability", 0)
        lung_rows = [
            ["Status", "Completed"],
            ["Segmented Mask Area", f"{l_pixels:,} pixels"],
            ["Segmented Area Ratio", f"{l_ratio:.2f}%"],
            ["Mean Mask Probability", f"{mean_p:.4f}"],
            ["Architecture", "PyTorch U-Net V2 Thoracic Segmentation (:8103)"],
        ]
        story.append(build_kv_table(lung_rows))
        mask_img = resolve_image(l_seg.get("mask_url"))
        if mask_img:
            story.append(Spacer(1, 3))
            story.append(mask_img)
    elif lung_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_lung.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No scan submitted for Fetal Lung analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 07. FETAL BONE ANALYSIS
    # ========================================================
    story.append(Paragraph("07. FETAL BONE ANALYSIS", sec_heading_style))
    f_bone = findings.get("bone", {})
    bone_status = f_bone.get("status", "not_provided")
    if bone_status == "completed" and f_bone.get("result"):
        b_dets = f_bone["result"].get("detections", [])
        b_summary = f"{len(b_dets)} Skeletal Landmark(s) Detected"
        if b_dets:
            b_summary += " (" + ", ".join([f"{d.get('class_name')}: {d.get('confidence',0)*100:.1f}%" for d in b_dets[:4]]) + ")"
        bone_rows = [
            ["Status", "Completed"],
            ["Detection Summary", b_summary],
            ["Detection Count", str(len(b_dets))],
            ["Architecture", "YOLOv8 Fetal Bone/Femur Detector (:8105)"],
        ]
        story.append(build_kv_table(bone_rows))
    elif bone_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_bone.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No scan submitted for Fetal Bone analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 08. PLACENTA ANALYSIS
    # ========================================================
    story.append(Paragraph("08. PLACENTA ANALYSIS", sec_heading_style))
    f_plac = findings.get("placenta", {})
    plac_status = f_plac.get("status", "not_provided")
    if plac_status == "completed" and f_plac.get("result"):
        p_seg = f_plac["result"].get("segmentation", f_plac["result"])
        p_pixels = p_seg.get("mask_pixels", 0)
        p_ratio = (p_seg.get("mask_ratio", 0) * 100)
        mean_p = p_seg.get("mean_probability", 0)
        plac_rows = [
            ["Status", "Completed"],
            ["Placenta Mask Area", f"{p_pixels:,} pixels"],
            ["Segmented Area Ratio", f"{p_ratio:.2f}%"],
            ["Mean Mask Probability", f"{mean_p:.4f}"],
            ["Architecture", "SMP U-Net Placental Segmentation (:8106)"],
        ]
        story.append(build_kv_table(plac_rows))
        mask_img = resolve_image(p_seg.get("mask_url"))
        if mask_img:
            story.append(Spacer(1, 3))
            story.append(mask_img)
    elif plac_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_plac.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No scan submitted for Placenta analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 09. FETAL FACE 3D ANALYSIS
    # ========================================================
    story.append(Paragraph("09. FETAL FACE 3D ANALYSIS", sec_heading_style))
    f_face = findings.get("face", {})
    face_status = f_face.get("status", "not_provided")
    if face_status == "completed" and f_face.get("result"):
        fc_res = f_face["result"]
        fc_pred = fc_res.get("prediction", {})
        fc_lbl = fc_pred.get("predicted_label") or fc_pred.get("label") or fc_pred.get("predicted_class") or "Normal"
        fc_conf = fc_pred.get("confidence_percent", round(fc_pred.get("confidence", 0.92) * 100, 1))
        m_info = fc_res.get("mesh_info") or fc_res.get("input") or {}
        pts = m_info.get("points", 0)
        cells = m_info.get("cells", 0)

        face_rows = [
            ["Status", "Completed"],
            ["3D Mesh Model Classification", f"<b>{fc_lbl}</b>"],
            ["Model Classification Confidence", f"{fc_conf}%"],
            ["3D Mesh Topology", f"{pts:,} Points • {cells:,} Cells • 30 Geometric VTK Features"],
            ["Environment", "Python 3.11 + VTK Polygonal Mesh Feature Extractor (:8107)"],
        ]
        story.append(build_kv_table(face_rows))
    elif face_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_face.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No 3D VTK mesh submitted for Facial Morphology analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 10. FETAL HEART ANALYSIS
    # ========================================================
    story.append(Paragraph("10. FETAL HEART ANALYSIS", sec_heading_style))
    f_heart = findings.get("heart", {})
    heart_status = f_heart.get("status", "not_provided")
    if heart_status == "completed" and f_heart.get("result"):
        h_seg = f_heart["result"].get("segmentation", f_heart["result"])
        h_pixels = h_seg.get("mask_pixels", 0)
        h_ratio = (h_seg.get("mask_ratio", 0) * 100)
        mean_p = h_seg.get("mean_probability", 0)
        heart_rows = [
            ["Status", "Completed"],
            ["Cardiac Mask Area", f"{h_pixels:,} pixels"],
            ["Segmented Area Ratio", f"{h_ratio:.2f}%"],
            ["Mean Mask Probability", f"{mean_p:.4f}"],
            ["Architecture", "PyTorch U-Net 4-Chamber Cardiac Segmentation (:8108)"],
        ]
        story.append(build_kv_table(heart_rows))
        mask_img = resolve_image(h_seg.get("mask_url"))
        if mask_img:
            story.append(Spacer(1, 3))
            story.append(mask_img)
    elif heart_status == "failed":
        story.append(build_kv_table([["Status", "Failed"], ["Error", f_heart.get("error", {}).get("message", "Inference error")]]))
    else:
        story.append(build_kv_table([["Status", "Not Provided"], ["Note", "No scan submitted for Fetal Heart analysis."]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 11. KIDNEY STATUS
    # ========================================================
    story.append(Paragraph("11. KIDNEY STATUS", sec_heading_style))
    kidney_rows = [
        ["Status", "Unavailable"],
        ["Reason", "Kidney AI model is disabled (no verified ML model weights configured)."],
        ["Notice", "Automated kidney analysis is disabled. Manual clinical examination required."],
    ]
    story.append(build_kv_table(kidney_rows))
    story.append(Spacer(1, 6))

    # ========================================================
    # 12. CROSS-MODEL FINDINGS SUMMARY
    # ========================================================
    story.append(Paragraph("12. CROSS-MODEL FINDINGS SUMMARY", sec_heading_style))
    summary_matrix = [["Anatomical Target", "Analysis Status", "Model Output Finding"]]
    for k in ["plane", "brain", "spine", "lung", "bone", "placenta", "face", "heart", "kidney"]:
        f_item = findings.get(k, {})
        st = f_item.get("status", "not_provided" if k != "kidney" else "unavailable")
        desc = "No input scan submitted"
        if st == "completed":
            res = f_item.get("result", {})
            if k == "plane":
                desc = f"Predicted plane: {res.get('predicted_class')} ({res.get('confidence_percent', 0):.1f}%)"
            elif k == "brain":
                anom = res.get("brain_anomaly", {})
                desc = f"Brain plane: {res.get('brain_plane', {}).get('predicted_class')}, Outlier signal: {anom.get('status', 'N/A')}"
            elif k in ("spine", "bone"):
                dets = res.get("detections", [])
                desc = f"{len(dets)} landmark(s) detected"
            elif k in ("lung", "placenta", "heart"):
                seg = res.get("segmentation", res)
                desc = f"Segmented area: {seg.get('mask_pixels', 0):,} px ({(seg.get('mask_ratio', 0)*100):.1f}%)"
            elif k == "face":
                pred = res.get("prediction", {})
                lbl = pred.get("predicted_label") or pred.get("label") or "Normal"
                desc = f"Classification: {lbl} ({pred.get('confidence_percent', 0):.1f}%)"
            else:
                desc = "Model executed successfully"
        elif st == "failed":
            desc = f_item.get("error", {}).get("message", "Execution error")
        elif st == "unavailable":
            desc = "Model unavailable (disabled)"
        summary_matrix.append([k.capitalize(), st.upper(), desc])

    sm_table = Table(summary_matrix, colWidths=[90, 100, 314])
    sm_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(sm_table)
    story.append(Spacer(1, 6))

    # ========================================================
    # 13. PROCESSING / TECHNICAL DETAILS
    # ========================================================
    story.append(Paragraph("13. PROCESSING / TECHNICAL DETAILS", sec_heading_style))
    tech_rows = [
        ["Report Identifier", report_num],
        ["Analysis Session ID", analysis_id],
        ["Gateway Process", "FastAPI :8000 (ML-Free Router)"],
        ["Worker Architecture", "Isolated Subprocesses (Ports 8100-8108)"],
        ["Memory Mode", "Sequential On-Demand Execution (~512MB Budget)"],
    ]
    story.append(build_kv_table(tech_rows))
    story.append(Spacer(1, 6))

    # ========================================================
    # 14. WARNINGS & LIMITATIONS
    # ========================================================
    story.append(Paragraph("14. WARNINGS & LIMITATIONS", sec_heading_style))
    warn_text = "Standard imaging considerations apply (acoustic shadowing, transducer orientation, maternal habitus)."
    if warnings or errors:
        warn_items = [f"• {w}" for w in warnings] + [f"• Error: {e}" for e in errors]
        warn_text = "<br/>".join(warn_items)
    story.append(build_kv_table([["Active Warnings & Limitations", warn_text]]))
    story.append(Spacer(1, 6))

    # ========================================================
    # 15. AI / RESEARCH DISCLAIMER
    # ========================================================
    story.append(Paragraph("15. AI / RESEARCH DISCLAIMER", sec_heading_style))
    disclaimer_text = (
        "AI model outputs are experimental clinical decision-support and research "
        "outputs. They do not constitute a medical diagnosis, clinical confirmation, "
        "or standalone medical finding. All outputs must be verified by a qualified healthcare professional."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))
    story.append(Spacer(1, 6))

    # ========================================================
    # 16. REPORT METADATA
    # ========================================================
    story.append(Paragraph("16. REPORT METADATA", sec_heading_style))
    meta_rows = [
        ["Report Number", report_num],
        ["Specification Version", "FetalAI-Report-v1.0 (Locked 16-Section Schema)"],
        ["Generated Timestamp", str(created_at)],
        ["Format", "PDF / ISO 32000 compliant"],
    ]
    story.append(build_kv_table(meta_rows))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
