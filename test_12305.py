def test():
    import configparser
    from pal.infrastructure.database import DatabaseManager
    from pal.services.abastecimiento import AbastecimientoService
    from pal.core.credentials import SecureCredentialsManager

    config = configparser.ConfigParser()
    config.read('db_config.ini')

    try:
        mgr = SecureCredentialsManager()
        server = mgr.decrypt(config['Database']['server'])
        database = mgr.decrypt(config['Database']['database'])
        user = mgr.decrypt(config['Database']['user'])
        password = mgr.decrypt(config['Database']['password'])
    except Exception:
        server = config['Database'].get('server', '')
        database = config['Database'].get('database', '')
        user = config['Database'].get('user', '')
        password = config['Database'].get('password', '')
        
    db = DatabaseManager()
    if not db.connect(server, database, user, password):
        print("db falló")
        return
        
    service = AbastecimientoService(db)
    
    with open('salida_12305.txt', 'w', encoding='utf-8') as f:
        # Primero: diagnosticar compromisos en la tabla NUEVA
        f.write("="*60 + "\n")
        f.write("DIAGNOSTICO DE COMPROMISOS (pal_compromisos_inventario)\n")
        f.write("="*60 + "\n")
        
        sql_all_comp = "SELECT producto_codigo, sucursal_destino, cantidad, estado, referencia_maestro, fecha_creacion FROM pal_compromisos_inventario ORDER BY fecha_creacion DESC"
        all_comp = db.fetch_data(sql_all_comp)
        if all_comp:
            for c in all_comp:
                f.write(f"  Producto: {c[0]} | Destino: {c[1]} | Cantidad: {c[2]} | Estado: {c[3]} | RefMaestro: {c[4]} | Fecha: {c[5]}\n")
        else:
            f.write("  NO HAY COMPROMISOS en pal_compromisos_inventario\n")
        
        # Compromisos activos específicos para producto 12305
        f.write("\n--- Compromisos ACTIVOS para producto 12305 ---\n")
        sql_comp_12305 = "SELECT producto_codigo, sucursal_destino, cantidad, estado FROM pal_compromisos_inventario WHERE producto_codigo = '12305' AND estado = 'activo'"
        comp_12305 = db.fetch_data(sql_comp_12305)
        if comp_12305:
            for c in comp_12305:
                f.write(f"  Destino: {c[1]} | Cantidad: {c[2]} | Estado: {c[3]}\n")
        else:
            f.write("  No hay compromisos activos para 12305\n")
        
        # También verificar en tabla antigua por comparación
        f.write("\n--- Compromisos en tabla ANTIGUA (pal_sugerencias_transferencia) para 12305 ---\n")
        sql_old = "SELECT producto_codigo, sucursal_destino, cantidad_sugerida, estado FROM pal_sugerencias_transferencia WHERE producto_codigo = '12305' AND estado IN ('pendiente', 'aprobada', 'en_transito')"
        old_comp = db.fetch_data(sql_old)
        if old_comp:
            for c in old_comp:
                f.write(f"  Destino: {c[1]} | Cantidad: {c[2]} | Estado: {c[3]}\n")
        else:
            f.write("  No hay compromisos en tabla antigua para 12305\n")
        
        # Ahora ejecutar el cálculo global
        f.write("\n" + "="*60 + "\n")
        f.write("RESULTADO DEL CALCULO GLOBAL\n")
        f.write("="*60 + "\n")
        
        sugerencias = service.calcular_abastecimiento_global()
        found = False
        for s in sugerencias:
            if str(s.get("producto_codigo")).strip().lstrip("0") == "12305":
                found = True
                f.write(f"\nProducto: {s['producto_codigo']}\n")
                f.write(f"Destino: {s['sucursal_destino']}\n")
                f.write(f"Sugerencia Final: {s['cantidad_sugerida']}\n")
                f.write(f"Stock Actual: {s['stock_actual']}\n")
                f.write(f"Stock Origen CDT (usado): {s['stock_origen']}\n")
                f.write(f"Promedio: {s['promedio_diario']}\n")
                f.write(f"Es_Rojo: {s['es_rojo']}\n")
                f.write(f"Dias Objetivo: {s['dias_stock_objetivo']}\n")
                
                dias_obj = s['dias_stock_objetivo']
                ideal = int(round(s['promedio_diario'] * dias_obj * 1.25 * 1.15))
                f.write(f"Stock Ideal (sin compromisos): {ideal}\n")
                
                # Calcular qué compromiso se debería haber usado
                compromiso_esperado = 0
                if comp_12305:
                    for c in comp_12305:
                        if str(c[1]).strip().upper() == str(s['sucursal_destino']).strip().upper():
                            compromiso_esperado = float(c[2])
                f.write(f"Compromiso esperado para esta sede: {compromiso_esperado}\n")
                
                # Verificar que el deficit NO incluye el compromiso (se resta después)
                deficit_sin_compromiso = max(0, ideal - s['stock_actual'])
                f.write(f"Deficit (ideal - stock, SIN compromiso): {deficit_sin_compromiso}\n")
                
                # Verificar que la sugerencia final = distribuido - compromiso
                f.write(f"Sugerencia: {s['cantidad_sugerida']} = distribuido - compromiso({compromiso_esperado})\n")
                f.write(f"  => distribuido estimado = {s['cantidad_sugerida'] + compromiso_esperado}\n")
                f.write("-"*40 + "\n")
        
        if not found:
            f.write("\nProducto 12305 NO encontrado en sugerencias globales.\n")
        
        # Verificar configuración de sedes
        f.write("\n" + "="*60 + "\n")
        f.write("CONFIGURACION DE SEDES\n")
        f.write("="*60 + "\n")
        from pal.core.config_manager import ConfigManager
        config_mgr = ConfigManager(db)
        sedes = config_mgr.get_sedes_config()
        for nombre, cfg in sedes.items():
            f.write(f"  Sede: '{nombre}' | Almacenes: {cfg.get('almacenes_tratables', [])} | CDT: {cfg.get('almacenes_cdt', [])}\n")

test()
