# Alembic en `posmigra`

Este directorio contiene la configuración de migraciones para el subproyecto
de migración.

## Uso básico

Desde la carpeta `posmigra/`:

```bash
poetry run alembic revision -m "descripcion_cambio"
poetry run alembic upgrade head
```

Por defecto se usa una base de datos SQLite local (`posmigra_dev.db`).
Para apuntar a otra base de datos, define la variable de entorno
`POSMIGRA_DB_URL` antes de ejecutar Alembic.


