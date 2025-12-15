# Sistema de Permisos Granulares - Casapro Nexus

## Overview del Sistema

El sistema implementa un control de acceso granular basado en **módulos** y **acciones específicas**, permitiendo un control preciso sobre lo que cada usuario puede hacer en la aplicación.

## Arquitectura de Permisos

### 1. Estructura Base

Los permisos se organizan en una jerarquía de tres niveles:

```
MÓDULO.ACCIÓN
```

Donde:
- **MÓDULO**: Área funcional del sistema (RI, MBRP, STOCK, etc.)
- **ACCIÓN**: Operación específica dentro del módulo (ver, exportar, editar, etc.)

### 2. Tablas de Base de Datos

- **pal_permisos**: Catálogo de todos los permisos disponibles
- **pal_roles**: Definición de roles del sistema
- **pal_usuarios**: Información de usuarios
- **pal_usuarios_permisos**: Asignación directa de permisos a usuarios
- **pal_roles_permisos**: Asignación de permisos a roles
- **pal_usuarios_roles**: Asignación de roles a usuarios
- **pal_usuarios_modulos**: Módulos habilitados por usuario

## Módulos y Permisos Disponibles

### 📈 TRA (Rotación de Inventario)
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `tra.ver` | Ver datos de rotación | Acceso al módulo RI y visualización de datos |
| `tra.exportar` | Exportar reportes RI | Generar descargas en Excel/CSV |
| `tra.ver_costo_utilidad` | Ver costo y utilidad | Acceso a información financiera sensible |

### 📉 MBRP (Movimiento de Baja Rotación)
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `mbrp.ver` | Ver análisis de baja rotación | Acceso al módulo MBRP |
| `mbrp.exportar` | Exportar reportes MBRP | Generar descargas en Excel/CSV |
| `mbrp.ver_costo_utilidad` | Ver costo y utilidad | Acceso a información financiera sensible |

### 📎 STOCK (Gestión de Inventario)
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `stock.ver` | Ver alertas de stock | Acceso a módulo de alertas |
| `stock.editar` | Modificar configuraciones | Editar umbrales y configuraciones |
| `stock.exportar` | Exportar reportes de stock | Generar descargas en Excel/CSV |
| `stock.ver_costo_utilidad` | Ver costo y utilidad | Acceso a información financiera sensible |

### 📨 MENSAJERÍA (WhatsApp)
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `mensajes.ver` | Ver mensajes | Acceso al historial de mensajes |
| `mensajes.crear` | Crear mensajes | Redactar nuevos mensajes |
| `mensajes.enviar` | Enviar mensajes | Ejecutar envío masivo |
| `mensajes.eliminar` | Eliminar mensajes | Borrar mensajes del historial |
| `mensajes.configurar` | Configurar plantillas | Gestionar plantillas de mensaje |

### 📊 ESTADÍSTICAS
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `estadisticas.ver` | Ver gráficos y reportes | Acceso a dashboard estadístico |
| `estadisticas.exportar` | Exportar reportes | Generar descargas de estadísticas |

### 📅 CALENDARIO
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `calendario.ver` | Ver eventos | Acceso al calendario |
| `calendario.crear` | Crear eventos | Agendar nuevos eventos |
| `calendario.editar` | Editar eventos | Modificar eventos existentes |
| `calendario.eliminar` | Eliminar eventos | Borrar eventos |

### 🔓 ADMINISTRACIÓN
| Permiso | Descripción | Funcionalidad |
|---------|-------------|---------------|
| `admin.usuarios` | Gestionar usuarios | Crear, editar, desactivar usuarios |
| `admin.roles` | Gestionar roles | Crear y modificar roles |
| `admin.permisos` | Gestionar permisos | Administrar sistema de permisos |
| `admin.sistema` | Configuración general | Acceso a configuración avanzada |
| `admin.auditoria` | Ver logs de auditoría | Acceso a registro de actividades |

## Roles Predefinidos

### Administrador
- **Acceso completo**: Todos los permisos de todos los módulos
- **Función**: Administración total del sistema

###  Supervisor
- **Permisos**: Acceso completo a RI, MBRP, STOCK (incluyendo costos)
- **Función**: Supervisión de operaciones y análisis financiero

