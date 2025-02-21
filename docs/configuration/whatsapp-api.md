# Integración con WhatsApp API

## Clase WhatsAppClient (utils/api_client.py)
```python
class WhatsAppClient:
    def __init__(self, token: str):
        self.base_url = "https://graph.facebook.com/v21.0"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def send_template_message(self, phone: str, template: str, parameters: list):
        """Envía mensaje usando plantilla pre-aprobada"""
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": "es"},
                "components": [{"type": "body", "parameters": parameters}]
            }
        }
        response = requests.post(
            f"{self.base_url}/490677417472051/messages",
            headers=self.headers,
            json=payload
        )
        return response.json()

        # Ejemplo de almacenamiento

cred_manager.store_whatsapp_token("EAABkZ...")
```