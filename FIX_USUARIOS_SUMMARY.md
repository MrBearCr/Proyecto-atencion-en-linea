# 🔧 Correcciones - Error al Guardar Usuarios

**Fecha**: 2025-10-30  
**Problema**: Error al guardar usuarios nuevos - NULL en pal_usuarios_modulos  
**Estado**: ✅ RESUELTO

---

## 📋 Problemas Encontrados

### Problema 1: UserManager.crear_usuario() retornaba 0
**Síntoma**: Error "usuario_id is NULL" al insertar en pal_usuarios_modulos

**Root Cause**: 
- Función no validaba si el INSERT fue exitoso
- Retornaba `0` en lugar de lanzar excepción
- No verificaba duplicados de username antes de insertar

**Archivo**: `pal/core/user_management.py` (línea 15-34)

### Problema 2: Estructura if/else incorrecta en _save_admin_user()
**Síntoma**: 
- `messagebox.showinfo("Usuario creado")` siempre se ejecutaba
- El `else` estaba fuera del `if is_new`
- Sin manejo de excepciones en crear usuario

**Archivo**: `app.py` (línea 4438-4528)

### Problema 3: Sin validación de user_id antes de guardar módulos
**Síntoma**: Intentaba insertar NULL en pal_usuarios_modulos

**Archivo**: `app.py` (línea 4510-4528)

---

## ✅ Correcciones Realizadas

### 1. Mejorar UserManager.crear_usuario()

```python
# ANTES (línea 15-34):
def crear_usuario(self, username, password, nombre_completo, email=None, roles=None):
    pwd_hash = bcrypt.hashpw(...)
    self.db.execute_query(...)  # No validaba resultado
    row = self.db.fetch_data(...)
    user_id = int(row[0][0]) if row else 0  # Retornaba 0 si falla
    return user_id

# AHORA:
def crear_usuario(self, username, password, nombre_completo, email=None, roles=None):
    """Crea nuevo usuario con validaciones"""
    pwd_hash = bcrypt.hashpw(...)
    
    # Validar que username no exista
    existing = self.db.fetch_data("SELECT id FROM pal_usuarios WHERE username = ?", (username,))
    if existing:
        raise Exception(f"El usuario '{username}' ya existe")
    
    # Insertar usuario
    success = self.db.execute_query(...)
    if not success:
        raise Exception(f"Error al crear usuario '{username}'")
    
    # Obtener ID
    row = self.db.fetch_data(...)
    if not row:
        raise Exception(f"No se pudo obtener ID del usuario '{username}'")
    
    user_id = int(row[0][0])
    return user_id
```

**Cambios**:
- ✅ Verificar username duplicado ANTES de insertar
- ✅ Validar resultado del execute_query
- ✅ Validar que se pueda recuperar el ID
- ✅ Lanzar excepciones descriptivas

---

### 2. Corregir estructura if/else en _save_admin_user()

```python
# ANTES (línea 4472-4508):
if is_new:
    user_id = um.crear_usuario(...)  # Sin try/except
messagebox.showinfo("Usuario creado")  # Siempre se ejecuta
else:  # Fuera del if!
    # Actualizar usuario

# AHORA:
if is_new:
    try:
        user_id = um.crear_usuario(username, password, nombre, email)
        messagebox.showinfo("Usuario creado exitosamente")
        # Auditoría
    except Exception as create_err:
        messagebox.showerror("Error", f"No se pudo crear usuario: {str(create_err)}")
        self.log(f"Error creando usuario: {create_err}", "ERROR")
        return  # Salir si falla la creación
else:
    # Actualizar usuario (solo si no es nuevo)
    user_id = self.current_admin_user_id
    self.db_manager.execute_query(...)
```

**Cambios**:
- ✅ Agregar try/except alrededor de crear_usuario()
- ✅ messagebox.showinfo() DENTRO del try
- ✅ Manejar excepción y retornar si falla
- ✅ Indentación correcta del else

---

### 3. Validar user_id antes de guardar módulos

```python
# ANTES (línea 4510-4527):
# Guardar módulos sin validar user_id
for modulo_db, var in self.admin_user_mod_vars.items():
    self.db_manager.execute_query(..., (user_id, ...))  # user_id puede ser None!

# AHORA:
# Guardar módulos (solo si user_id es válido)
if user_id:
    for modulo_db, var in self.admin_user_mod_vars.items():
        self.db_manager.execute_query(...)
    
    self.log(f"Usuario '{username}' guardado", "SUCCESS")
    self._reload_users_list()
    self._clear_user_form()
else:
    messagebox.showerror("Error", "No se asignó un ID válido al usuario")
```

**Cambios**:
- ✅ Validar `if user_id:` antes de loop
- ✅ Mensaje de error si user_id es inválido
- ✅ Protegido contra NULL en BD

---

## 🧪 Testing

### Caso 1: Crear usuario duplicado
```
Acción: Crear usuario "test" (ya existe)
Esperado: Error "El usuario 'test' ya existe"
✅ Funciona
```

### Caso 2: Crear usuario nuevo
```
Acción: Crear usuario "test2" con nombre "Test User 2"
Esperado: Usuario creado exitosamente
✅ Funciona
```

### Caso 3: Guardar módulos
```
Acción: Habilitar módulos para nuevo usuario
Esperado: Inserción exitosa en pal_usuarios_modulos
✅ Funciona
```

---

## 📊 Resumen de Cambios

| Archivo | Función | Cambios |
|---------|---------|---------|
| `pal/core/user_management.py` | `crear_usuario()` | +30 líneas de validación |
| `app.py` | `_save_admin_user()` | Estructura if/else corregida |
| `app.py` | `_save_admin_user()` | Validación de user_id agregada |

---

## 🎯 Impacto

- ✅ Error NULL en pal_usuarios_modulos: **RESUELTO**
- ✅ Detección de usuarios duplicados: **MEJORADA**
- ✅ Manejo de errores: **MEJORADO**
- ✅ Validaciones: **ROBUSTAS**

---

## 📌 Próximos Pasos

1. ✅ Probar crear usuarios nuevos
2. ✅ Probar editar usuarios existentes
3. ✅ Probar habilitar/deshabilitar módulos
4. ✅ Verificar logs de auditoría
5. [ ] Completar matriz de pruebas de Fase 7

---

**Estado**: ✅ COMPLETADO  
**Prueba**: ✅ EXITOSA  
**Deploy**: Listo

