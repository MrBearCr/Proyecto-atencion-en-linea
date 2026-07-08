"""
MÃ³dulo de actualizaciÃ³n automÃ¡tica usando pyautoupdate.
Maneja la verificaciÃ³n y descarga de actualizaciones para la aplicaciÃ³n.
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
# Implementamos una soluciÃ³n personalizada usando requests
PY_AUTOUPDATE_AVAILABLE = True  # Siempre disponible con nuestra implementaciÃ³n


def _is_python_runtime(executable: str) -> bool:
    exe_name = os.path.basename(executable).lower()
    return exe_name in {"python.exe", "pythonw.exe", "python"} or exe_name.startswith("python3")


def _get_app_dir() -> str:
    """
    Devuelve la raiz real de la aplicacion.

    En Nuitka el modulo puede vivir bajo pal/core, pero sys.executable apunta al
    exe instalado en la raiz de Casapro Nexus. En desarrollo, sys.executable es
    python.exe y conviene mantener el directorio del modulo.
    """
    executable = os.path.abspath(sys.executable)
    if getattr(sys, 'frozen', False) or '__compiled__' in globals() or not _is_python_runtime(executable):
        return os.path.dirname(executable)
    return os.path.dirname(os.path.abspath(__file__))


def _find_updater_exe(app_dir: str, update_dir: str) -> Optional[str]:
    candidates = [
        os.path.join(app_dir, 'nexus_updater.exe'),
        os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'nexus_updater.exe'),
        os.path.join(update_dir, 'nexus_updater.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nexus_updater.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'updates', 'nexus_updater.exe'),
    ]

    seen = set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.abspath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if os.path.exists(candidate):
            return candidate
    return None


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
    
    # PatrÃ³n para URLs de GitHub web interface
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
    Gestor de actualizaciones automÃ¡ticas para la aplicaciÃ³n.
    
    Requiere:
    - Una URL base donde se alojan las versiones (ej: https://tu-servidor.com/updates/)
    - Un archivo version.json en esa URL con la estructura:
      {
          "version": "1.0.0",
          "url": "https://tu-servidor.com/updates/app-1.0.0.zip",
          "changelog": "DescripciÃ³n de cambios"
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
            app_name: Nombre de la aplicaciÃ³n
            current_version: VersiÃ³n actual de la aplicaciÃ³n (ej: "1.0.0")
            update_url: URL base donde se alojan las actualizaciones
            update_check_interval: Intervalo en segundos para verificar actualizaciones
            auto_download: Si True, descarga automÃ¡ticamente las actualizaciones
            auto_install: Si True, instala automÃ¡ticamente las actualizaciones (requiere auto_download=True)
        """
        # No necesitamos verificar pyautoupdate ya que usamos nuestra implementaciÃ³n
        
        self.app_name = app_name
        self.current_version = current_version
        self.update_url = update_url
        self.update_check_interval = update_check_interval
        self.auto_download = auto_download
        self.auto_install = auto_install
        
        self.app_dir = _get_app_dir()
        self.update_dir = os.path.join(self.app_dir, 'updates')
        os.makedirs(self.update_dir, exist_ok=True)
        
        # Almacenar configuraciÃ³n
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
            
            # Obtener informaciÃ³n de versiÃ³n del servidor
            # Asegurar que la URL termine sin / y luego agregar version.json
            base_url = normalized_url.rstrip('/')
            # Evitar duplicar version.json si ya estÃ¡ en la URL
            if base_url.endswith('/version.json'):
                version_url = base_url
            else:
                version_url = f"{base_url}/version.json"
            
            self.logger.debug(f"Fetching version info from: {version_url}")
            
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            
            # Verificar que la respuesta es JSON vÃ¡lido
            if not response.text.strip():
                self.logger.warning("Server response is empty when checking for updates.")
                raise ValueError("La respuesta del servidor estÃ¡ vacÃ­a")
            
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
                self.logger.info(f"ActualizaciÃ³n disponible: {latest_version} (actual: {self.current_version})")
                self._latest_version_info = version_data  # Guardar para uso posterior
                return True
            else:
                if show_no_update_message:
                    messagebox.showinfo(
                        "Actualizaciones",
                        f"Ya tienes la versiÃ³n mÃ¡s reciente ({self.current_version})"
                    )
                self.logger.info(f"No hay actualizaciones disponibles. VersiÃ³n actual ({self.current_version}) es la mÃ¡s reciente o posterior a la del servidor ({latest_version}).")
                return False
                
        except Exception as e:
            self.logger.error(f"Error al verificar actualizaciones: {str(e)}")
            if show_no_update_message:
                messagebox.showerror(
                    "Error de actualizaciÃ³n",
                    f"No se pudo verificar actualizaciones: {str(e)}"
                )
            return False
    
    def download_update(self, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Descarga la actualizaciÃ³n disponible.
        
        Args:
            progress_callback: FunciÃ³n opcional que recibe el progreso (0.0 a 1.0)
            
        Returns:
            True si la descarga fue exitosa, False en caso contrario
        """
        self.logger.debug("Entering download_update.")
        try:
            import requests
            
            self.logger.info("Iniciando descarga de actualizaciÃ³n...")
            
            # Obtener URL de descarga desde version.json
            if not hasattr(self, '_latest_version_info') or self._latest_version_info is None:
                self.logger.warning("No _latest_version_info found, attempting to check for updates.")
                if not self.check_for_updates():
                    self.logger.error("No update information available after re-check.")
                    return False
            
            download_url = self._latest_version_info.get('url', '')
            if not download_url:
                self.logger.error("No se encontrÃ³ URL de descarga en version.json")
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
            
            self.logger.info(f"ActualizaciÃ³n descargada exitosamente. Guardado en {zip_path}")
            self._downloaded_zip = zip_path
            return True
                
        except Exception as e:
            self.logger.error(f"Error al descargar actualizaciÃ³n: {str(e)}")
            messagebox.showerror(
                "Error de descarga",
                f"No se pudo descargar la actualizaciÃ³n: {str(e)}"
            )
            return False
    
    def install_update(self, restart_callback: Optional[Callable[[], None]] = None) -> bool:
        """
        Instala la actualizaciÃ³n descargada.
        
        Para aplicaciones instaladas con Inno Setup, ejecuta el instalador descargado.
        Para aplicaciones portables, extrae el ZIP.
        
        Args:
            restart_callback: FunciÃ³n opcional para reiniciar la aplicaciÃ³n despuÃ©s de la instalaciÃ³n
            
        Returns:
            True si la instalaciÃ³n fue exitosa, False en caso contrario
        """
        self.logger.debug("Entering install_update.")
        
        log_file = os.path.join(self.update_dir, 'update.log')
        # Limpiar el archivo de log anterior si existe
        if os.path.exists(log_file):
            os.remove(log_file)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # Evitar duplicar handlers si la funciÃ³n se llama varias veces
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_file for h in self.logger.handlers):
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
            self.logger.info("checkpass: log file created")
        
        try:
            if not hasattr(self, '_downloaded_zip') or not os.path.exists(self._downloaded_zip):
                self.logger.error("No hay archivo de actualizaciÃ³n descargado (_downloaded_zip no existe o archivo no encontrado)")
                return False
            
            self.logger.info("Instalando actualizaciÃ³n...")
            self.logger.debug(f"Downloaded ZIP file: {self._downloaded_zip}")

            updater_exe = _find_updater_exe(self.app_dir, self.update_dir)
            if not updater_exe:
                self.logger.error(
                    f"No se encontro nexus_updater.exe. app_dir={self.app_dir}, update_dir={self.update_dir}"
                )
                messagebox.showerror(
                    "Error de actualizacion",
                    "No se encontro nexus_updater.exe junto a la aplicacion.\n\n"
                    "Comunicate con tu departamento de Soporte."
                )
                return False

            import tempfile
            import uuid

            temp_updater_exe = os.path.join(
                tempfile.gettempdir(), f"nexus_updater_{uuid.uuid4().hex}.exe"
            )
            shutil.copy2(updater_exe, temp_updater_exe)

            updater_log = os.path.join(self.update_dir, 'nexus_updater.log')
            command = [
                temp_updater_exe,
                '--update-file', self._downloaded_zip,
                '--app-exe', sys.executable,
                '--parent-pid', str(os.getpid()),
                '--log-file', updater_log,
            ]

            self.logger.info(f"Lanzando actualizador externo: {temp_updater_exe}")
            self.logger.debug(f"Updater command: {command}")

            try:
                subprocess.Popen(
                    command,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True
                )
                self.logger.info("Actualizador externo iniciado.")
                self.logger.info("checkpass: updater executable launched")

                if restart_callback:
                    self.logger.info("Llamando a restart_callback para cerrar la aplicacion.")
                    self.logger.info("checkpass: application closing")
                    restart_callback()
                else:
                    self.logger.info("restart_callback no proporcionado. Forzando salida con os._exit(0).")
                    self.logger.info("checkpass: application closing")
                    os._exit(0)

                self.logger.info("install_update completado exitosamente.")
                return True
            except Exception as e:
                self.logger.error(f"Error al lanzar el actualizador externo: {str(e)}")
                messagebox.showerror(
                    "Error de actualizacion",
                    f"No se pudo iniciar el proceso de actualizacion: {str(e)}"
                )
                return False
            
        except Exception as e:
            self.logger.error(f"Error al instalar actualizaciÃ³n: {str(e)}")
            messagebox.showerror(
                "Error de instalaciÃ³n",
                f"No se pudo instalar la actualizaciÃ³n: {str(e)}\n\n"
                "Por favor, descarga e instala manualmente desde:\n"
                f"{self._latest_version_info.get('url', '') if hasattr(self, '_latest_version_info') else 'URL no disponible'}"
            )
            return False    
    def update_with_prompt(self) -> bool:
        """
        Verifica actualizaciones y muestra un diÃ¡logo al usuario si hay una disponible.
        
        Returns:
            True si el usuario aceptÃ³ actualizar, False en caso contrario
        """
        if not self.check_for_updates():
            return False
        
        # Obtener informaciÃ³n de la versiÃ³n desde el servidor
        version_info = self.get_latest_version_info()
        latest_version = version_info.get('version', 'Desconocida') if version_info else 'Desconocida'
        changelog = version_info.get('changelog', '') if version_info else ""
        
        message = f"Hay una nueva versiÃ³n disponible:\n\n"
        message += f"VersiÃ³n actual: {self.current_version}\n"
        message += f"Nueva versiÃ³n: {latest_version}\n\n"
        
        if changelog:
            message += f"Cambios:\n{changelog}\n\n"
        
        message += "Â¿Deseas descargar e instalar la actualizaciÃ³n ahora?"
        
        response = messagebox.askyesno(
            "ActualizaciÃ³n disponible",
            message
        )
        
        if response:
            # Descargar (que tambiÃ©n instala)
            return self.download_update()
        
        return False
    
    def start_periodic_check(self, callback: Optional[Callable[[bool], None]] = None):
        """
        Inicia la verificaciÃ³n periÃ³dica de actualizaciones en segundo plano.
        
        Args:
            callback: FunciÃ³n opcional que se llama cuando se encuentra una actualizaciÃ³n (recibe True)
        """
        if self._check_thread and self._check_thread.is_alive():
            self.logger.warning("La verificaciÃ³n periÃ³dica ya estÃ¡ en ejecuciÃ³n")
            return
        
        self._stop_checking.clear()
        
        def check_loop():
            while not self._stop_checking.is_set():
                try:
                    if self.check_for_updates():
                        if callback:
                            callback(True)
                        elif not self.auto_download:
                            # Si no hay callback y no es auto-download, mostrar notificaciÃ³n
                            self.logger.info("ActualizaciÃ³n encontrada, esperando acciÃ³n del usuario")
                    else:
                        if callback:
                            callback(False)
                except Exception as e:
                    self.logger.error(f"Error en verificaciÃ³n periÃ³dica: {str(e)}")
                
                # Esperar el intervalo o hasta que se detenga
                if self._stop_checking.wait(self.update_check_interval):
                    break
        
        self._check_thread = threading.Thread(target=check_loop, daemon=True)
        self._check_thread.start()
        self.logger.info(f"VerificaciÃ³n periÃ³dica iniciada (cada {self.update_check_interval} segundos)")
    
    def stop_periodic_check(self):
        """Detiene la verificaciÃ³n periÃ³dica de actualizaciones."""
        if self._check_thread and self._check_thread.is_alive():
            self._stop_checking.set()
            self._check_thread.join(timeout=5)
            self.logger.info("VerificaciÃ³n periÃ³dica detenida")
    
    def get_latest_version_info(self) -> Optional[dict]:
        """
        Obtiene informaciÃ³n sobre la Ãºltima versiÃ³n disponible.
        
        Returns:
            Diccionario con informaciÃ³n de la versiÃ³n o None si hay error
        """
        try:
            import requests
            # Normalizar URL de GitHub a formato raw si es necesario
            normalized_url = _normalize_github_url(self.update_url)
            # Intentar obtener el archivo version.json del servidor
            base_url = normalized_url.rstrip('/')
            # Evitar duplicar version.json si ya estÃ¡ en la URL
            if base_url.endswith('/version.json'):
                version_url = base_url
            else:
                version_url = f"{base_url}/version.json"
            
            response = requests.get(version_url, timeout=10)
            if response.status_code == 200:
                # Verificar que la respuesta es JSON vÃ¡lido
                if not response.text.strip():
                    self.logger.error("La respuesta del servidor estÃ¡ vacÃ­a")
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
            self.logger.error(f"Error al obtener informaciÃ³n de versiÃ³n: {str(e)}")
            return None
