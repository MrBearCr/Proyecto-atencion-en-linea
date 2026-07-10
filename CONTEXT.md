# Contexto del Proyecto

Este archivo define el contexto del proyecto para ser cargado al arrancar. Referencia a la documentación de contexto organizada en `docs/contexto/`.

## Documentación de Contexto

- **Arquitectura** → @docs/contexto/arquitectura.md
- **Convenciones** → @docs/contexto/convenciones.md
- **Decisiones** → @docs/contexto/decisiones.md
- **Glosario** → @docs/contexto/glosario.md
- **Flujo de trabajo** → @docs/contexto/flujo-de-trabajo.md
- **Errores conocidos** → @docs/contexto/errores-conocidos.md

## Resumen del Proyecto

Aplicación de escritorio en Python (Tkinter) para gestionar clientes, monitorear inventario (Stock/TRA/MBRP) y enviar notificaciones por WhatsApp (Graph API), con SQL Server como backend.

## Estructura Principal

- `app.py` - Punto de entrada y orquestación
- `pal/core/` - Funcionalidad central (sesión, credenciales, errores, auditoría)
- `pal/services/` - Lógica de negocio (stock, tra, mbrp, filtros, envíos, cache)
- `pal/infrastructure/` - Acceso a datos (database.py)
- `pal/ui/` - Interfaz gráfica (header, sidebar, splash, tabs)

## Documentación Adicional

- `README.md` - Documentación general
- `docs/README.md` - Documentación unificada
- `docs/arquitectura/` - Arquitectura técnica detallada
- `docs/configuracion/` - Configuración del sistema
