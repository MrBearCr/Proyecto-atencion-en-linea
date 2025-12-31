"""
Módulo de actualización automática usando pyautoupdate.
Maneja la verificación y descarga de actualizaciones para la aplicación.
"""
import os
import sys
import threading
import tkinter.messagebox as messagebox
from typing import Optional, Callable
import logging
import re
import subprocess
import zipfile
import shutil

# pyautoupdate no es compatible con Python 3.13+
# Implementamos una solución personalizada usando requests
PY_AUTOUPDATE_AVAILABLE = True  # Siempre disponible con nuestra implementación


def _normalize_github_url(url: str) -> str:
    """
    Convierte URLs de GitHub web interface a raw URLs para acceso directo a archivos.
    
    Convierte:
    - https://github.com/user/repo/tree/branch/path -> https://raw.githubusercontent.com/user/repo/branch/path
    - https://github.com/user/repo/blob/branch/path -> https://raw.githubusercontent.com/user/repo/branch/path
    - Deja intactas las URLs que ya son raw.githubusercontent.com
    - Deja intactas otras URLs
    
    Args:
        url: URL a normalizar
        
    Returns:
        URL normalizada a formato raw
    """
    if not url:
        return url
    
    # Si ya es una URL raw, no hacer nada
    if 'raw.githubusercontent.com' in url:
        return url
    
    # Patrón para URLs de GitHub web interface
    # github.com/user/repo/tree/branch/path
    # github.com/user/repo/blob/branch/path
    pattern = r'https?://github\.com/([^/]+)/([^/]+)/(?:tree|blob)/([^/]+)(/.+)?'
    match = re.match(pattern, url)
    
    if match:
        user, repo, branch, path = match.groups()
        path = path or ''
        # Construir URL raw
        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}{path}"
    
    # Si no es una URL de GitHub web, devolverla tal cual
    return url


