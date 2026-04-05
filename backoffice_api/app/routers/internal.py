from fastapi import APIRouter, Header, HTTPException, Request
from datetime import datetime, timezone
import os
import logging
from ..db import fetch_one
from .daily_closure import execute_daily_closure
from ..schemas.daily_closure import DailyClosureExecuteRequest
from ..services.pdf_generator import generate_daily_closure_pdf
from ..services.email_service import send_daily_closure_email

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "change-me-in-production")

@router.post("/daily_closure/auto")
async def auto_daily_closure(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Endpoint interno para ejecutar cierre automático diario.
    Se ejecuta vía cron a las 23:55 VET.
    """
    # Accept either X-API-Key or X-INTERNAL-KEY
    internal_key = request.headers.get("X-INTERNAL-KEY")
    provided_key = x_api_key or internal_key

    if provided_key != INTERNAL_API_KEY:
        raise HTTPException(403, "Invalid API Key")

    # We must find the TREASURY user to attribute the closure creation
    treasury_user = await fetch_one("SELECT id FROM users WHERE alias = 'TREASURY'")
    if not treasury_user:
        raise HTTPException(status_code=500, detail="TREASURY system user not found")

    today = datetime.now(timezone.utc).date()

    try:
        # Prepare auth context for execute_daily_closure
        auth_context = {"user_id": treasury_user["id"], "role": "system"}

        # Exec closure
        payload = DailyClosureExecuteRequest(
            closure_date=today,
            notes="Generado automáticamente por sistema de auto-cierre cron",
            force=False
        )

        try:
            result = await execute_daily_closure(payload=payload, auth=auth_context)
        except HTTPException as he:
            # If it's a conflict (409), the closure already exists for today.
            if he.status_code == 409:
                return {"ok": True, "message": f"Cierre para {today} ya existía."}
            raise he

        # Transform the dict-like asyncpg Record to dict
        result_dict = dict(result)

        # Generate PDF
        pdf_buffer = generate_daily_closure_pdf(result_dict)

        # Guardar PDF en storage (opcional - skipping for now as per instructions)
        pdf_filename = f"cierre_{today}.pdf"

        # Enviar email
        email_sent = await send_daily_closure_email(pdf_buffer, str(today))

        return {
            "ok": True,
            "message": f"Cierre automático ejecutado para {today}",
            "pdf_generated": True,
            "pdf_filename": pdf_filename,
            "email_sent": email_sent
        }
    except Exception as e:
        logger.exception("Error en cierre automático")
        raise HTTPException(500, f"Error en cierre automático: {str(e)}")
