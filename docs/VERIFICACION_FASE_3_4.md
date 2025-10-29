# Verificación del Sistema de Usuarios y Privilegios
## Fases 3-4 Implementadas

---

## ✅ Fase 3: Interface de Login

### 1. Splash Screen con Login
- **Ubicación**: Al iniciar la app, mostrar splash con logo, barra de progreso y formulario de login
- **Verificar**:
  - [ ] Splash se muestra al conectar a BD
  - [ ] Aparecen campos "Usuario" y "Contraseña"
  - [ ] Botón "Entrar" se habilita tras conectar
  - [ ] Mensaje "Ingrese sus credenciales"

### 2. Credenciales Iniciales
- **Admin automático**: usuario: `admin`, contraseña: `123` (predeterminada)
- **Verificar**:
  - [ ] Ingresar admin/123 en el splash
  - [ ] Sistema pide cambiar contraseña (forzado en primer acceso)
  - [ ] Ingresar nueva contraseña dos veces
  - [ ] Confirmación: "Contraseña actualizada"
  - [ ] App carga con módulos habilitados

### 3. Logout
- **Ubicación**: Menú Usuario → Cerrar sesión
- **Verificar**:
  - [ ] Botón "Cerrar sesión" en esquina superior derecha
  - [ ] Al hacer clic, pide confirmación
  - [ ] Muestra diálogo de login nuevamente

---

## ✅ Fase 4: Control de Acceso a Módulos

### 1. Módulos Basados en BD (pal_usuarios_modulos)
- **Control**: Los módulos se habilitan/deshabilitan desde BD, no desde archivo ini
- **Verificar**:
  - [ ] Al iniciar sesión, solo ver módulos habilitados en BD para ese usuario
  - [ ] Tabs deshabilitados no aparecen en el workspace
  - [ ] Admin ve todos los módulos (si están habilitados en BD)
  - [ ] Usuario normal solo ve sus módulos asignados

### 2. Gestión de Módulos en Configuración (solo admin)
- **Ubicación**: Configuración → Gestión de Usuarios
- **Verificar**:
  - [ ] Si NO eres admin: mostrar "Solo el administrador puede gestionar usuarios y módulos"
  - [ ] Si eres admin:
    - [ ] Selector desplegable con usuarios
    - [ ] Checkboxes para módulos (TRA, MBRP, STOCK, MENSAJES, ESTADISTICAS, CALENDARIO, ADMIN)
    - [ ] Botón "Guardar Módulos"
    - [ ] Botón "Recargar"
  - [ ] Seleccionar usuario, marcar módulos, guardar
  - [ ] Cerrar sesión, login con ese usuario
  - [ ] Verificar que solo ve esos módulos

---

## ✅ Fase 4 - PARTE 2: Gestión de Usuarios (Pestaña Admin)

### 1. Pestaña "Gestión de Usuarios"
- **Ubicación**: Workspace principal (pestaña 🔓 Gestión de Usuarios)
- **Solo visible para**: Usuario admin (si tiene módulo ADMIN habilitado)
- **Verificar**:
  - [ ] Admin ve pestaña "🔓 Gestión de Usuarios" en el workspace
  - [ ] Usuario normal NO ve esa pestaña

### 2. Interfaz de Administración
- **Left (Listado)**:
  - [ ] Treeview con columnas: ID, Usuario, Nombre Completo, Activo (✓/❌)
  - [ ] Todos los usuarios activos e inactivos listados
  - [ ] Hacer clic en usuario carga su info en el formulario

- **Right (Formulario)**:
  - [ ] Campo "Usuario"
  - [ ] Campo "Nombre Completo"
  - [ ] Campo "Email"
  - [ ] Campo "Contraseña" (con nota "dejar en blanco para no cambiar")
  - [ ] Checkbox "Activo"
  - [ ] Checkboxes para módulos (ADMIN, CALENDARIO, ESTADISTICAS, MBRP, MENSAJES, STOCK, TRA)
  - [ ] Botones: "Nuevo Usuario", "Guardar", "Eliminar"

### 3. Crear Nuevo Usuario
- **Verificar**:
  - [ ] Click en "Nuevo Usuario"
  - [ ] Formulario se limpia
  - [ ] Campo Usuario enfocado
  - [ ] Llenar: usuario, nombre, email, contraseña
  - [ ] Marcar módulos a habilitar
  - [ ] Click "Guardar"
  - [ ] Mensaje: "Usuario '[username]' creado exitosamente"
  - [ ] Usuario aparece en listado
  - [ ] Logout, login con ese usuario
  - [ ] Verificar que solo ve módulos asignados