###  Analista
- **Permisos**: RI, MBRP, STOCK (solo visualización y exportación)
- **Función**: Análisis de datos sin acceso a información financiera sensible

###  Operador Stock
- **Permisos**: STOCK (ver y editar configuraciones) -- EN DESARROLLO
- **Función**: Gestión diaria de inventario

###  Mensajería
- **Permisos**: MENSAJERÍA (ver, crear, enviar) -- EN DESARROLLO 
- **Función**: Comunicación con clientes

###  Consulta 
- **Permisos**: Solo visualización de todos los módulos
- **Función**: Consulta de información sin capacidad de modificación


### Obtener Permisos de Usuario


## Flujo de Autorización

### 1. Autenticación
- Usuario inicia sesión con credenciales
- Sistema valida contraseña y estado de cuenta
- Se crea sesión con token seguro

### 2. Carga de Permisos
- Sistema carga módulos habilitados para el usuario
- Carga permisos directos y por roles
- Almacena en caché para rendimiento

### 3. Verificación en Tiempo Real
- Cada acción solicita verificación de permiso
- Sistema valida: módulo habilitado + permiso específico
- Registra intentos en auditoría

### 4. Auditoría
- Todas las verificaciones de permisos se registran
- Incluye usuario, acción, resultado y timestamp
- Facilita trazabilidad y cumplimiento

## Características de Seguridad

### 🔐 Cifrado
- Contraseñas hasheadas con bcrypt (12 rounds)
- Tokens de sesión con URL-safe random strings
- Datos sensibles cifrados con Fernet

### ⏰ Gestión de Sesiones
- Duración: 8 horas por defecto
- Expiración automática por inactividad
- Logout explícito con registro en auditoría

### 🚫 Bloqueo de Cuentas
- Máximo 5 intentos fallidos
- Bloqueo temporal de 15 minutos
- Reset automático al ingresar correctamente

### 📝 Registro Completo
- Auditoría de accesos y acciones
- Registro de cambios de permisos
- Logs de modificaciones críticas


## Configuración y Mantenimiento

### Agregar Nuevos Permisos
1. Insertar en `pal_permisos`
2. Asignar a roles correspondientes
3. Actualizar código de UI para verificar nuevo permiso

### Modificar Roles
1. Editar asignaciones en `pal_roles_permisos`
2. Limpiar caché de usuarios afectados
3. Verificar funcionamiento correcto

### Auditoría de Permisos
```sql
-- Ver permisos de un usuario específico
SELECT 
    u.username,
    p.modulo,
    p.codigo,
    p.descripcion
FROM pal_usuarios u
JOIN pal_usuarios_permisos up ON u.id = up.usuario_id
JOIN pal_permisos p ON up.permiso_id = p.id
WHERE u.username = 'usuario_ejemplo';
```

## Mejores Prácticas

### ✅ Recomendaciones
1. **Principio de menor privilegio**: Asignar solo permisos necesarios
2. **Revisión periódica**: Evaluar permisos asignados trimestralmente
3. **Roles predefinidos**: Usar roles en lugar de permisos individuales
4. **Auditoría activa**: Revisar logs de acceso regularmente

### ❌ Restricciones
1. No compartir credenciales entre usuarios
2. No asignar permisos de administrador innecesariamente
3. No modificar directamente tablas de permisos
4. No deshabilitar logs de auditoría

## Soporte y Troubleshooting

### Problemas Comunes

**"Permiso denegado" inesperado:**
1. Verificar que el módulo esté habilitado para el usuario
2. Confirmar asignación directa o por rol
3. Limpiar caché de permisos del usuario

**Rendimiento lento:**
1. Revisar tamaño de caché de permisos
2. Optimizar consultas de carga inicial
3. Considerar caché por módulo

**Auditoría incompleta:**
1. Verificar conexión con base de datos
2. Confirmar permisos de escritura en tablas de auditoría
3. Revisar configuración de logging

---

*Este documento describe el sistema de permisos granulares de Casapro Nexus, diseñado para proporcionar control de acceso preciso y auditoría completa en un entorno empresarial seguro.*