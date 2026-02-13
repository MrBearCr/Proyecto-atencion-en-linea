# Plan de Migración y Transformación: Módulo Stock a "Quiebre de Stock"

## Objetivo
Transformar el módulo de Stock actual (obsoleto) en un nuevo módulo de "Quiebre de Stock", integrando lógica del módulo RI (TRA) y añadiendo alertas visuales persistentes.

## Estado Actual 
- El módulo de Stock actual (`pal/services/stock`) dejará de utilizarse en su formato presente.
- Existe lógica de detección de quiebres de stock dispersa (principalmente en RI/TRA).
- Se requiere un sistema de alertas proactivo.

## Estrategia de Implementación

### Fase 1: Depuración y Preparación
- [ ] Comentar lógica obsoleta en el módulo de Stock actual (`pal/services/stock`).
- [ ] Identificar y aislar la lógica de "rompimiento de stock" en RI (TRA) (`pal/services/tra`).

### Fase 2: Implementación de Lógica "Quiebre de Stock"
- [ ] Implementar análisis multi-sede. **Regla Clave**: Un quiebre debe evaluarse en contexto. Puede que un producto "rompa stock" en una sede (ej. 0101) pero se venda normalmente en otra (ej. 0301). El sistema debe ser capaz de diferenciar o, más importante, alertar. 
    - *Hipótesis*: La alerta debe saltar si hay **Venta Perdida** real (demanda > stock disponible total o local crítico).

### Fase 3: Sistema de Alertas (Popup)
- [ ] Implementar worker/checks de fondo que monitoreen quiebres.
- [ ] Crear componente de UI (Popup insistente).

### Registro de Tests y Avance
- **Sesión 1**: Inicio de migración. Creación de plan.

## Notas Técnicas
- Archivos clave: `pal/services/stock`, `pal/services/tra`.
