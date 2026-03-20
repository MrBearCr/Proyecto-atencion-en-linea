
import sys
import os

# Mocking enough to run the logic
class Logger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

logger = Logger()

def test_dynamic_logic(sedes_config):
    if sedes_config:
        GRUPOS_DEPOSITOS = {}
        # 1. Grupos por Sede (Tratables)
        for s_name, s_cfg in sedes_config.items():
            deps = s_cfg.get('almacenes_tratables', [])
            if deps:
                GRUPOS_DEPOSITOS[f'Stock {s_name}'] = deps
        
        # 2. CDT consolidado
        cdts = []
        for s_cfg in sedes_config.values():
            cdts.extend(s_cfg.get('almacenes_cdt', []))
        if cdts:
            GRUPOS_DEPOSITOS['CDT'] = sorted(list(set(cdts)))
        
        # 3. Transito consolidado (Nueva lógica es_transito)
        transitos = []
        for s_cfg in sedes_config.values():
            transitos.extend(s_cfg.get('almacenes_transito', []))
        if transitos:
            GRUPOS_DEPOSITOS['Transito SEDES'] = sorted(list(set(transitos)))
        
        print(f"Groups: {GRUPOS_DEPOSITOS}")
    else:
        print("Using Fallback")
        GRUPOS_DEPOSITOS = {
            'Stock Cabudare': ['0301', '0302'],
            'Stock Barinas':  ['0101', '0102', '0108'],
            'Stock Guanare':  ['0401', '0402'],
            'CDT':            ['0106'],
            'Transito SEDES': ['0104', '0110', '0112']
        }
        print(f"Groups: {GRUPOS_DEPOSITOS}")

    headers = [
        'Código', 'Descripción', 'Departamento', 'Grupo', 'Subgrupo', 'Marca', 
        'Sede de Quiebre', 'Unid. Perdidas', 'Días Quiebre', 'Últ. Liquidación', 'Últ. Venta'
    ]
    
    for group_name in GRUPOS_DEPOSITOS.keys():
        headers.append(group_name)
    
    headers.append('Stock Total')
    print(f"Headers: {headers}")

# Test Case 1: Dynamic config with Transito
mock_config = {
    "Barinas": {
        "almacenes_tratables": ["0101", "0108"],
        "almacenes_cdt": ["0106"],
        "almacenes_transito": ["0104"]
    },
    "Cabudare": {
        "almacenes_tratables": ["0301"],
        "almacenes_transito": ["0110"]
    }
}
print("--- TEST 1: DYNAMIC ---")
test_dynamic_logic(mock_config)

# Test Case 2: Fallback
print("\n--- TEST 2: FALLBACK ---")
test_dynamic_logic(None)