class UpdateManager:
    """
    Gestor de actualizaciones automáticas para la aplicación.
    
    Requiere:
    - Una URL base donde se alojan las versiones (ej: https://tu-servidor.com/updates/)
    - Un archivo version.json en esa URL con la estructura:
      {
          "version": "1.0.0",
          "url": "https://tu-servidor.com/updates/app-1.0.0.zip",
          "changelog": "Descripción de cambios"
      }
    """
    
    def __init__(
        self,
        app_name: str,
        current_version: str,
        update_url: str,
        update_check_interval: int = 3600,  # 1 hora por defecto
        auto_download: bool = False,
        auto_install: bool = False
    ):
        """
        Inicializa el gestor de actualizaciones.
        
        Args:
            app_name: Nombre de la aplicación
            current_version: Versión actual de la aplicación (ej: "1.0.0")
            update_url: URL base donde se alojan las actualizaciones
            update_check_interval: Intervalo en segundos para verificar actualizaciones
            auto_download: Si True, descarga automáticamente las actualizaciones
            auto_install: Si True, instala automáticamente las actualizaciones (requiere auto_download=True)
        """
        # No necesitamos verificar pyautoupdate ya que usamos nuestra implementación
        
        self.app_name = app_name
        self.current_version = current_version
        self.update_url = update_url
        self.update_check_interval = update_check_interval
        self.auto_download = auto_download
        self.auto_install = auto_install
        
        # Obtener el directorio de la aplicación
        if getattr(sys, 'frozen', False):
            # Ejecutable compilado con PyInstaller
            self.app_dir = os.path.dirname(sys.executable)
        else:
            # Ejecutándose desde código fuente
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.update_dir = os.path.join(self.app_dir, 'updates')
        os.makedirs(self.update_dir, exist_ok=True)
        
        # Almacenar configuración
        self.app_name = app_name
        self.current_version = current_version
        self.update_url = update_url
        self._latest_version_info = None
        self._downloaded_zip = None
        
        self.logger = logging.getLogger(__name__)
        self._check_thread: Optional[threading.Thread] = None
        self._stop_checking = threading.Event()
        self.logger.debug(f"UpdateManager initialized: App='{app_name}', CurrentVersion='{current_version}', UpdateURL='{update_url}'")
        
    def check_for_updates(self, show_no_update_message: bool = False) -> bool:
        """
        Verifica si hay actualizaciones disponibles.
        
        Args:
            show_no_update_message: Si True, muestra un mensaje cuando no hay actualizaciones
            
        Returns:
            True si hay actualizaciones disponibles, False en caso contrario
        """
        self.logger.debug(f"Entering check_for_updates. Current version: {self.current_version}")
        try:
            import requests
            from packaging import version
            
            # Normalizar URL de GitHub a formato raw si es necesario
            normalized_url = _normalize_github_url(self.update_url)
            self.logger.info(f"Verificando actualizaciones desde {normalized_url}")
            
            # Obtener información de versión del servidor
            # Asegurar que la URL termine sin / y luego agregar version.json
            base_url = normalized_url.rstrip('/')
            # Evitar duplicar version.json si ya está en la URL
            if base_url.endswith('/version.json'):
                version_url = base_url
            else:
                version_url = f"{base_url}/version.json"
            
            self.logger.debug(f"Fetching version info from: {version_url}")
            
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            
            # Verificar que la respuesta es JSON válido
            if not response.text.strip():
                self.logger.warning("Server response is empty when checking for updates.")
                raise ValueError("La respuesta del servidor está vacía")
            
            # Intentar parsear JSON con mejor manejo de errores
            try:
                version_data = response.json()
            except ValueError as json_error:
                # Mostrar los primeros caracteres de la respuesta para debugging
                preview = response.text[:200] if len(response.text) > 200 else response.text
                self.logger.error(
                    f"Error al parsear JSON de la respuesta. "
                    f"Status: {response.status_code}, "
                    f"Content-Type: {response.headers.get('Content-Type', 'unknown')}, "
                    f"Preview: {preview}"
                )
                raise ValueError(
                    f"Error al parsear JSON de la respuesta. "
                    f"Status: {response.status_code}, "
                    f"Content-Type: {response.headers.get('Content-Type', 'unknown')}, "
                    f"Preview: {preview}"
                ) from json_error
            
            latest_version = version_data.get('version', '')
            self.logger.debug(f"Latest version from server: {latest_version}")
            
            # Comparar versiones
            if latest_version and version.parse(latest_version) > version.parse(self.current_version):
                self.logger.info(f"Actualización disponible: {latest_version} (actual: {self.current_version})")
                self._latest_version_info = version_data  # Guardar para uso posterior
                return True
            else:
                if show_no_update_message:
                    messagebox.showinfo(
                        "Actualizaciones",
                        f"Ya tienes la versión más reciente ({self.current_version})"
                    )
                self.logger.info(f"No hay actualizaciones disponibles. Versión actual ({self.current_version}) es la más reciente o posterior a la del servidor ({latest_version}).")
                return False
                
        except Exception as e:
            self.logger.error(f"Error al verificar actualizaciones: {str(e)}")
            if show_no_update_message:
                messagebox.showerror(
                    "Error de actualización",
                    f"No se pudo verificar actualizaciones: {str(e)}"
                )
            return False
    
    def download_update(self, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Descarga la actualización disponible.
        
        Args:
            progress_callback: Función opcional que recibe el progreso (0.0 a 1.0)
            
        Returns:
            True si la descarga fue exitosa, False en caso contrario
        """
        self.logger.debug("Entering download_update.")
        try:
            import requests
            
            self.logger.info("Iniciando descarga de actualización...")
            
            # Obtener URL de descarga desde version.json
            if not hasattr(self, '_latest_version_info') or self._latest_version_info is None:
                self.logger.warning("No _latest_version_info found, attempting to check for updates.")
                if not self.check_for_updates():
                    self.logger.error("No update information available after re-check.")
                    return False
            
            download_url = self._latest_version_info.get('url', '')
            if not download_url:
                self.logger.error("No se encontró URL de descarga en version.json")
                return False
            
            self.logger.debug(f"Download URL: {download_url}")
            
            # Descargar archivo
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Guardar en directorio de actualizaciones
            zip_path = os.path.join(self.update_dir, 'update.zip')
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            self.logger.debug(f"Saving downloaded update to: {zip_path}")
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = downloaded / total_size
                            progress_callback(progress)
            
            self.logger.info(f"Actualización descargada exitosamente. Guardado en {zip_path}")
            self._downloaded_zip = zip_path
            return True
                
        except Exception as e:
            self.logger.error(f"Error al descargar actualización: {str(e)}")
            messagebox.showerror(
                "Error de descarga",
                f"No se pudo descargar la actualización: {str(e)}"
            )
            return False
    
    def install_update(self, restart_callback: Optional[Callable[[], None]] = None) -> bool:
        """
        Instala la actualización descargada.
        
        Para aplicaciones instaladas con Inno Setup, ejecuta el instalador descargado.
        Para aplicaciones portables, extrae el ZIP.
        
        Args:
            restart_callback: Función opcional para reiniciar la aplicación después de la instalación
            
        Returns:
            True si la instalación fue exitosa, False en caso contrario
        """
        self.logger.debug("Entering install_update.")
        try:
            if not hasattr(self, '_downloaded_zip') or not os.path.exists(self._downloaded_zip):
                self.logger.error("No hay archivo de actualización descargado (_downloaded_zip no existe o archivo no encontrado)")
                return False
            
            self.logger.info("Instalando actualización...")
            self.logger.debug(f"Downloaded ZIP file: {self._downloaded_zip}")
            
            # Verificar si es un instalador .exe o un ZIP
            downloaded_file = self._downloaded_zip
            
            # Si es ZIP, extraer y buscar instalador dentro
            if downloaded_file.endswith('.zip'):
                extract_dir = os.path.join(self.update_dir, 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                self.logger.debug(f"Extracting ZIP to: {extract_dir}")
                
                with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Buscar instalador .exe en el directorio extraído
                installer_files = []
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith('.exe') and ('setup' in file.lower() or 'install' in file.lower()):
                            installer_files.append(os.path.join(root, file))
                
                if installer_files:
                    from packaging import version
                    
                    def get_version_from_filename(filename):
                        # Extraer versión de nombres como 'app-1.2.3-setup.exe'
                        match = re.search(r'(\d+(\.\d+)+)', os.path.basename(filename))
                        if match:
                            return version.parse(match.group(0))
                        return version.parse('0.0.0') # Versión por defecto si no se encuentra

                    # Ordenar instaladores por versión
                    installer_files.sort(key=get_version_from_filename)
                    
                    # Usar el instalador con la versión más alta
                    installer_path = installer_files[-1]
                    self.logger.info(f"Instalador más reciente encontrado: {installer_path}")
                else:
                    # Si no hay instalador, asumir que es una actualización portable
                    self.logger.info("No se encontró instalador, asumiendo actualización portable")
                    messagebox.showinfo(
                        "Actualización descargada",
                        "La actualización se ha descargado correctamente.\n\n"
                        "Para completar la instalación, cierra la aplicación y ejecuta el instalador manualmente."
                    )
                    return True
            else:
                # Es un archivo .exe directamente
                installer_path = downloaded_file
            
            self.logger.debug(f"Determined installer path: {installer_path}")
            self.logger.info(f"Lanzando el instalador a través del script: {installer_path}")
            
            try:
                # Obtener la ruta del ejecutable de Python
                python_executable = sys.executable
                self.logger.debug(f"Python executable: {python_executable}")
                
                # Obtener la ruta del script de lanzamiento
                # Se asume que está en el directorio raíz del proyecto
                if getattr(sys, 'frozen', False):
                    # Si es un ejecutable, el launcher debería estar al lado del ejecutable
                    base_dir = os.path.dirname(sys.executable)
                    self.logger.debug(f"Running as frozen app. Base dir: {base_dir}")
                else:
                    # Si se ejecuta desde el código fuente, buscar en el directorio raíz del proyecto
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                    self.logger.debug(f"Running from source. Base dir: {base_dir}")
    
                launcher_script = os.path.join(base_dir, 'updater_launcher.py')
                self.logger.debug(f"Calculated launcher_script path: {launcher_script}")
    
                if not os.path.exists(launcher_script):
                    # Fallback al directorio de trabajo actual
                    self.logger.warning(f"Launcher script not found at {launcher_script}. Trying current working directory.")
                    launcher_script = os.path.join(os.getcwd(), 'updater_launcher.py')
                    if not os.path.exists(launcher_script):
                        self.logger.critical(f"Launcher script 'updater_launcher.py' not found in any expected location.")
                        raise FileNotFoundError("El script de lanzamiento 'updater_launcher.py' no se encontró.")
                
                self.logger.debug(f"Final launcher_script path: {launcher_script}")
                pid = os.getpid()
                command = [python_executable, launcher_script, installer_path, str(pid)]
                self.logger.debug(f"Executing command: {command}")
                
                # Ejecutar el script de forma desacoplada
                subprocess.Popen(command, creationflags=subprocess.DETACHED_PROCESS, close_fds=True)
                self.logger.info("subprocess.Popen llamado. Script de actualización iniciado.")
                
                messagebox.showinfo(
                    "Actualización en curso",
                    "La actualización se ha iniciado. La aplicación se cerrará ahora para completar el proceso."
                )
    
                # Cerrar la aplicación actual para permitir que el instalador proceda
                if restart_callback:
                    self.logger.info("Llamando a restart_callback para cerrar la aplicación.")
                    restart_callback()
                else:
                    self.logger.info("restart_callback no proporcionado. Forzando salida con os._exit(0).")
                    os._exit(0)
                
                self.logger.info("install_update completado exitosamente.")
                return True
            except Exception as e:
                self.logger.error(f"Error al lanzar el script de actualización: {str(e)}")
                messagebox.showerror(
                    "Error de actualización",
                    f"No se pudo iniciar el proceso de actualización: {str(e)}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error al instalar actualización: {str(e)}")
            messagebox.showerror(
                "Error de instalación",
                f"No se pudo instalar la actualización: {str(e)}\n\n"
                "Por favor, descarga e instala manualmente desde:\n"
                f"{self._latest_version_info.get('url', '') if hasattr(self, '_latest_version_info') else 'URL no disponible'}"
            )
            return False    
    def update_with_prompt(self) -> bool:
        """
        Verifica actualizaciones y muestra un diálogo al usuario si hay una disponible.
        
        Returns:
            True si el usuario aceptó actualizar, False en caso contrario
        """
        if not self.check_for_updates():
            return False
        
        # Obtener información de la versión desde el servidor
        version_info = self.get_latest_version_info()
        latest_version = version_info.get('version', 'Desconocida') if version_info else 'Desconocida'
        changelog = version_info.get('changelog', '') if version_info else ""
        
        message = f"Hay una nueva versión disponible:\n\n"
        message += f"Versión actual: {self.current_version}\n"
        message += f"Nueva versión: {latest_version}\n\n"
        
        if changelog:
            message += f"Cambios:\n{changelog}\n\n"
        
        message += "¿Deseas descargar e instalar la actualización ahora?"
        
        response = messagebox.askyesno(
            "Actualización disponible",
            message
        )
        
        if response:
            # Descargar (que también instala)
            return self.download_update()
        
        return False
    
    def start_periodic_check(self, callback: Optional[Callable[[bool], None]] = None):
        """
        Inicia la verificación periódica de actualizaciones en segundo plano.
        
        Args:
            callback: Función opcional que se llama cuando se encuentra una actualización (recibe True)
        """
        if self._check_thread and self._check_thread.is_alive():
            self.logger.warning("La verificación periódica ya está en ejecución")
            return
        
        self._stop_checking.clear()
        
        def check_loop():
            while not self._stop_checking.is_set():
                try:
                    if self.check_for_updates():
                        if callback:
                            callback(True)
                        elif not self.auto_download:
                            # Si no hay callback y no es auto-download, mostrar notificación
                            self.logger.info("Actualización encontrada, esperando acción del usuario")
                    else:
                        if callback:
                            callback(False)
                except Exception as e:
                    self.logger.error(f"Error en verificación periódica: {str(e)}")
                
                # Esperar el intervalo o hasta que se detenga
                if self._stop_checking.wait(self.update_check_interval):
                    break
        
        self._check_thread = threading.Thread(target=check_loop, daemon=True)
        self._check_thread.start()
        self.logger.info(f"Verificación periódica iniciada (cada {self.update_check_interval} segundos)")
    
    def stop_periodic_check(self):
        """Detiene la verificación periódica de actualizaciones."""
        if self._check_thread and self._check_thread.is_alive():
            self._stop_checking.set()
            self._check_thread.join(timeout=5)
            self.logger.info("Verificación periódica detenida")
    
    def get_latest_version_info(self) -> Optional[dict]:
        """
        Obtiene información sobre la última versión disponible.
        
        Returns:
            Diccionario con información de la versión o None si hay error
        """
        try:
            import requests
            # Normalizar URL de GitHub a formato raw si es necesario
            normalized_url = _normalize_github_url(self.update_url)
            # Intentar obtener el archivo version.json del servidor
            base_url = normalized_url.rstrip('/')
            # Evitar duplicar version.json si ya está en la URL
            if base_url.endswith('/version.json'):
                version_url = base_url
            else:
                version_url = f"{base_url}/version.json"
            
            response = requests.get(version_url, timeout=10)
            if response.status_code == 200:
                # Verificar que la respuesta es JSON válido
                if not response.text.strip():
                    self.logger.error("La respuesta del servidor está vacía")
                    return None
                # Intentar parsear JSON con mejor manejo de errores
                try:
                    version_data = response.json()
                    return {
                        'version': version_data.get('version', 'Desconocida'),
                        'changelog': version_data.get('changelog', '')
                    }
                except ValueError as json_error:
                    # Mostrar los primeros caracteres de la respuesta para debugging
                    preview = response.text[:200] if len(response.text) > 200 else response.text
                    self.logger.error(
                        f"Error al parsear JSON. Status: {response.status_code}, "
                        f"Content-Type: {response.headers.get('Content-Type', 'unknown')}, "
                        f"Preview: {preview}"
                    )
                    return None
            return None
        except Exception as e:
            self.logger.error(f"Error al obtener información de versión: {str(e)}")
            return None
