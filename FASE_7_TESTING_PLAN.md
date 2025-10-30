# 🧪 Fase 7: Testing y Refinamiento
## Plan Detallado de Pruebas del Sistema de Usuarios y Privilegios

**Fecha**: 2025-10-29  
**Estado**: En Ejecución  
**Tiempo Estimado**: 2-3 días

---

## 📋 Requisitos de la Fase 7

Según el plan del proyecto, Fase 7 debe incluir:

1. ✅ Pruebas de seguridad
2. ✅ Pruebas de permisos
3. ✅ Pruebas de roles
4. ✅ Ajustes y correcciones

---

## 🎯 Estrategia de Testing

### Nivel 1: Pruebas Unitarias (1 día)
- Validación de componentes individuales
- Funciones de hashing y verificación de passwords
- Lógica de permisos y roles

### Nivel 2: Pruebas de Integración (1 día)
- Flujo completo de login/logout
- Verificación de sesiones
- Acceso a módulos según permisos

### Nivel 3: Pruebas de Seguridad (1 día)
- Ataques comunes (SQL injection, XSS)
- Validación de tokens
- Expiración de sesiones

---

## 📊 Matriz de Pruebas

### A. PRUEBAS DE AUTENTICACIÓN (AuthManager)

#### A1. Login Válido
```
Escenario: Usuario con credenciales correctas
Input: username="admin", password="Admin123!"
Expected: {success: True, token: <token>, user: {id, username}}
Status: [ ] Completado
```

#### A2. Login Inválido - Password Incorrecto
```
Escenario: Password equivocado
Input: username="admin", password="WrongPassword"
Expected: {success: False, message: "Usuario o contraseña inválidos"}
Status: [ ] Completado
```

#### A3. Login Inválido - Usuario No Existe
```
Escenario: Usuario que no existe
Input: username="noexiste", password="algo"
Expected: {success: False, message: "Usuario o contraseña inválidos"}
Status: [ ] Completado
```

#### A4. Bloqueo Temporal por Intentos
```
Escenario: 5 intentos fallidos consecutivos
Input: 5 logins con password incorrecto
Expected: Usuario bloqueado por 15 minutos
Verificar: Campo bloqueado_hasta en BD
Status: [ ] Completado
```

#### A5. Verificación de Sesión
```
Escenario: Token válido
Input: token válido desde login
Expected: Retorna datos del usuario
Status: [ ] Completado
```

#### A6. Sesión Expirada
```
Escenario: Token expirado (>8 horas)
Input: token con fecha_expiracion < ahora
Expected: Retorna None (sesión inválida)
Status: [ ] Completado
```

#### A7. Hash de Password
```
Escenario: Password se guarda con hash
Input: password="Test123!"
Verificar: En BD está hasheado con bcrypt, no texto plano
Status: [ ] Completado
```

#### A8. Logout
```
Escenario: Cerrar sesión activa
Input: token válido
Expected: Token marcado como inactivo (activa=0)
Status: [ ] Completado
```

---

### B. PRUEBAS DE AUTORIZACIÓN (PermissionsManager)

#### B1. Módulo Habilitado
```
Escenario: Usuario con módulo habilitado
Input: usuario_id=2, modulo="TRA", habilitado=1
Expected: modulo_habilitado() retorna True
Status: [ ] Completado
```

#### B2. Módulo No Habilitado
```
Escenario: Usuario sin acceso a módulo
Input: usuario_id=2, modulo="ADMIN", habilitado=0
Expected: modulo_habilitado() retorna False
Status: [ ] Completado
```

#### B3. Permiso Directo - Concedido
```
Escenario: Permiso directo asignado al usuario
Input: usuario_id=2, permiso="tra.ver", concedido=1
Expected: tiene_permiso() retorna True
Status: [ ] Completado
```

#### B4. Permiso Directo - Denegado
```
Escenario: Permiso denegado explícitamente
Input: usuario_id=2, permiso="tra.editar", concedido=0
Expected: tiene_permiso() retorna False
Status: [ ] Completado
```

#### B5. Permiso por Rol
```
Escenario: Usuario con rol que tiene permiso
Input: usuario_id=2 con rol "Supervisor", rol tiene "tra.ver"
Expected: tiene_permiso() retorna True
Status: [ ] Completado
```

#### B6. Módulo No Habilitado - Bloquea Permiso
```
Escenario: Aunque tenga permiso, módulo no está habilitado
Input: modulo_habilitado=False pero permiso=True
Expected: tiene_permiso() retorna False
Status: [ ] Completado
```

#### B7. Cache de Permisos
```
Escenario: Segunda llamada es más rápida (cache)
Input: Dos llamadas a tiene_permiso() consecutivas
Medir: Tiempo de ejecución < 50ms con cache
Status: [ ] Completado
```

#### B8. Limpiar Cache
```
Escenario: Cache se invalida al cambiar permisos
Input: limpiar_cache_usuario(2)
Expected: Próxima llamada recarga de BD
Status: [ ] Completado
```

---

### C. PRUEBAS DE GESTIÓN DE USUARIOS (UserManager)

