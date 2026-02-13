import unittest
import json
from pal.core.config_manager import ConfigManager
from pal.infrastructure.database import DatabaseManager
from pal.core.credentials import SecureCredentialsManager
import datetime

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.cred_manager = SecureCredentialsManager()
        self.db_manager = DatabaseManager(self.cred_manager)
        self.config_manager = ConfigManager(self.db_manager)
        
    def test_save_and_load_sedes_config(self):
        # Data de prueba
        test_config = {
            "TestSede": {
                "descripcion": "Sede de Prueba Automática",
                "almacenes_tratables": ["0101", "0999"],
                "zona": "TestZone"
            }
        }
        
        # 1. Guardar
        print("Guardando configuración de prueba...")
        success = self.config_manager.save_sedes_config(test_config)
        self.assertTrue(success, "Debe guardar correctamente")
        
        # 2. Cargar
        print("Cargando configuración...")
        loaded_config = self.config_manager.get_sedes_config()
        
        # 3. Verificar
        print(f"Configuración cargada: {loaded_config}")
        self.assertIn("TestSede", loaded_config, "La sede de prueba debe existir")
        self.assertEqual(loaded_config["TestSede"]["almacenes_tratables"], ["0101", "0999"])
        
        # 4. Limpieza (Opcional, restaurar default o dejarlo)
        # Por ahora lo dejamos para verificar manualmente en UI si se quiere.
        
if __name__ == "__main__":
    unittest.main()
