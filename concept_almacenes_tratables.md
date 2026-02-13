# Configuración de Almacenes Tratables (Propuesta Simplificada)

## Concepto
`PAL_ALMACENES_TRATABLES` no es necesariamente una tabla nueva de base de datos, sino el **concepto** de definir qué almacenes se consideran "aptos para venta" en cada sede.

## Problema Actual
Actualmente, el sistema no distingue inteligentemente entre:
1.  **Stock Físico Total**: Todo lo que hay en el sistema (incluyendo garantías, defectuoso, tránsito).
2.  **Stock Tratable (Disponible para Venta)**: Solo lo que está en almacenes principales (ej: 0101, 0301) y listos para facturar.

## Solución Propuesta (Sin Nueva Tabla)
Utilizar la tabla existente `pal_global_settings` para guardar una configuración JSON que defina estas reglas.

### Estructura del JSON en `pal_global_settings`
Clave: `sedes_config`

```json
{
  "Barinas": {
    "descripcion": "Sede Principal Barinas",
    "almacenes_tratables": ["0101", "0102"],  // Solo estos cuentan para "No hay Stock"
    "zona": "Llanos"
  },
  "Cabudare": {
    "descripcion": "Sede Cabudare",
    "almacenes_tratables": ["0301"],         // Solo 0301 cuenta
    "zona": "Centro"
  }
}
```

## Beneficios
1.  **Flexibilidad**: Si mañana crean el almacén "0105 - Contingencia", solo lo agregamos a la lista de Barinas en la UI y listo.
2.  **Sin Migraciones Complejas**: Usamos la infraestructura existente.
3.  **Lógica Clara**: 
    - **Ventas (TRA)**: Global (Todo lo que se facturó).
    - **Quiebre (Stock)**: Local (¿Tengo mercancía en MIS almacenes tratables?).