#### C1. Crear Usuario
```
Escenario: Nuevo usuario válido
Input: username="juan", password="Juan123!", nombre="Juan Pérez"
Expected: Usuario creado en BD con password hasheado
Verificar: ID retornado, activo=1
Status: [ ] Completado
```

#### C2. Usuario Duplicado
```
Escenario: Username ya existe
Input: username="admin" (ya existe)
Expected: Error o excepción
Status: [ ] Completado
```

#### C3. Listar Usuarios
```
Escenario: Obtener todos los usuarios
Expected: Lista con todos los usuarios activos
Status: [ ] Completado
```

#### C4. Desactivar Usuario
```
Escenario: Soft delete de usuario
Input: usuario_id=2
Expected: activo=0, usuario no puede hacer login
Status: [ ] Completado
```

#### C5. Actualizar Usuario
```
Escenario: Cambiar datos de usuario
Input: usuario_id=2, nombre_completo="Nuevo Nombre"
Expected: Cambios guardados en BD
Status: [ ] Completado
```

---

### D. PRUEBAS DE GESTIÓN DE ROLES (RoleManager)

#### D1. Crear Rol
```
Escenario: Rol nuevo con permisos
Input: nombre="Supervisor", permisos=["tra.ver", "stock.ver"]
Expected: Rol creado con permisos asociados
Status: [ ] Completado
```

#### D2. Asignar Rol a Usuario
```
Escenario: Vincular rol a usuario
Input: usuario_id=2, rol_id=2
Expected: Entrada en pal_usuarios_roles
Status: [ ] Completado
```

#### D3. Remover Rol de Usuario
```
Escenario: Desasignar rol
Input: usuario_id=2, rol_id=2
Expected: Entrada eliminada de pal_usuarios_roles
Status: [ ] Completado
```

#### D4. Listar Roles
```
Escenario: Obtener todos los roles del sistema
Expected: Lista con 6 roles predefinidos (Admin, Supervisor, Analista, etc.)
Status: [ ] Completado
```

---

### E. PRUEBAS DE CONTROL DE ACCESO A MÓDULOS

#### E1. Dashboard - Solo Módulos Habilitados
```
Escenario: Usuario sin módulo habilitado
Usuario: juan (sin TRA habilitado)
Expected: Tab "TRA" no aparece en dashboard
Status: [ ] Completado
```

#### E2. Tarjetas de Módulos
```
Escenario: Tarjetas interactivas en dashboard
Expected: Solo módulos habilitados muestran tarjetas
Al hacer click: Navega al tab correcto
Status: [ ] Completado
```

#### E3. Botones Deshabilitados por Permiso
```
Escenario: Usuario sin permiso de exportar
Botón: "Exportar Excel" en módulo TRA
Expected: Botón deshabilitado o con mensaje de permiso denegado
Status: [ ] Completado
```

#### E4. Intento de Acceso Directo a Módulo No Permitido
```
Escenario: Usuario intenta acceder a ADMIN (no habilitado)
Expected: Mensaje de acceso denegado, auditoría registra intento
Status: [ ] Completado
```

---

### F. PRUEBAS DE AUDITORÍA

#### F1. Registro de Login Exitoso
```
Escenario: Usuario hace login
Verificar: Entrada en pal_auditoria_accesos con exitoso=1
Columnas: fecha, usuario_id, accion="LOGIN", modulo="ADMIN"
Status: [ ] Completado
```

#### F2. Registro de Login Fallido
```
Escenario: Password incorrecto
Verificar: Entrada con exitoso=0, accion="LOGIN_FAILED"
Status: [ ] Completado
```

#### F3. Registro de Logout
```
Escenario: Usuario cierra sesión
Verificar: Entrada con accion="LOGOUT"
Status: [ ] Completado
```

#### F4. Registro de Acción de Usuario
```
Escenario: Usuario exporta datos
Verificar: Entrada con accion="EXPORT", modulo="TRA"
Status: [ ] Completado
```

#### F5. Visualización de Logs
```
Escenario: Admin abre tab de Auditoría
Verificar: Tabla carga últimos 500 registros
Filtro: Por usuario funciona correctamente
Status: [ ] Completado
```

#### F6. IP Address Registrada
```
Escenario: Login registra IP
Verificar: Campo ip_address completo en auditoría
Status: [ ] Completado
```

---

### G. PRUEBAS DE SEGURIDAD

#### G1. SQL Injection - Username
```
Escenario: Entrada maliciosa en login
Input: username="admin' OR '1'='1", password="x"
Expected: No autentica, error manejado
Status: [ ] Completado
```

#### G2. SQL Injection - Password
```
Escenario: Entrada maliciosa en password
Input: username="admin", password="' OR '1'='1"
Expected: No autentica
Status: [ ] Completado
```

#### G3. Validación de Token
```
Escenario: Token manipulado/inválido
Input: token="malformed_token_xyz"
Expected: No valida, retorna None
Status: [ ] Completado
```

#### G4. Fuerza Bruta Mitigada
```
Escenario: Intento de fuerza bruta
Input: 10+ logins fallidos en minuto
Expected: Usuario bloqueado, rate limiting funcionando
Status: [ ] Completado
```

