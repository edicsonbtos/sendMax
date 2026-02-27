"""
Repositorio: Trust Score de operadores.

Reglas:
  +2  por orden COMPLETADA
  +1  extra si usó un beneficiario guardado (agenda)
  -3  por orden CANCELADA por causa del operador
  Score se clampea entre 0 y 100.

Cada movimiento queda en trust_score_log para auditoría.
"""
from __future__ import annotations

import logging
from decimal import Decimal

import psycopg

from src.db.connection import get_async_conn

logger = logging.getLogger(__name__)

# ── Deltas de puntuación ──────────────────────────────────────────────────────
DELTA_ORDER_COMPLETED     = Decimal("2")
DELTA_SAVED_BENEFICIARY   = Decimal("1")   # extra si usó un contacto guardado
DELTA_ORDER_CANCELLED     = Decimal("-3")

SCORE_MIN = Decimal("0")
SCORE_MAX = Decimal("100")


async def update_trust_score(
    user_id: int,
    delta: Decimal,
    reason: str,
    ref_order_public_id: int | None = None,
    ref_beneficiary_id: int | None = None,
) -> Decimal:
    """
    Aplica delta al trust_score del usuario de forma atómica.
    Score se clampea entre 0 y 100.
    Inserta un registro en trust_score_log para auditoría.
    Retorna el score resultante.
    """
    async with get_async_conn() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                # UPDATE atómico con clamp
                await cur.execute(
                    """
                    UPDATE users
                    SET trust_score = GREATEST(%s, LEAST(%s, trust_score + %s)),
                        trust_score_updated_at = now()
                    WHERE id = %s
                    RETURNING trust_score;
                    """,
                    (float(SCORE_MIN), float(SCORE_MAX), float(delta), user_id),
                )
                row = await cur.fetchone()
                new_score = Decimal(str(row[0])) if row else SCORE_MIN

                # Log de auditoría
                await cur.execute(
                    """
                    INSERT INTO trust_score_log
                        (user_id, delta, score_after, reason, ref_order_public_id, ref_beneficiary_id)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (user_id, float(delta), float(new_score), reason,
                     ref_order_public_id, ref_beneficiary_id),
                )

    logger.info(
        "Trust score updated: user_id=%s delta=%+.1f reason=%s score_after=%.2f",
        user_id, float(delta), reason, float(new_score),
    )
    return new_score


async def get_trust_score(user_id: int) -> Decimal:
    """Obtiene el trust score actual del usuario."""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT trust_score FROM users WHERE id = %s LIMIT 1;",
                (user_id,),
            )
            row = await cur.fetchone()
            return Decimal(str(row[0])) if row and row[0] is not None else Decimal("50")
