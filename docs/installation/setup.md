# Configuración Inicial

## Estructura del Proyecto
```Markdown
src/
├── app.py # Punto de entrada principal
├── db/
│ ├── manager.py # DatabaseManager y clases relacionadas
│ └── models.py # Modelos de datos y esquemas
├── auth/
│ ├── session.py # SessionManager
│ └── crypto.py # SecureCredentialsManager
├── ui/
│ ├── widgets/ # Componentes personalizados
│ └── themes/ # Configuración de estilos
└── utils/
├── logger.py # AuditLogger
└── api_client.py # Cliente WhatsApp API
```