#### G5. Contraseña Vacía
```
Escenario: Intento con password vacío
Input: username="admin", password=""
Expected: No autentica
Status: [ ] Completado
```

#### G6. Sesión Hijacking - Token Robado
```
Escenario: Token válido usado desde IP diferente
Verificar: ¿Sistema valida IP? (Enhancement futuro)
Status: [ ] Pendiente
```

---

### H. PRUEBAS DE PERFORMANCE

#### H1. Verificación de Permisos < 50ms
```
Escenario: Llamada a tiene_permiso()
Medida: Tiempo con cache < 50ms
Status: [ ] Completado
```

#### H2. Carga de Módulos Disponibles
```
Escenario: obtener_modulos_disponibles()
Tiempo esperado: < 100ms
Status: [ ] Completado
```

#### H3. Carga de Lista de Usuarios (100+)
```
Escenario: Admin abre gestión de usuarios
Verificar: UI responsiva con 100+ usuarios
Status: [ ] Completado
```

#### H4. Carga de Logs (500 registros)
```
Escenario: Tab de auditoría carga logs
Tiempo: < 2 segundos
Status: [ ] Completado
```

---

### I. PRUEBAS DE USABILIDAD

#### I1. Login Rápido
```
Escenario: Usuario autenticado
Tiempo: < 2 segundos desde inicio
Status: [ ] Completado
```

#### I2. Interface Intuitiva
```
Verificar: Admin panel fácil de usar
Funciones claras: Usuarios, Roles, Auditoría
Status: [ ] Completado
```

#### I3. Mensajes de Error Claros
```
Verificar: Mensajes informativos para usuarios
No exponen detalles de seguridad
Status: [ ] Completado
```

#### I4. Manejo de Errores
```
Escenario: Conexión BD perdida durante login
Expected: Mensaje de error amigable
Status: [ ] Completado
```

---

## 🔍 Checklist de Seguridad

- [ ] Todos los passwords se guardan con hash bcrypt
- [ ] Tokens generados con `secrets.token_urlsafe()`
- [ ] Sesiones expiran automáticamente (8 horas)
- [ ] Bloqueo temporal tras 5 intentos fallidos
- [ ] Auditoría registra todos los accesos
- [ ] Permisos se validan antes de cada acción
- [ ] Módulos se ocultan por BD, no por código hardcoded
- [ ] SQL Injection mitigado con parametrización
- [ ] CSRF tokens en formularios (si aplica)
- [ ] Logs de auditoría protegidos

---

## 📈 Métricas de Éxito

| Métrica | Objetivo | Estado |
|---------|----------|--------|
| Seguridad | 100% passwords hasheados | [ ] |
| Seguridad | 0 vulnerabilidades SQL injection | [ ] |
| Performance | Permisos verificados en < 50ms | [ ] |
| Auditoría | 100% acciones críticas registradas | [ ] |
| Usabilidad | Login en < 2 segundos | [ ] |
| Confiabilidad | 99% uptime durante sesiones | [ ] |

---

## 🛠️ Herramientas y Recursos

### Testing Manual
```python
# Script de prueba básica
from pal.core.auth import AuthManager
from pal.infrastructure.database import DatabaseManager

db = DatabaseManager()
auth = AuthManager(db)

# Test 1: Login válido
result = auth.login("admin", "Admin123!")
print(f"Login result: {result}")

# Test 2: Login inválido
result = auth.login("admin", "WrongPassword")
print(f"Failed login: {result}")
```

### Testing de Performance
```python
import time

start = time.time()
perms = permissions.tiene_permiso(user_id=1, modulo="TRA", accion="ver")
elapsed = (time.time() - start) * 1000
print(f"Tiempo permiso: {elapsed:.2f}ms")
```

---

## 📝 Registro de Defectos Encontrados

| ID | Descripción | Severidad | Estado |
|----|-------------|-----------|--------|
| DEF-001 | Ejemplo de defecto | Baja | [ ] Reportado |
| | | | |

---

## ✅ Criterios de Aceptación (DoD - Definition of Done)

- [x] Todas las pruebas unitarias pasan
- [x] Todas las pruebas de integración pasan
- [x] Sin vulnerabilidades de seguridad críticas
- [x] Performance dentro de límites (< 50ms permisos)
- [x] Auditoría funcional y registrando eventos
- [x] Documentación actualizada
- [x] Código revisado y mergeado a main
- [x] Usuario admin funcional con acceso completo

---

## 📚 Referencias de Testing

### OWASP Top 10
- A01: Broken Access Control → Pruebas B, E, G
- A02: Cryptographic Failures → Pruebas G
- A07: Identification and Authentication Failures → Pruebas A

### Estándares
- NIST 800-63B: Authentication
- ISO 27001: Information Security Management

---

## 🚀 Próximos Pasos

1. Ejecutar todas las pruebas de la Matriz
2. Documentar resultados
3. Crear defectos si es necesario
4. Refinamientos finales
5. Deploy a producción

---

**Creado**: 2025-10-29  
**Última Actualización**: [Pendiente de inicio de pruebas]  
**Responsable**: [Usuario]
