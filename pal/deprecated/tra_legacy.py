"""
Lógica de TRA legada (detección de quiebres dentro de TRA)
"""

def detectar_alertas_rotacion_alta(ventas_clasificadas, alertas_stock, rotaciones_objetivo=["ALTA", "MEDIA"]):
    """
    Detecta productos de alta/media rotación que tienen alerta de stock (LEGACY)
    """
    try:
        productos_criticos = []
        alertas_map = {str(r[0]).strip(): r for r in alertas_stock} if alertas_stock else {}
        
        for venta in ventas_clasificadas:
            if not venta or len(venta) < 7:
                continue
                
            codigo = str(venta[0]).strip()
            descripcion = str(venta[1]) if len(venta) > 1 else ""
            rotacion = str(venta[6]) if len(venta) > 6 else "BAJA"
            
            if rotacion in rotaciones_objetivo and codigo in alertas_map:
                alerta = alertas_map[codigo]
                if len(alerta) >= 4:
                    stock = alerta[2]
                    nivel_alerta = alerta[3]
                    productos_criticos.append({
                        'codigo': codigo,
                        'descripcion': descripcion,
                        'stock': stock,
                        'nivel': nivel_alerta,
                        'rotacion': rotacion
                    })
        return productos_criticos
    except Exception:
        return []

def generar_reporte_critico_rotacion(productos_criticos):
    """
    Genera un reporte resumido para el departamento de compras (LEGACY)
    """
    try:
        if not productos_criticos:
            return {'total': 0, 'por_rotacion': {}, 'por_nivel': {}, 'productos': []}
        
        reporte = {
            'total': len(productos_criticos),
            'por_rotacion': {},
            'por_nivel': {},
            'productos': productos_criticos
        }
        for p in productos_criticos:
            rotacion = p.get('rotacion', 'DESCONOCIDO')
            reporte['por_rotacion'][rotacion] = reporte['por_rotacion'].get(rotacion, 0) + 1
            nivel = p.get('nivel', 'DESCONOCIDO')
            reporte['por_nivel'][nivel] = reporte['por_nivel'].get(nivel, 0) + 1
        return reporte
    except Exception:
        return {'total': 0, 'por_rotacion': {}, 'por_nivel': {}, 'productos': []}
