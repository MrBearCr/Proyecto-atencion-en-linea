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
    
    sugerencias = service.calcular_abastecimiento_global()
    found = False
    with open('salida_12305.txt', 'w', encoding='utf-8') as f:
        for s in sugerencias:
            if str(s.get("producto_codigo")).strip().lstrip("0") == "12305":
                found = True
                f.write("="*50 + "\n")
                f.write(f"Producto: {s['producto_codigo']}\n")
                f.write(f"Destino: {s['sucursal_destino']}\n")
                f.write(f"Sugerencia Final: {s['cantidad_sugerida']}\n")
                f.write(f"Stock Actual: {s['stock_actual']}\n")
                f.write(f"Stock Origen CDT (usado): {s['stock_origen']}\n")
                f.write(f"Promedio: {s['promedio_diario']}\n")
                f.write(f"Es_Rojo: {s['es_rojo']}\n")
                
                dias_obj = s['dias_stock_objetivo']
                ideal = int(round(s['promedio_diario'] * dias_obj * 1.25 * 1.15))
                f.write(f"Stock Ideal Calculado (sin compromisos): {ideal}\n")

                sql_comp = "SELECT producto_codigo, sucursal_destino, cantidad_sugerida FROM pal_sugerencias_transferencia WHERE estado IN ('pendiente', 'aprobada', 'en_transito') AND producto_codigo=?"
                res = db.fetch_data(sql_comp, (s['producto_codigo'],))
                f.write(f"Compromisos en DB: {res}\n")
        
        if not found:
            f.write("Producto 12305 no encontrado en sugerencias globales.\n")

test()
