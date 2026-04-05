import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import logging

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@sendmax.com")

async def send_daily_closure_email(pdf_buffer, closure_date: str):
    """
    Envía email con PDF del cierre diario.
    """
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP credentials not configured. Skipping email sending.")
        return False

    message = MIMEMultipart()
    message["From"] = SMTP_USER
    message["To"] = ADMIN_EMAIL
    message["Subject"] = f"Cierre Diario SendMax - {closure_date}"

    # Cuerpo del email
    body = f"""
    Hola Admin,

    Adjunto encontrarás el reporte de cierre financiero del día {closure_date}.

    Este email fue generado automáticamente por el sistema.

    Saludos,
    SendMax Financial System
    """
    message.attach(MIMEText(body, "plain"))

    # Adjuntar PDF
    pdf_attachment = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
    pdf_attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"cierre_{closure_date}.pdf"
    )
    message.attach(pdf_attachment)

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True
        )
        logger.info(f"Daily closure email sent successfully for {closure_date}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
