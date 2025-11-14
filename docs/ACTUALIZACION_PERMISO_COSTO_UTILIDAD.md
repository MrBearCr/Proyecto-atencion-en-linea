# Guía de Actualización: Permiso Ver Costo y Utilidad

**Versión**: 1.0.2 (Sin publicar)  
**Fecha**: 2025-01-14  
**Tipo**: Actualización de funcionalidad  

---

## 📋 Resumen

Esta actualización agrega un nuevo permiso granular `ver_costo_utilidad` que controla qué usuarios pueden visualizar información sensible de costos y márgenes de utilidad en los reportes de Excel exportados desde los módulos **TRA**, **MBRP** y **Stock**.

## 🎯 ¿Qué cambia?

### Antes ✗
- **Todos los usuarios** que podían exportar reportes veían la misma información
- No había control sobre quién podía ver costos y utilidades
- Información financiera sensible expuesta a todos

### Después ✓
- **Control granular** por usuario/rol sobre visualización de costos
- Columnas **condicionales** en Excel: `Precio`, `Costo`, `Utilidad %`
- Solo usuarios con permiso `ver_costo_utilidad` ven estas columnas
- Mayor **seguridad** y cumplimiento de políticas empresariales

---

## 🔧 Cambios Técnicos

### 1. **Nuevos Permisos**
Se agregaron 3 nuevos permisos al sistema:

| Código | Módulo | Descripción |
|--------|--------|-------------|
| `tra.ver_costo_utilidad` | TRA | Ver costo y utilidad en reportes TRA |
| `mbrp.ver_costo_utilidad` | MBRP | Ver costo y utilidad en reportes MBRP |
| `stock.ver_costo_utilidad` | STOCK | Ver costo y utilidad en reportes Stock |

### 2. **Columnas Agregadas en Excel**
Cuando el usuario **tiene permiso**, los reportes incluyen:

| Columna | Origen | Descripción |
|---------|--------|-------------|
| **Precio** | `MA_PRODUCTOS.n_precio1` | Precio de venta del producto |
| **Costo** | `MA_PRODUCTOS.n_costoact` | Costo actual del producto |
| **Utilidad %** | *Calculado* | `((precio - costo) / costo) * 100` |

### 3. **Módulos Afectados**
- ✅ **TRA (Rotación y Abastecimiento)**: Exportación `reporte_tra_YYYYMMDD_HHMMSS.xlsx`
- ✅ **MBRP (Baja Rotación)**: Exportación `reporte_mbrp_YYYYMMDD_HHMMSS.xlsx`
- ⏳ **Stock (Alertas)**: Pendiente de implementación

### 4. **Archivos Modificados**

```
pal/
├── infrastructure/
│   └── database.py              # ✏️ Queries SQL con precio/costo
├── services/
│   └── exports.py               # ✏️ Exportaciones con columnas condicionales
└── app.py                       # ✏️ Paso de permisos a funciones de exportación

docs/
└── migrations/
    └── 001_agregar_permiso_costo_utilidad.sql  # 🆕 Script de migración SQL
```

---

## 📦 Pasos de Instalación

### 🆕 **IMPORTANTE: ¿Instalación Nueva o Actualización?**

✅ **Si estás instalando PAL desde CERO** (BD nueva):
- **NO necesitas ejecutar el script de migración**
- El sistema creará automáticamente todos los permisos al iniciar por primera vez
- Los roles Administrador y Supervisor ya tendrán `ver_costo_utilidad` asignado
- 🚀 **Solo inicia la app y listo**

⚠️ **Si estás ACTUALIZANDO** una instalación existente de PAL:
- **SÍ necesitas ejecutar el script de migración** (Paso 1 abajo)
- Esto agregará los nuevos permisos a tu BD existente

---

### **Paso 1: Ejecutar Migración SQL** (⚠️ Solo para actualizaciones)

1. Abrir **SQL Server Management Studio (SSMS)**
2. Conectarse a la base de datos del sistema PAL
3. Abrir el archivo: `docs/migrations/001_agregar_permiso_costo_utilidad.sql`
4. **IMPORTANTE**: Modificar línea 8 con el nombre de tu base de datos:
   ```sql
   USE [tu_base_de_datos]; -- CAMBIAR POR EL NOMBRE DE TU BD
   ```
5. Ejecutar el script completo (`F5`)
6. Verificar salida:
   ```
   Paso 1/3: Agregando permisos a pal_permisos...
     ✓ Permiso tra.ver_costo_utilidad creado
     ✓ Permiso mbrp.ver_costo_utilidad creado
     ✓ Permiso stock.ver_costo_utilidad creado
   
   Paso 2/3: Asignando permisos al rol Administrador...
     ✓ Permiso TRA asignado a Administrador
     ✓ Permiso MBRP asignado a Administrador
     ✓ Permiso STOCK asignado a Administrador
   
   Paso 3/3: Asignando permisos al rol Supervisor (opcional)...
     ✓ Permiso TRA asignado a Supervisor
     ✓ Permiso MBRP asignado a Supervisor
     ✓ Permiso STOCK asignado a Supervisor
   
   Migración 001 completada exitosamente ✓
   ```

### **Paso 2: Actualizar Código de la Aplicación**

1. Hacer pull/descargar los últimos cambios del repositorio
2. Reiniciar la aplicación PAL

**No se requieren cambios adicionales** - el código ya está preparado para detectar los nuevos permisos automáticamente.

---

## 🎛️ Configuración de Permisos

### **Por Defecto**
El script de migración asigna automáticamente el permiso a:
- ✅ Rol **Administrador** (todos los módulos)
- ✅ Rol **Supervisor** (todos los módulos)

