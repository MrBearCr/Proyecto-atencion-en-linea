# Glosario y entidades

## Términos del dominio
- **Jerarquía (Dep/Grp/Sub)** → Clasificación de 3 niveles para productos: Departamento (Nivel 1), Grupo (Nivel 2), Subgrupo (Nivel 3). Es compartida por inventario, TRA y MBRP.
- **Lista Roja** → Productos no trasladables. Productos que por regla de negocio no deben enviarse entre ciertas sedes en abastecimiento.
- **Quiebre** → Estado donde el stock actual es insuficiente para cubrir los días mínimos proyectados de ventas en el análisis logístico.
- **Sugerencia de Transferencia** → Propuesta automática del sistema (`AbastecimientoService`) de mover stock de una sede origen a una destino.

## Entidades principales
- **Producto** → Representado en la BD por `MA_PRODUCTOS`. Tiene jerarquía asignada y posee dos descripciones (corta y larga).
- **Departamento / Grupo / Subgrupo** → Estructuras jerárquicas almacenadas en `MA_DEPARTAMENTOS`, `MA_GRUPOS`, `MA_SUBGRUPOS`.
- **Cliente** → Entidad objetivo para gestión de ventas y destinatario de las notificaciones masivas de WhatsApp.

## Siglas y nombres internos
- **PAL** → Proyecto de Atención en Línea (o Gestión de Clientes y Logística).
- **TRA** → Transferencias y Rotación de Inventario (módulo para el análisis de rotación de productos).
- **MBRP** → Máximo y Mínimo por Punto de Reorden (módulo de cálculo de niveles óptimos de stock ROP).
- **ROP** → Reorder Point (Punto de reorden).
