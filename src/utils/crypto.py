"""
Funciones de criptografía para el bot.
Compatible con backoffice_api (mismo algoritmo bcrypt).
"""

import bcrypt


def get_password_hash(password: str) -> str:
    """
    Hash password con bcrypt.
    Compatible con verify_password del backoffice.
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica password contra hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
