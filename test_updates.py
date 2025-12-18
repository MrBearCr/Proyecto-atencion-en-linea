"""
Script de prueba para el sistema de actualizaciones automáticas.

Este script permite probar la funcionalidad de actualizaciones automáticas
de manera local antes de configurar un servidor real.

Uso:
    python test_updates.py

El script creará un servidor HTTP local que simula un servidor de actualizaciones.
"""

import os
import sys
import json
import http.server
import socketserver
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Configuración
PORT = 8000
UPDATE_DIR = "test_updates"
VERSION_FILE = os.path.join(UPDATE_DIR, "version.json")
TEST_VERSION = "1.0.1"  # Versión de prueba (mayor que la actual 1.0.0)


class UpdateHandler(http.server.SimpleHTTPRequestHandler):
    """Manejador HTTP personalizado para servir actualizaciones."""
    
    def do_GET(self):
        """Maneja las peticiones GET."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Debug: mostrar la ruta solicitada
        print(f"[Servidor] Solicitud GET: {path}")
        
        # Servir el archivo version.json (múltiples rutas posibles)
        if path == "/version.json" or path == "/updates/version.json" or path.endswith("/version.json"):
            print(f"[Servidor] Sirviendo version.json")
            self.send_version_info()
        # Servir archivos estáticos
        elif path.startswith("/updates/"):
            filename = path[9:]  # Remover "/updates/"
            print(f"[Servidor] Sirviendo archivo: {filename}")
            self.serve_file(filename)
        else:
            # Para debugging: mostrar qué ruta se solicitó
            print(f"[Servidor] Ruta no encontrada: {path}")
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            error_msg = f"Not Found: {path}\n\nRutas disponibles:\n- /version.json\n- /updates/version.json\n- /updates/*"
            self.wfile.write(error_msg.encode('utf-8'))
    
    def send_version_info(self):
        """Envía información de versión en formato JSON."""
        version_info = {
            "version": TEST_VERSION,
            "url": f"http://localhost:{PORT}/updates/app-{TEST_VERSION}.zip",
            "changelog": "Versión de prueba con mejoras:\n- Integración de actualizaciones automáticas\n- Mejoras en rendimiento\n- Corrección de errores menores"
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(version_info).encode('utf-8'))
    
    def serve_file(self, filename):
        """Sirve un archivo desde el directorio de actualizaciones."""
        file_path = os.path.join(UPDATE_DIR, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            # Determinar content-type
            if filename.endswith('.zip'):
                self.send_header('Content-Type', 'application/zip')
            elif filename.endswith('.json'):
                self.send_header('Content-Type', 'application/json')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Access-Control-Allow-Origin', '*')
            
            # Enviar tamaño del archivo
            file_size = os.path.getsize(file_path)
            self.send_header('Content-Length', str(file_size))
            self.end_headers()
            
            # Enviar contenido del archivo
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File Not Found")
    
    def log_message(self, format, *args):
        """Sobrescribe el método de logging para mostrar mensajes más claros."""
        print(f"[Servidor] {format % args}")


def create_test_update_structure():
    """Crea la estructura de directorios y archivos de prueba."""
    os.makedirs(UPDATE_DIR, exist_ok=True)
    
    # Crear archivo version.json
    version_info = {
        "version": TEST_VERSION,
        "url": f"http://localhost:{PORT}/updates/app-{TEST_VERSION}.zip",
        "changelog": "Versión de prueba con mejoras:\n- Integración de actualizaciones automáticas\n- Mejoras en rendimiento\n- Corrección de errores menores"
    }
    
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)
    
    print(f"[INFO] Archivo de versión creado: {VERSION_FILE}")
    print(f"[INFO] Versión de prueba: {TEST_VERSION}")
    print(f"[INFO] Para probar, configura UPDATE_URL en app.py como: http://localhost:{PORT}/updates/")


def start_server():
    """Inicia el servidor HTTP local."""
    handler = UpdateHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n{'='*60}")
        print(f"Servidor de actualizaciones de prueba iniciado")
        print(f"{'='*60}")
        print(f"URL: http://localhost:{PORT}")
        print(f"Archivo de versión: http://localhost:{PORT}/version.json")
        print(f"\nPara probar actualizaciones:")
        print(f"1. Asegúrate de que UPDATE_URL en app.py apunte a: http://localhost:{PORT}/updates/")
        print(f"2. Ejecuta la aplicación principal")
        print(f"3. Ve a Configuración > Actualizaciones")
        print(f"4. Haz clic en 'Verificar actualizaciones ahora'")
        print(f"\nPresiona Ctrl+C para detener el servidor")
        print(f"{'='*60}\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Deteniendo servidor...")
            httpd.shutdown()


def main():
    """Función principal."""
    print("="*60)
    print("Script de Prueba para Actualizaciones Automáticas")
    print("="*60)
    
    # Crear estructura de prueba
    create_test_update_structure()
    
    # Iniciar servidor
    start_server()


if __name__ == "__main__":
    main()
