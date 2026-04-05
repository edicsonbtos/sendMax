from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO

def generate_daily_closure_pdf(closure_data: dict) -> BytesIO:
    """
    Genera PDF del cierre diario.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title = Paragraph(f"<b>REPORTE DE CIERRE DIARIO</b><br/>SendMax Financial", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))

    subtitle = Paragraph(f"Fecha: {closure_data['closure_date']}", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.2*inch))

    # Resumen Ejecutivo
    summary_data = [
        ['RESUMEN EJECUTIVO', ''],
        ['Total Órdenes', str(closure_data.get('total_orders_count', 0))],
        ['Volumen Transaccionado', f"${float(closure_data.get('total_volume_origin', 0)):,.2f}"],
        ['Ganancia Estimada', f"{float(closure_data.get('total_profit_usdt', 0)):,.2f} USDT"],
        ['Ganancia Real', f"{float(closure_data.get('total_profit_real', 0)):,.2f} USDT"],
        ['Tasa de Éxito', f"{float(closure_data.get('success_rate', 0)):.1f}%"],
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))

    # Mejores Operadores
    best_op = Paragraph(f"<b>Mejor Operador:</b> {closure_data.get('best_operator_alias') or 'N/A'}", styles['Normal'])
    elements.append(best_op)
    elements.append(Spacer(1, 0.1*inch))

    # Países destacados
    best_route = Paragraph(
        f"<b>Ruta Principal:</b> {closure_data.get('best_origin_country') or 'N/A'} -> {closure_data.get('best_dest_country') or 'N/A'}",
        styles['Normal']
    )
    elements.append(best_route)
    elements.append(Spacer(1, 0.3*inch))

    # Retiros Pendientes
    withdrawals = Paragraph(
        f"<b>Retiros Pendientes:</b> {closure_data.get('pending_withdrawals_count', 0)} (Total: {float(closure_data.get('pending_withdrawals_amount', 0)):.2f} USDT)",
        styles['Normal']
    )
    elements.append(withdrawals)
    elements.append(Spacer(1, 0.3*inch))

    # Footer
    footer = Paragraph(
        f"<i>Generado automáticamente por SendMax Financial System</i>",
        styles['Normal']
    )
    elements.append(Spacer(1, 0.5*inch))
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer
