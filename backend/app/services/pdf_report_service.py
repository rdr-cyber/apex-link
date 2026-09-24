"""PDF report generation service for APEX LINK."""

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ALGORITHM_VERSION
from app.models.case import Case
from app.models.entity import Entity, CaseEntity
from app.models.evidence import Evidence
from app.models.lead import Lead
from app.models.relationship import Relationship
from app.services.graph_service import GraphService
from app.services.report_service import ReportService


def _safe(text: str) -> str:
    """Escape text for PDF rendering."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PDFReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_pdf(self, case_id: uuid.UUID) -> bytes:
        """Generate a professional PDF investigation report."""
        report_service = ReportService(self.db)
        report = await report_service.generate_case_report(case_id)

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak, HRFlowable,
            )
        except ImportError:
            # Fallback: return a simple text-based PDF
            return self._generate_simple_pdf(report)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                                leftMargin=0.75 * inch, rightMargin=0.75 * inch)

        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                                      fontSize=20, spaceAfter=6, textColor=colors.HexColor('#1a1a2e'))
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                         fontSize=12, spaceAfter=12, textColor=colors.HexColor('#555555'))
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading1'],
                                        fontSize=14, spaceBefore=16, spaceAfter=8,
                                        textColor=colors.HexColor('#1a1a2e'))
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                                     fontSize=10, spaceAfter=6, leading=14)
        disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'],
                                           fontSize=9, textColor=colors.HexColor('#888888'),
                                           spaceAfter=4, leading=12)
        label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                      fontSize=9, textColor=colors.HexColor('#666666'))

        # Header
        elements.append(Paragraph("APEX LINK", title_style))
        elements.append(Paragraph("Investigation Analysis Report", subtitle_style))
        elements.append(Paragraph(
            f"Generated: {report['generated_at'][:19]}Z &nbsp;|&nbsp; "
            f"Algorithm: v{report['algorithm_version']} &nbsp;|&nbsp; "
            f"Type: {report['report_type']}",
            label_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        elements.append(Spacer(1, 12))

        # Disclaimer
        elements.append(Paragraph(
            f"<i>{report['disclaimer']}</i>", disclaimer_style
        ))
        elements.append(Spacer(1, 12))

        # Case Summary
        elements.append(Paragraph("1. Case Summary", heading_style))
        cs = report["case_summary"]
        case_data = [
            ["Case Number", cs.get("case_number", "N/A")],
            ["Title", cs.get("title", "N/A")],
            ["Description", cs.get("description", "N/A")],
            ["Category", cs.get("category", "N/A")],
            ["Priority", cs.get("priority", "N/A")],
            ["Status", cs.get("status", "N/A")],
            ["Location", cs.get("location") or "N/A"],
            ["Incident Date", cs.get("incident_date") or "N/A"],
        ]
        t = Table(case_data, colWidths=[2 * inch, 4.5 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Known Entities
        elements.append(Paragraph("2. Known Entities", heading_style))
        elements.append(Paragraph(
            f"Total entities: {report['known_entities']['total']}", body_style
        ))
        if report["known_entities"]["entities"]:
            entity_data = [["Type", "Value", "Confidence", "Observation"]]
            for e in report["known_entities"]["entities"][:30]:
                entity_data.append([
                    e["type"], e["value"],
                    f"{e['confidence']:.0%}", e["observation_type"]
                ])
            t = Table(entity_data, colWidths=[1.2 * inch, 2.5 * inch, 1 * inch, 2 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)
        elements.append(Spacer(1, 12))

        # Key Network Entities
        elements.append(Paragraph("3. Key Network Entities", heading_style))
        elements.append(Paragraph(
            "<i>Network prominence is an analytical indicator and does not establish criminal "
            "responsibility.</i>", disclaimer_style
        ))
        if report["key_network_entities"]["entities"]:
            ke_data = [["Entity", "Type", "Score", "Degree", "Bridge", "Cross-case"]]
            for ke in report["key_network_entities"]["entities"]:
                f = ke.get("factors", {})
                ke_data.append([
                    ke["label"], ke["type"],
                    f"{ke['score']:.1f}",
                    f"{f.get('degree', 0):.0f}",
                    f"{f.get('betweenness', 0):.0f}",
                    f"{f.get('cross_case', 0):.0f}",
                ])
            t = Table(ke_data, colWidths=[1.5 * inch, 1 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 1 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)
        elements.append(Spacer(1, 12))

        # Cross-case Correlations
        elements.append(Paragraph("4. Cross-Case Correlations", heading_style))
        elements.append(Paragraph(
            "<i>Potential cross-case relationships detected by algorithmic analysis. "
            "Requires investigator verification.</i>", disclaimer_style
        ))
        if report["cross_case_correlations"]["leads"]:
            for lead in report["cross_case_correlations"]["leads"]:
                elements.append(Paragraph(
                    f"<b>Score: {lead['score']:.0f}/100 ({lead['priority']})</b><br/>"
                    f"{_safe(lead['explanation'])}<br/>"
                    f"<i>Observation type: {lead['observation_type']}</i>",
                    body_style
                ))
                elements.append(Spacer(1, 6))
        else:
            elements.append(Paragraph("No cross-case correlations detected.", body_style))
        elements.append(Spacer(1, 12))

        # Suspicious Patterns
        elements.append(Paragraph("5. Detected Patterns", heading_style))
        elements.append(Paragraph(
            "<i>Patterns are algorithmic observations requiring human review.</i>",
            disclaimer_style
        ))
        if report["suspicious_patterns"]:
            for p in report["suspicious_patterns"]:
                elements.append(Paragraph(
                    f"<b>{p.get('pattern', 'UNKNOWN')}</b>: "
                    f"{_safe(p.get('description', ''))} "
                    f"(Entity: {_safe(p.get('entity', 'N/A'))})",
                    body_style
                ))
        else:
            elements.append(Paragraph("No suspicious patterns detected.", body_style))
        elements.append(Spacer(1, 12))

        # Evidence Summary
        elements.append(Paragraph("6. Evidence Summary", heading_style))
        es = report["evidence_summary"]
        elements.append(Paragraph(f"Total evidence items: {es['total']}", body_style))
        if es["items"]:
            ev_data = [["Evidence #", "Type", "Filename", "SHA-256 (truncated)", "Observation"]]
            for ev in es["items"][:20]:
                ev_data.append([
                    ev["number"], ev["type"], ev["filename"],
                    ev["integrity_hash"][:16] + "..." if ev["integrity_hash"] else "N/A",
                    ev["observation_type"],
                ])
            t = Table(ev_data, colWidths=[1 * inch, 1 * inch, 1.5 * inch, 1.8 * inch, 1.2 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(t)
        elements.append(Spacer(1, 12))

        # Network Statistics
        elements.append(Paragraph("7. Network Statistics", heading_style))
        ns = report["network_statistics"]
        elements.append(Paragraph(
            f"Total relationships: {ns['total_relationships']}<br/>"
            f"Relationship types: {', '.join(f'{k}: {v}' for k, v in ns.get('relationship_types', {}).items())}",
            body_style
        ))
        elements.append(Spacer(1, 12))

        # Limitations
        elements.append(Paragraph("8. Limitations", heading_style))
        for lim in report.get("limitations", []):
            elements.append(Paragraph(f"• {_safe(lim)}", body_style))
        elements.append(Spacer(1, 12))

        # Footer
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f"APEX LINK — Explainable Criminal Network &amp; Investigation Intelligence Platform<br/>"
            f"Generated by APEX LINK v{report['algorithm_version']} | "
            f"{report['generated_at'][:19]}Z<br/>"
            f"This report is for authorized investigative use only.",
            disclaimer_style
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _generate_simple_pdf(self, report: dict) -> bytes:
        """Fallback: generate a minimal PDF without reportlab."""
        # Simple PDF with raw text
        content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj
<</Length 444>>
stream
BT
/F1 20 Tf
50 750 Td
(APEX LINK Investigation Report) Tj
/F1 12 Tf
0 -30 Td
(Generated: {report['generated_at'][:19]}Z) Tj
0 -20 Td
(Case: {report['case_summary'].get('case_number', 'N/A')}) Tj
0 -20 Td
(Algorithm Version: {report['algorithm_version']}) Tj
0 -40 Td
/F1 10 Tf
(This report requires reportlab for full formatting.) Tj
0 -15 Td
(Install: pip install reportlab) Tj
0 -30 Td
(Full JSON report is also available via /api/v1/reports/case/{report['case_summary'].get('case_number', '')}) Tj
ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000762 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
821
%%EOF"""
        return content.encode("latin-1", errors="replace")
