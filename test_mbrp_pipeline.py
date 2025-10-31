#!/usr/bin/env python3
"""
Test script to validate MBRP pipeline functions in isolation.
Run this to verify filtering and classification work correctly.

Usage:
    python test_mbrp_pipeline.py
"""

from pal.services.mbrp import (
    calcular_indice_movilidad,
    filtrar_productos_baja_rotacion,
    clasificar_rotacion_mbrp,
)
from pal.core.log import get_logger

logger = get_logger("TEST_MBRP")


def test_pipeline():
    """Test the MBRP pipeline with synthetic data"""
    
    # Create synthetic sales data (6 fields: codigo, desc, dept, grupo, subgrupo, neto)
    synthetic_data = [
        ("PROD001", "Producto 1", "DEPT1", "GRP1", "SUB1", 1000.0),
        ("PROD002", "Producto 2", "DEPT1", "GRP1", "SUB1", 500.0),
        ("PROD003", "Producto 3", "DEPT1", "GRP1", "SUB1", 100.0),
        ("PROD004", "Producto 4", "DEPT1", "GRP1", "SUB1", 50.0),
        ("PROD005", "Producto 5", "DEPT1", "GRP1", "SUB1", 0.0),  # Sin ventas
    ]
    
    print("\n" + "="*70)
    print("MBRP PIPELINE TEST")
    print("="*70)
    
    # Test 1: Calculate Índice de Movilidad
    print("\n1. Testing calcular_indice_movilidad()...")
    print(f"   Input: {len(synthetic_data)} products")
    
    indices = calcular_indice_movilidad(synthetic_data)
    print(f"   Output: {len(indices)} indices calculated")
    
    if not indices:
        print("   ❌ FAILED: No indices calculated!")
        return False
    
    for codigo, im in indices.items():
        print(f"      {codigo}: IM = {im}%")
    
    # Test 2: Filter by Índice de Movilidad
    print("\n2. Testing filtrar_productos_baja_rotacion()...")
    print(f"   Input: {len(synthetic_data)} products, umbral_im=30.0")
    
    filtered = filtrar_productos_baja_rotacion(synthetic_data, umbral_im=30.0)
    print(f"   Output: {len(filtered)} products filtered")
    
    if not filtered:
        print("   ❌ FAILED: No products filtered!")
        return False
    
    for item in filtered:
        print(f"      {item[0]}: neto={item[5]}, IM={indices.get(item[0], 'N/A')}%")
    
    # Test 3: Classify rotation
    print("\n3. Testing clasificar_rotacion_mbrp()...")
    print(f"   Input: {len(filtered)} products to classify")
    
    classified = clasificar_rotacion_mbrp(filtered)
    print(f"   Output: {len(classified)} products classified")
    
    if not classified:
        print("   ❌ FAILED: No products classified!")
        return False
    
    for item in classified:
        rotacion = item[6] if len(item) > 6 else "N/A"
        print(f"      {item[0]}: rotacion={rotacion}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70 + "\n")
    return True


if __name__ == "__main__":
    try:
        test_pipeline()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
