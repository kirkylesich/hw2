from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re


def markdown_to_reportlab(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = text.replace('&', '&amp;').replace('<b>', '<b>').replace('</b>', '</b>').replace('<i>', '<i>').replace('</i>', '</i>')
    return text


def generate_pdf(title: str, summary_text: str, output_path: str) -> None:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#1a1a1a',
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='DejaVuSans-Bold'
    )
    
    heading2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=18,
        textColor='#1a1a1a',
        spaceAfter=12,
        spaceBefore=12,
        alignment=TA_LEFT,
        fontName='DejaVuSans-Bold'
    )
    
    heading3_style = ParagraphStyle(
        'Heading3',
        parent=styles['Heading3'],
        fontSize=14,
        textColor='#1a1a1a',
        spaceAfter=10,
        spaceBefore=10,
        alignment=TA_LEFT,
        fontName='DejaVuSans-Bold'
    )
    
    heading4_style = ParagraphStyle(
        'Heading4',
        parent=styles['Heading4'],
        fontSize=12,
        textColor='#1a1a1a',
        spaceAfter=8,
        spaceBefore=8,
        alignment=TA_LEFT,
        fontName='DejaVuSans-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        textColor='#333333',
        spaceAfter=8,
        alignment=TA_LEFT,
        fontName='DejaVuSans',
        leading=14
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['BodyText'],
        fontSize=11,
        textColor='#333333',
        spaceAfter=6,
        alignment=TA_LEFT,
        fontName='DejaVuSans',
        leading=14,
        leftIndent=20,
        bulletIndent=10
    )
    
    title_para = Paragraph(title, title_style)
    story.append(title_para)
    story.append(Spacer(1, 0.2 * inch))
    
    lines = summary_text.split('\n')
    for line in lines:
        line = line.rstrip()
        
        if not line.strip():
            story.append(Spacer(1, 0.1 * inch))
            continue
        
        if line.startswith('### '):
            text = markdown_to_reportlab(line[4:])
            story.append(Paragraph(text, heading3_style))
        elif line.startswith('#### '):
            text = markdown_to_reportlab(line[5:])
            story.append(Paragraph(text, heading4_style))
        elif line.startswith('## '):
            text = markdown_to_reportlab(line[3:])
            story.append(Paragraph(text, heading2_style))
        elif line.startswith('# '):
            text = markdown_to_reportlab(line[2:])
            story.append(Paragraph(text, heading2_style))
        elif line.startswith('- ') or line.startswith('* '):
            text = markdown_to_reportlab(line[2:])
            story.append(Paragraph(f'• {text}', bullet_style))
        elif re.match(r'^\d+\.\s', line):
            text = markdown_to_reportlab(re.sub(r'^\d+\.\s', '', line))
            num = re.match(r'^(\d+)\.\s', line).group(1)
            story.append(Paragraph(f'{num}. {text}', bullet_style))
        else:
            text = markdown_to_reportlab(line)
            story.append(Paragraph(text, body_style))
    
    doc.build(story)