### 4. Editar Usuario
- **Verificar**:
  - [ ] Seleccionar usuario del listado
  - [ ] Datos se cargan en formulario
  - [ ] Cambiar nombre o email
  - [ ] Marcar/desmarcar módulos
  - [ ] Click "Guardar"
  - [ ] Mensaje: "Usuario actualizado exitosamente"
  - [ ] Logout y login para verificar cambios

### 5. Desactivar Usuario
- **Verificar**:
  - [ ] Seleccionar usuario
  - [ ] Click "Eliminar"
  - [ ] Pide confirmación: "¿Desactivar usuario '[username]'?"
  - [ ] Confirmar
  - [ ] Mensaje: "Usuario desactivado"
  - [ ] Usuario ahora muestra ❌ en columna "Activo"
  - [ ] Usuario NO puede iniciar sesión con sus credenciales

---

## 📋 Checklist de Verificación Completa

### Seguridad
- [ ] Admin puede cambiar contraseña de otros usuarios
- [ ] Passwords se hashean (no se muestran en BD)
- [ ] Session token expira correctamente
- [ ] Usuario desactivado no puede acceder

### Funcionalidad
- [ ] Crear usuario funciona correctamente
- [ ] Editar usuario y módulos funciona
- [ ] Desactivar usuario funciona
- [ ] Módulos cargados dinámicamente desde BD
- [ ] UI responde correctamente

### UX
- [ ] Formulario limpio y intuitivo
- [ ] Mensajes de confirmación claros
- [ ] Errores mostrados adecuadamente
- [ ] Lista se recarga tras cambios
- [ ] Campos requeridos validados

---

## 🔍 Pruebas Recomendadas

### Test 1: Admin Inicial
```
1. Ejecutar app
2. Conectar a BD
3. Login: admin / 123
4. Cambiar contraseña a "AdminNew123"
5. Verificar acceso a "Gestión de Usuarios"
```

### Test 2: Crear Usuario
```
1. En "Gestión de Usuarios"
2. Click "Nuevo Usuario"
3. Llenar:
   - Usuario: "operador1"
   - Nombre: "Juan Pérez"
   - Email: "juan@example.com"
   - Contraseña: "Op123456"
   - Módulos: STOCK, TRA, MBRP
4. Guardar
5. Logout
6. Login: operador1 / Op123456
7. Verificar que solo ve tabs STOCK, TRA, MBRP
```

### Test 3: Editar Módulos
```
1. Como admin, seleccionar "operador1"
2. Desmarcar MBRP
3. Marcar MENSAJES
4. Guardar
5. Logout
6. Login: operador1 / Op123456
7. Verificar que ahora ve: STOCK, TRA, MENSAJES (no MBRP)
```

### Test 4: Desactivar Usuario
```
1. Como admin, seleccionar "operador1"
2. Click "Eliminar"
3. Confirmar
4. Logout
5. Intentar login: operador1 / Op123456
6. Debe fallar: "Usuario o contraseña inválidos"
```

---

## 🚨 Posibles Problemas y Soluciones

### Problema: Tab "Gestión de Usuarios" no aparece
- **Causa**: Módulo ADMIN no habilitado para admin en BD
- **Solución**: En Configuración → Gestión de Usuarios, habilitar ADMIN para admin

### Problema: Crear usuario falla
- **Causa**: Contraseña vacía o usuario duplicado
- **Solución**: Verificar que campo usuario no exista en BD, contraseña no sea vacía

### Problema: Login falla tras crear usuario
- **Causa**: Hash de contraseña incorrecto
- **Solución**: Verificar que bcrypt esté importado y funcionando

### Problema: Módulos no aparecen tras login
- **Causa**: Tabla `pal_usuarios_modulos` vacía o no sincronizada
- **Solución**: Verificar en BD que usuario tiene registros en pal_usuarios_modulos

---

## ✅ Próximos Pasos (Fases 5-7)

- [ ] **Fase 5**: Panel de Administración completo (roles, permisos granulares)
- [ ] **Fase 6**: Auditoría y Logs (registro de accesos)
- [ ] **Fase 7**: Testing y Refinamiento

