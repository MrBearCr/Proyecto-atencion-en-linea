"""
Configuración básica de Alembic para el subproyecto `posmigra`.

La URL de base de datos por defecto es un SQLite local (`posmigra_dev.db`),
pero en entornos reales se recomienda establecer la variable de entorno
`POSMIGRA_DB_URL` apuntando a la base de datos que replica producción.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Esta configuración se genera a partir de alembic.ini
config = context.config

# Permite sobreescribir la URL desde variable de entorno
db_url = os.getenv("POSMIGRA_DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# En este punto aún no definimos modelos declarativos específicos;
# cuando el backend nuevo esté listo, se podrán importar aquí.
target_metadata = None


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


