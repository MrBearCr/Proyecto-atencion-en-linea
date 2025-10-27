# ARCHIVO ARCHIVADO
Este documento ha sido unificado en `docs/README.md`.

Contenido original (tabla y códigos vigente en el código):

# Sistema de Gestión de Errores

| Código | Categoría            | Descripción                                 |
|-------:|----------------------|---------------------------------------------|
| 1001   | Base de Datos        | Error de conexión a la base de datos        |
| 1002   | Base de Datos        | Error al ejecutar consulta SQL              |
| 1003   | Base de Datos        | Error creando tabla en la base de datos     |
| 1004   | Base de Datos        | Registro no encontrado                      |
| 1005   | Base de Datos        | Descripción no encontrada                   |
| 2001   | Validación           | Número de cliente inválido                  |
| 2002   | Validación           | Código de producto inválido                 |
| 2003   | Validación           | Entrada con caracteres potencialmente peligrosos |
| 3001   | Cifrado              | Error al cifrar datos                       |
| 3002   | Cifrado              | Error al descifrar datos                    |
| 3003   | Cifrado              | Error generando clave de cifrado            |
| 4001   | API                  | Error en comunicación con API de WhatsApp   |
| 4002   | API                  | Token de API inválido o expirado            |
| 5001   | Autenticación/Sesión | Error de autenticación                      |
| 5002   | Autenticación/Sesión | Sesión expirada por inactividad             |
| 6001   | Configuración        | Configuración faltante                      |
| 6002   | Configuración        | Configuración inválida                      |