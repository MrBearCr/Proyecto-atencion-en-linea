# Integración con WhatsApp (Graph API)

## Configuración
1. Obtener token en Meta Developer → WhatsApp Business.
2. Guardarlo en la app: Settings → API WhatsApp (se almacena cifrado en keyring).

## Envío de mensajes (plantillas)
```python
import requests
from pal.core.credentials import SecureCredentialsManager

API_ENDPOINT = "https://graph.facebook.com/v21.0/<PHONE_NUMBER_ID>/messages"
cred = SecureCredentialsManager()
whatsapp_token = cred.get_whatsapp_token()

payload = {
  "messaging_product": "whatsapp",
  "to": "58XXXXXXXXXX",
  "type": "template",
  "template": {
    "name": "alerta_stock",
    "language": {"code": "es"},
    "components": [{
      "type": "body",
      "parameters": [{"type": "text", "text": "1. Prod A • 2. Prod B"}]
    }]
  }
}
headers = {"Authorization": f"Bearer {whatsapp_token}", "Content-Type": "application/json"}
resp = requests.post(API_ENDPOINT, headers=headers, json=payload)
```

## Consideraciones
- Respetar límites de tasa de la API; la app espacía envíos masivos (~7s).
- Plantillas deben estar aprobadas previamente.
- Nunca registrar el token en logs.