### **Asignación Manual**

#### **Opción A: Por Rol (Recomendado)**
Ideal para grupos de usuarios con las mismas políticas de acceso.

```sql
-- Asignar permiso TRA al rol "Gerente Ventas"
DECLARE @rol_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Gerente Ventas');
DECLARE @perm_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.ver_costo_utilidad');

INSERT INTO pal_roles_permisos (rol_id, permiso_id)
VALUES (@rol_id, @perm_id);
```

#### **Opción B: Por Usuario Individual**
Para casos específicos donde un usuario necesita acceso particular.

```sql
-- Asignar permiso MBRP directamente a usuario "juan.perez"
DECLARE @usuario_id INT = (SELECT id FROM pal_usuarios WHERE username = N'juan.perez');
DECLARE @perm_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'mbrp.ver_costo_utilidad');

INSERT INTO pal_usuarios_permisos (usuario_id, permiso_id, concedido)
VALUES (@usuario_id, @perm_id, 1); -- concedido=1 para dar acceso
```

#### **Opción C: Desde la Interfaz de PAL (Futuro)**
_Próximamente: Panel de administración de permisos en la app_

---

## 🧪 Pruebas de Verificación

### **Test 1: Usuario CON permiso**
1. Iniciar sesión con usuario que tenga rol **Administrador** o **Supervisor**
2. Ir al módulo **TRA**
3. Exportar reporte a Excel
4. Abrir archivo y verificar que existen las columnas:
   - ✅ **Precio** (columna I)
   - ✅ **Costo** (columna J)
   - ✅ **Utilidad %** (columna K)

### **Test 2: Usuario SIN permiso**
1. Crear usuario de prueba con rol **Consulta** (sin permisos adicionales)
2. Iniciar sesión con ese usuario
3. Ir al módulo **TRA**
4. Exportar reporte a Excel
5. Abrir archivo y verificar que **NO existen** las columnas de costo/utilidad
   - ✅ Columnas terminan en **Representación %** (columna H)

### **Test 3: Cálculo de Utilidad**
Verificar que el cálculo es correcto:
1. Abrir reporte con permisos
2. Seleccionar un producto con:
   - Precio = 150
   - Costo = 100
3. Verificar que **Utilidad % = 50.00**
   - Fórmula: `((150 - 100) / 100) * 100 = 50%`

---

## ❓ Preguntas Frecuentes (FAQ)

### **¿Qué pasa si ejecuto el script SQL dos veces?**
✅ **Seguro** - El script verifica existencia antes de insertar. Mensajes informativos:
```
ℹ Permiso tra.ver_costo_utilidad ya existe
ℹ Permiso TRA ya asignado a Administrador
```

### **¿Puedo revocar el permiso después?**
✅ **Sí** - Dos formas:
```sql
-- Opción 1: Eliminar de rol
DELETE FROM pal_roles_permisos 
WHERE rol_id = @rol_id AND permiso_id = @perm_id;

-- Opción 2: Denegar a usuario específico (override)
UPDATE pal_usuarios_permisos 
SET concedido = 0 
WHERE usuario_id = @usuario_id AND permiso_id = @perm_id;
```

### **¿Afecta el rendimiento de las exportaciones?**
✅ **Impacto mínimo** - Los campos `n_precio` y `n_costoact` ya se traen en el query principal. Solo se agregan 3 columnas al Excel si el usuario tiene permiso.

### **¿Qué pasa con usuarios que tenían acceso antes?**
⚠️ **Cambio de comportamiento** - Después de la actualización:
- Solo roles **Administrador** y **Supervisor** verán costos por defecto
- Otros roles (Analista, Consulta, etc.) **NO verán** las nuevas columnas
- Si necesitas que otros roles tengan acceso, asígnalo manualmente

### **¿Los datos de costo son históricos o actuales?**
📊 **Actuales** - Se usa `n_costoact` (costo actual) de `MA_PRODUCTOS`. No se guardan costos históricos por transacción.

---

## 🚨 Troubleshooting

### **Problema**: Script SQL falla con "Invalid object name 'pal_permisos'"
**Causa**: Las tablas de seguridad no existen  
**Solución**: Ejecutar primero `ensure_security_tables()` desde la app o script de creación de tablas

### **Problema**: Columnas no aparecen aunque el usuario tiene el rol correcto
**Causa**: Cache de permisos no actualizado  
**Solución**: 
1. Cerrar completamente la aplicación PAL
2. Reiniciar
3. Iniciar sesión nuevamente

### **Problema**: Utilidad % muestra 0 en todos los productos
**Causa**: Campo `n_costoact` es NULL o 0 en `MA_PRODUCTOS`  
**Solución**: 
1. Verificar datos en BD:
   ```sql
   SELECT TOP 10 C_CODIGO, n_precio1, n_costoact 
   FROM MA_PRODUCTOS 
   WHERE n_costoact IS NULL OR n_costoact = 0;
   ```
2. Actualizar costos en sistema origen (ICH/ERP)

---

## 📞 Soporte

**¿Problemas con la actualización?**
1. Revisar logs en `logs/pal_YYYYMMDD.log`
2. Verificar permisos en BD con queries de verificación
3. Contactar al administrador del sistema

---

## 📝 Notas Adicionales

- Esta actualización **NO requiere** reinstalación completa de la app
- **Compatibilidad**: Python 3.8+, SQL Server 2016+
- **Rollback**: Si necesitas revertir, ejecutar:
  ```sql
  -- Eliminar permisos
  DELETE FROM pal_permisos 
  WHERE codigo LIKE N'%.ver_costo_utilidad';
  ```

---

**Última actualización**: 2025-01-14  
**Versión del documento**: 1.0
