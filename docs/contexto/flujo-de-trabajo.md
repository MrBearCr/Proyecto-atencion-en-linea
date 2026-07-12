# Flujo de trabajo

## Antes de tocar nada
1. Verificar que el entorno virtual esté activo y las dependencias de `requirements.txt` instaladas.
2. Leer la documentación en `GEMINI.md` para entender el impacto en jerarquías o descripciones.
3. Asegurarse de tener conectividad con la base de datos SQL Server configurada en `db_config.ini` (encriptado vía `keyring`).

## Para hacer un cambio
1. Modificar los componentes en su carpeta correspondiente, respetando la arquitectura: `pal/ui` para vistas, `pal/services` para lógica de negocio o exportación, `pal/core` para componentes base.
2. Probar conectividad y operaciones intensivas con el `DatabaseManager` sin bloquear la UI principal.
3. Crear o actualizar los tests unitarios correspondientes en `tests/` si se modifica la lógica de negocio, infraestructura o mecanismos del core.
4. Actualizar la versión si aplica en `app.py` o módulo de versión (`chore: bump application version...`).

## Antes de dar algo por terminado
- [ ] No hay credenciales en texto plano (verificar uso de `SecureCredentialsManager`).
- [ ] Las consultas pesadas se ejecutan en hilos/pools, no bloquean el mainloop de Tkinter.
- [ ] Se registran las acciones críticas usando el `AuditLogger`.
- [ ] Los errores utilizan el sistema unificado de `ErrorCode` en `pal/core/errors.py`.
- [ ] Todo formato a Excel pasa por `clean_for_excel()` para evitar caracteres de control.
- [ ] Se ejecutan y superan todas las pruebas automatizadas usando `pytest` o `python -m unittest discover -s tests`.
- [ ] Si se añade funcionalidad crítica, se incluye su respectivo test unitario de cobertura.

## Deploy
La publicación se realiza compilando la aplicación a binario `.exe` (utilizando InnoSetup/Nuitka con `build.bat` o `setup_nuitka.iss`). El sistema interno `nexus_updater.exe` / `updater_main.py` maneja las descargas e instalación de nuevas versiones para el usuario final.
