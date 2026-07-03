import logging
from pal.core.updater import UpdateManager

# Configurar logging básico para ver qué hace el updater
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def simular_reinicio():
    print("¡El updater ha solicitado cerrar la app para aplicar la actualización!")

# 1. Configura el updater con versión 1.7.1
updater = UpdateManager(
    app_name="Casapro Nexus",
    current_version="1.1.0", 
    update_url="https://raw.githubusercontent.com/MrBearCr/nexus/main/updates/version.json?v=1"
)

print("1. Buscando actualizaciones...")
hay_actualizacion = updater.check_for_updates()

if hay_actualizacion:
    info = updater.get_latest_version_info()
    print(f"¡Actualización {info['version']} encontrada!")
    
    print("\n2. Descargando actualización...")
    if updater.download_update(progress_callback=lambda p: print(f"Progreso: {p*100:.1f}%")):
        
        print("\n3. Instalando actualización...")
        # Esto lanzará el .bat y cerrará el script actual
        if updater.install_update(restart_callback=simular_reinicio):
            print("Instalación lanzada correctamente.")
        else:
            print("Falló el lanzamiento de la instalación.")
    else:
        print("Falló la descarga.")
else:
    print("No se encontraron actualizaciones. Revisa la URL o las versiones.")
