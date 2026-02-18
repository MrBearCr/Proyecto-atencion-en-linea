import json
from datetime import datetime
from pal.core.log import get_logger

logger = get_logger("CONFIG")

class ConfigManager:
    """
    Manager centralizado para configuraciones almacenadas en la base de datos via pal_global_settings.
    """
    
    KEY_SEDES_CONFIG = "sedes_config"
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    def get_sedes_config(self):
        """
        Obtiene la configuración de sedes y sus almacenes tratables.
        
        Returns:
            dict: {
                "NombreSede": {
                    "descripcion": "...",
                    "almacenes_tratables": ["0101", "0102", ...],
                    "zona": "..."
                },
                ...
            }
        """
        try:
            # Intentar leer de DB
            sql = "SELECT setting_value FROM pal_global_settings WHERE setting_key = ?"
            result = self.db_manager.fetch_data(sql, (self.KEY_SEDES_CONFIG,))
            
            if result and result[0][0]:
                return json.loads(result[0][0])
            
            # Default config si no existe
            return {
                "Barinas": {
                    "descripcion": "Sede Principal Barinas",
                    "almacenes_tratables": ["0101", "0108"],
                    "zona": "Llanos"
                },
                "Cabudare": {
                    "descripcion": "Sede Cabudare",
                    "almacenes_tratables": ["0301"],
                    "zona": "Centro"
                },
                "Guanare": {
                    "descripcion": "Sede Guanare",
                    "almacenes_tratables": ["0401", "0402"],
                    "zona": "Llanos"
                }
            }
            
        except Exception as e:
            logger.error(f"Error cargando configuración de sedes: {e}")
            return {}

    def save_sedes_config(self, config_data):
        """
        Guarda la configuración de sedes.
        
        Args:
            config_data (dict): Diccionario de configuración completo
            
        Returns:
            bool: True si tuvo éxito
        """
        try:
            json_str = json.dumps(config_data, ensure_ascii=False)
            
            # Verificar si existe
            check_sql = "SELECT 1 FROM pal_global_settings WHERE setting_key = ?"
            exists = self.db_manager.fetch_data(check_sql, (self.KEY_SEDES_CONFIG,))
            
            if exists:
                sql = """
                    UPDATE pal_global_settings 
                    SET setting_value = ?, last_modified = GETDATE()
                    WHERE setting_key = ?
                """
                self.db_manager.execute_query(sql, (json_str, self.KEY_SEDES_CONFIG))
            else:
                sql = """
                    INSERT INTO pal_global_settings (setting_key, setting_value, description, last_modified)
                    VALUES (?, ?, 'Configuración de sedes y almacenes tratables para Quiebre de Stock', GETDATE())
                """
                self.db_manager.execute_query(sql, (self.KEY_SEDES_CONFIG, json_str))
                
            return True
            
        except Exception as e:
            logger.error(f"Error guardando configuración de sedes: {e}")
            return False

    def get_setting(self, key: str, default=None):
        """
        Obtiene una configuración genérica por clave.
        
        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe
            
        Returns:
            El valor almacenado o el default
        """
        try:
            sql = "SELECT setting_value FROM pal_global_settings WHERE setting_key = ?"
            result = self.db_manager.fetch_data(sql, (key,))
            
            if result and result[0][0]:
                value = result[0][0]
                # Intentar parsear como JSON
                try:
                    return json.loads(value)
                except:
                    return value
            
            return default
        except Exception as e:
            logger.error(f"Error get_setting({key}): {e}")
            return default

    def set_setting(self, key: str, value, description: str = ""):
        """
        Guarda una configuración genérica.
        
        Args:
            key: Clave de configuración
            value: Valor a guardar (se convertirá a JSON si es dict/list)
            description: Descripción opcional
            
        Returns:
            bool: True si tuvo éxito
        """
        try:
            if isinstance(value, (dict, list)):
                json_str = json.dumps(value, ensure_ascii=False)
            else:
                json_str = str(value)
            
            # Verificar si existe
            check_sql = "SELECT 1 FROM pal_global_settings WHERE setting_key = ?"
            exists = self.db_manager.fetch_data(check_sql, (key,))
            
            if exists:
                sql = """
                    UPDATE pal_global_settings 
                    SET setting_value = ?, last_modified = GETDATE()
                    WHERE setting_key = ?
                """
                self.db_manager.execute_query(sql, (json_str, key))
            else:
                sql = """
                    INSERT INTO pal_global_settings (setting_key, setting_value, description, last_modified)
                    VALUES (?, ?, ?, GETDATE())
                """
                self.db_manager.execute_query(sql, (key, json_str, description or f"Configuración: {key}"))
                
            return True
        except Exception as e:
            logger.error(f"Error set_setting({key}): {e}")
            return False

    def get_sales_warehouses(self):
        """
        Obtiene TODOS los almacenes que se consideran para análisis de ventas (Global/ICH).
        Por ahora esto puede ser la unión de todos los almacenes tratables o una lista fija global
        si se requiere separar scope.
        """
        # Por defecto, devolvemos 'ICH' o una lista de todos los almacenes conocidos para ventas
        # O podríamos leer otra key 'global_sales_warehouses' si existiera.
        # Para TRA, generalmente se filtra por 'sedes' en la UI, pero el cálculo base
        # suele ser sobre toda la data disponible.
        return ["0101", "0102", "0108", "0301", "0401", "0402", "0106"]
