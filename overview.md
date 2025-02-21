# Gestión de Clientes - Documentación Técnica

## Descripción General
Aplicación de escritorio para gestión de clientes y envío masivo de notificaciones por WhatsApp. Desarrollada en Python con:
- **Interfaz Gráfica**: Tkinter
- **Base de Datos**: SQL Server
- **Seguridad**: Cifrado Fernet y Keyring
- **API**: WhatsApp Business

---

## Características Clave
✅ **CRUD de Clientes**  
✅ **Integración con WhatsApp**  
✅ **Cifrado de Credenciales**  
✅ **Auditoría de Eventos**  
✅ **Manejo de Sesiones Seguras**

---

## Requisitos
| Componente       | Versión Mínima |
|------------------|----------------|
| Python           | 3.8+           |
| SQL Server       | 2016+          |
| pyodbc           | 4.0+           |
| Tkinter          | 8.6+           |

---

## Instalación
```bash
pip install -r requirements.txt

```

## Códigos de Error

| Código | Tipo                  | Descripción                                      | Posibles Soluciones                  |
|--------|-----------------------|-------------------------------------------------|---------------------------------------|
| 1001   | Base de Datos         | Error de conexión a la base de datos            | Verificar credenciales y servidor    |
| 1002   | Base de Datos         | Error al ejecutar consulta SQL                  | Revisar sintaxis SQL                 |
| 2001   | Validación            | Número de cliente inválido                      | Usar solo números (1-11 dígitos)     |
| 2003   | Validación            | Entrada con caracteres peligrosos               | Evitar caracteres especiales         |
| 3001   | Cifrado               | Error al cifrar datos                           | Verificar clave de cifrado           |
| 4002   | API                   | Token de API inválido o expirado                | Actualizar token en configuración    |
| 5002   | Sesión                | Sesión expirada por inactividad                 | Reingresar al sistema                |
| 6001   | Configuración         | Configuración faltante                          | Verificar archivo de configuración   |