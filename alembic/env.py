from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import create_engine, pool

from dotenv import load_dotenv

# Carga variables desde .env (en la raíz del proyecto)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definido en .env")

# Alembic Config object (lee alembic.ini)
config = context.config

# Configura logging desde alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Si más adelante usas autogenerate, aquí pondremos metadata.
target_metadata = None


def run_migrations_offline() -> None:
    """
    Modo offline:
    - No abre conexión real a la DB.
    - Genera SQL usando solo la URL.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online:
    - Conecta a Neon usando DATABASE_URL desde .env
    """
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()