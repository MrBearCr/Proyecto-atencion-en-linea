import logging
from datetime import datetime
from pal.core.log import get_logger

logger = get_logger(__name__)

class AbastecimientoService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_red_list(self):
        """Obtiene todos los productos activos en la lista roja."""
        try:
            query = """
                SELECT id, producto_codigo, sede_destino, motivo, fecha_registro
                FROM pal_productos_no_trasladables
                WHERE activo = 1
                ORDER BY fecha_registro DESC
            """
            return self.db_manager.fetch_data(query) or []
        except Exception as e:
            logger.error(f"Error obteniendo lista roja: {e}")
            return []

    def add_to_red_list(self, producto_codigo, sede_destino, motivo, usuario_id=None):
        """Agrega un producto a la lista roja."""
        try:
            query = """
                INSERT INTO pal_productos_no_trasladables 
                (producto_codigo, sede_destino, motivo, usuario_id) 
                VALUES (?, ?, ?, ?)
            """
            # sede_destino = None means it applies to all branches
            self.db_manager.execute_query(query, (producto_codigo, sede_destino, motivo, usuario_id))
            return True
        except Exception as e:
            logger.error(f"Error agregando a lista roja: {e}")
            return False

    def remove_from_red_list(self, id_registro):
        """Desactiva un producto de la lista roja."""
        try:
            query = """
                UPDATE pal_productos_no_trasladables 
                SET activo = 0 
                WHERE id = ?
            """
            self.db_manager.execute_query(query, (id_registro,))
            return True
        except Exception as e:
            logger.error(f"Error removiendo de lista roja: {e}")
            return False

    # --- MÉTODOS AUXILIARES DE CÁLCULO ---

    def _build_stock_query(self, almacenes, dept_cod, group_cod, sub_cod):
        """Construye la query de stock aplicando filtros jerárquicos."""
        placeholders = ",".join(["?"] * len(almacenes))
        where_filtros = ""
        filtros_params = []
        if dept_cod or group_cod or sub_cod:
            conds = []
            if dept_cod: conds.append("p.c_departamento = ?"); filtros_params.append(dept_cod)
            if group_cod: conds.append("p.c_grupo = ?"); filtros_params.append(group_cod)
            if sub_cod: conds.append("p.c_subgrupo = ?"); filtros_params.append(sub_cod)
            where_filtros = " AND " + " AND ".join(conds)

        sql = f"""
            SELECT d.c_codarticulo, SUM(d.n_cantidad) as stock_actual, MAX(p.c_grupo) as cat_id,
                   MAX(p.cu_descripcion_corta) as desc_corta, MAX(p.C_DESCRI) as desc_larga
            FROM MA_DEPOPROD d WITH (NOLOCK)
            JOIN MA_PRODUCTOS p WITH (NOLOCK) ON d.c_codarticulo = p.c_codigo
            WHERE d.c_coddeposito IN ({placeholders}){where_filtros}
            GROUP BY d.c_codarticulo
        """
        return sql, tuple(almacenes) + tuple(filtros_params)

    def _cargar_lista_roja(self, sede_destino):
        """Obtiene el conjunto de códigos de productos rojos para una sede."""
        sql_rojos = "SELECT producto_codigo FROM pal_productos_no_trasladables WHERE (sede_destino = ? OR sede_destino IS NULL) AND activo = 1"
        res_rojos = self.db_manager.fetch_data(sql_rojos, (sede_destino,))
        return {str(r[0]).strip().lstrip('0') or "0" for r in res_rojos}

    def _cargar_odc_activas(self):
        """
        Carga todas las ODC activas (status='DPE') desde MA_ODC/TR_ODC.
        Retorna dict agrupado por (localidad_destino, codigo_producto_normalizado).
        Formato: {(localidad, cod_producto): [{"documento": ..., "cantidad": ..., "fecha": ...}]}
        """
        try:
            sql = """
                SELECT m.c_DOCUMENTO, t.c_CODARTICULO, t.n_cantidad, m.d_fecha, m.c_CODLOCALIDAD
                FROM MA_ODC m WITH (NOLOCK)
                INNER JOIN TR_ODC t WITH (NOLOCK) ON m.c_DOCUMENTO = t.c_DOCUMENTO
                WHERE m.c_status = 'DPE'
                ORDER BY m.d_fecha DESC
            """
            rows = self.db_manager.fetch_data(sql)
            if not rows:
                logger.info("No se encontraron ODC activas.")
                return {}

            odc_dict = {}
            for doc, cod_art, qty, fecha, localidad in rows:
                cod_norm = str(cod_art).strip().lstrip('0') or "0"
                loc_norm = str(localidad).strip().upper() if localidad else ""
                key = (loc_norm, cod_norm)
                if key not in odc_dict:
                    odc_dict[key] = []
                odc_dict[key].append({
                    "documento": str(doc).strip(),
                    "cantidad": float(qty or 0),
                    "fecha": fecha
                })

            logger.info(f"ODC activas cargadas: {len(odc_dict)} combinaciones (localidad, producto)")
            return odc_dict
        except Exception as e:
            logger.warning(f"Error cargando ODC activas (se continúa sin ODC): {e}")
            return {}

    def _verificar_odc_producto(self, odc_dict, codigo_producto, codigo_localidad):
        """
        Verifica si un producto tiene ODC activa para una localidad destino.
        codigo_localidad: código de localidad (ej: '01', '03', '04') desde la config de sede.
        Retorna (tiene_odc: bool, info_odc: list|None)
        """
        if not codigo_localidad:
            return False, None
        cod_norm = str(codigo_producto).strip().lstrip('0') or "0"
        loc_norm = str(codigo_localidad).strip().upper()
        info = odc_dict.get((loc_norm, cod_norm))
        if info:
            return True, info
        return False, None

    def get_compromisos_activos(self, sede_destino=None):
        """
        Obtiene los compromisos de inventario activos deducibles de futuras sugerencias.
        Retorna un dict con estructura {codigo_producto: {sede_destino: cantidad_comprometida}}
        """
        try:
            query = "SELECT producto_codigo, sucursal_destino, sum(cantidad) as total_comprometido FROM pal_compromisos_inventario WHERE estado = 'activo'"
            params = []
            if sede_destino:
                query += " AND sucursal_destino = ?"
                params.append(sede_destino)
            query += " GROUP BY producto_codigo, sucursal_destino"
            
            res_comp = self.db_manager.fetch_data(query, tuple(params))
            compromisos = {}
            for c_cod, c_sede, c_qty in (res_comp or []):
                c_cod_norm = str(c_cod).strip().lstrip('0') or "0"
                c_sede_norm = str(c_sede).strip().upper()
                if c_cod_norm not in compromisos: compromisos[c_cod_norm] = {}
                compromisos[c_cod_norm][c_sede_norm] = float(c_qty)
            return compromisos
        except Exception as e:
            logger.error(f"Error obteniendo compromisos de inventario: {e}")
            return {}

    def _cargar_stock_cdt(self, codigos, sedes_cdt):
        """Carga el stock disponible en los CDTs para los códigos dados."""
        if not codigos or not sedes_cdt: return {}
        stock_cdt = {}
        placeholders_cdt = ",".join(["?"] * len(sedes_cdt))
        
        # Procesar por chunks para evitar errores de SQL
        chunk_size = 500
        for i in range(0, len(codigos), chunk_size):
            chunk = codigos[i:i+chunk_size]
            placeholders_cods = ",".join(["?"] * len(chunk))
            sql = f"""
                SELECT c_codarticulo, c_coddeposito, n_cantidad 
                FROM MA_DEPOPROD WITH (NOLOCK) 
                WHERE c_codarticulo IN ({placeholders_cods}) 
                AND c_coddeposito IN ({placeholders_cdt}) 
                AND n_cantidad > 0
            """
            res_bulk = self.db_manager.fetch_data(sql, tuple(chunk) + tuple(sedes_cdt))
            for r_cod, r_dep, r_qty in res_bulk:
                if r_cod not in stock_cdt: stock_cdt[r_cod] = []
                stock_cdt[r_cod].append((r_dep, float(r_qty)))
        return stock_cdt

    def _cargar_ventas_bulk(self, codigos, almacenes, dias_base):
        """
        Carga ventas en bloques (chunks) para múltiples códigos y almacenes en 3 ventanas de tiempo.
        Ventanas: [base, base*2, base*3]
        Retorna: {codigo: {promedio: X, total: Y}}
        """
        if not codigos or not almacenes: return {}
        
        p1, p2, p3 = int(dias_base), int(dias_base * 2), int(dias_base * 3)
        res_final = {}
        
        chunk_size = 500
        for i in range(0, len(codigos), chunk_size):
            chunk = codigos[i:i+chunk_size]
            placeholders_cods = ",".join(["?"] * len(chunk))
            placeholders_deps = ",".join(["?"] * len(almacenes))
            
            sql = f"""
                SELECT c_Codarticulo,
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p1}, GETDATE()) AND c_Concepto = 'VEN' THEN n_cantidad ELSE 0 END) - 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p1}, GETDATE()) AND c_Concepto = 'DEV' THEN n_cantidad ELSE 0 END) as neto_p1,
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p2}, GETDATE()) AND c_Concepto = 'VEN' THEN n_cantidad ELSE 0 END) - 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p2}, GETDATE()) AND c_Concepto = 'DEV' THEN n_cantidad ELSE 0 END) as neto_p2,
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p3}, GETDATE()) AND c_Concepto = 'VEN' THEN n_cantidad ELSE 0 END) - 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p3}, GETDATE()) AND c_Concepto = 'DEV' THEN n_cantidad ELSE 0 END) as neto_p3
                FROM TR_INVENTARIO WITH (NOLOCK)
                WHERE f_fecha >= DATEADD(day, -{p3}, GETDATE())
                AND c_Codarticulo IN ({placeholders_cods})
                AND c_Deposito IN ({placeholders_deps})
                AND c_Concepto IN ('VEN', 'DEV')
                GROUP BY c_Codarticulo
            """
            rows = self.db_manager.fetch_data(sql, tuple(chunk) + tuple(almacenes))
            
            for r_cod, n1, n2, n3 in rows:
                promedio = 0
                if n1 and n1 > 0: promedio = float(n1) / p1
                elif n2 and n2 > 0: promedio = float(n2) / p2
                elif n3 and n3 > 0: promedio = float(n3) / p3
                
                res_final[r_cod] = {"promedio": promedio, "total": float(n1 or 0)}

        return res_final

    def calcular_sugerencias(self, sede_destino, dept_cod=None, group_cod=None, sub_cod=None):
        """
        Calcula sugerencias de transferencia para una sede destino, usando la lógica unificada.
        """
        try:
            from pal.core.config_manager import ConfigManager
            config_mgr = ConfigManager(self.db_manager)
            sedes_config = config_mgr.get_sedes_config()

            if sede_destino not in sedes_config:
                logger.error(f"Sede {sede_destino} no configurada.")
                return []
                
            almacenes_destino = sedes_config[sede_destino].get("almacenes_tratables", [])
            if not almacenes_destino:
                logger.warning(f"Sede {sede_destino} no tiene almacenes tratables configurados.")
                return []

            # Lógica de Parámetros por Categoría y Global
            params_db = self.obtener_parametros()
            config_params = {p[0]: p[1:] for p in params_db}
            
            # 1. Cargar stock y categorías de la sede
            all_cdts = [almacen for cfg in sedes_config.values() for almacen in cfg.get("almacenes_cdt", [])]
            almacenes_stock_sede = [a for a in almacenes_destino if a not in all_cdts]
            if not almacenes_stock_sede: almacenes_stock_sede = almacenes_destino
            
            sql_stock, stock_params = self._build_stock_query(almacenes_stock_sede, dept_cod, group_cod, sub_cod)
            logger.info(f"Ejecutando consulta de stock para {sede_destino}...")
            stock_sede = self.db_manager.fetch_data(sql_stock, stock_params)
            logger.info(f"Se analizarán {len(stock_sede)} productos con presencia en la sede.")

            if not stock_sede: return []

            # 2. Cargar datos auxiliares (Bulk)
            codigos_analizar = [item[0] for item in stock_sede]
            productos_rojos = self._cargar_lista_roja(sede_destino)
            odc_dict = self._cargar_odc_activas()
            # Obtener código de localidad ODC para la sede destino
            sede_cfg = sedes_config.get(sede_destino, {})
            cod_localidad_destino = sede_cfg.get("codigo_localidad", "")
            dict_compromisos_full = self.get_compromisos_activos(sede_destino)
            # Adaptamos al formato esperado por el resto de la función (plano por código)
            dict_compromisos = {k: v.get(sede_destino.strip().upper(), 0) for k, v in dict_compromisos_full.items()}
            dict_stock_cdt = self._cargar_stock_cdt(codigos_analizar, all_cdts)
            
            # Cargar ventas en bulk usando el análisis por defecto o el global
            default_analisis = config_params.get(None, (25, 15, 0, 90))[3]
            dict_ventas = self._cargar_ventas_bulk(codigos_analizar, almacenes_destino, default_analisis)
            
            # 3. Bucle de cálculo
            sugerencias = []
            for codigo, stock_actual, cat_id, desc_corta, desc_larga in stock_sede:
                cod_norm = str(codigo).strip().lstrip('0') or "0"
                es_rojo = cod_norm in productos_rojos
                qty_compromiso = dict_compromisos.get(cod_norm, 0)
                
                # Obtener parámetros: (dias_stock, umbral_quiebre, umbral_auto, dias_analisis)
                p_dias, p_quiebre, p_auto, p_analisis = config_params.get(cat_id, config_params.get(None, (25, 15, 0, 90)))

                # Obtener promedio pre-calculado
                v_data = dict_ventas.get(codigo, {"promedio": 0, "total": 0})
                promedio_diario = v_data["promedio"]
                
                if promedio_diario <= 0:
                    if es_rojo and stock_actual <= 0:
                        promedio_diario = 0.05 # Resurrección mínima para rojos
                    else:
                        continue

                if qty_compromiso > 0:
                    stock_ideal_dbg = (promedio_diario * p_dias * 1.25 * 1.15)
                    logger.info(f"[COMPROMISO INDIVIDUAL] Prod {cod_norm} -> {sede_destino}: compromiso={qty_compromiso}, stock_actual={stock_actual}, ideal={int(stock_ideal_dbg)}, necesidad_resultante={max(0, stock_ideal_dbg - stock_actual - qty_compromiso)}")

                # A. GATILLO (Trigger)
                cobertura_actual = stock_actual / promedio_diario if promedio_diario > 0 else 999
                if cobertura_actual >= p_quiebre and not (es_rojo and stock_actual <= 0):
                    continue
                    
                # B. META (Target)
                stock_ideal = (promedio_diario * p_dias * 1.25 * 1.15)
                necesidad = stock_ideal - (stock_actual + qty_compromiso)

                if necesidad > 0:
                    necesidad_final = int(round(necesidad))
                    if necesidad_final <= 0: continue
                    
                    disponibles = dict_stock_cdt.get(codigo, [])
                    origen, cant_origen, cant_mover = ("SIN STOCK CDT", 0, necesidad_final)
                    
                    if disponibles:
                        origen, cant_origen = disponibles[0]
                        cant_mover = min(necesidad_final, int(cant_origen))

                    if cant_mover > 0:
                        # Verificar si existe ODC activa para este producto en la localidad destino
                        tiene_odc, info_odc = self._verificar_odc_producto(odc_dict, codigo, cod_localidad_destino)

                        sugerencias.append({
                            "producto_codigo": codigo, 
                            "producto_descripcion": desc_corta or desc_larga or "SIN DESCRIPCIÓN",
                            "sucursal_destino": sede_destino, 
                            "sucursal_origen_sugerida": origen,
                            "cantidad_sugerida": cant_mover, 
                            "stock_actual": stock_actual,
                            "stock_origen": cant_origen, 
                            "requiere_autorizacion": 1 if es_rojo or tiene_odc or (p_auto > 0 and cant_mover > p_auto) else 0,
                            "es_rojo": es_rojo,
                            "tiene_odc_activa": tiene_odc,
                            "odc_info": info_odc,
                            "dias_stock_objetivo": p_dias,
                            "promedio_diario": round(promedio_diario, 4)
                        })
            return sugerencias
        except Exception as e:
            logger.error(f"Error en `calcular_sugerencias`: {e}") # exc_info=True eliminado
            import traceback
            traceback.print_exc()
            return []

    def calcular_abastecimiento_global(self, dept_cod=None, group_cod=None, sub_cod=None):
        """
        Calcula abastecimiento para TODAS las sedes simultáneamente,
        distribuyendo el stock de los CDTs de forma proporcional si es insuficiente.
        """
        try:
            logger.info("Iniciando cálculo de abastecimiento GLOBAL")
            
            # 1. Obtener configuración de sedes
            from pal.core.config_manager import ConfigManager
            config_mgr = ConfigManager(self.db_manager)
            sedes_config = config_mgr.get_sedes_config()
            
            # Identificar CDTs y Sedes Destino
            cdts_almacenes = []
            sedes_destino = {} # {nombre_sede: [almacenes_tratables]}
            
            for s_name, s_cfg in sedes_config.items():
                if s_cfg.get("almacenes_cdt"):
                    cdts_almacenes.extend(s_cfg["almacenes_cdt"])
                
                tratables = s_cfg.get("almacenes_tratables", [])
                if tratables:
                    # Excluir CDTs de los tratables para el cálculo de necesidad de la sede
                    almacenes_puros = [a for a in tratables if a not in cdts_almacenes]
                    if almacenes_puros:
                        sedes_destino[s_name] = almacenes_puros
                    else:
                        sedes_destino[s_name] = tratables

            if not cdts_almacenes:
                logger.error("No hay CDTs configurados para el cálculo global.")
                return []

            # 2. Parámetros Globales (el cálculo global no soporta params por categoría)
            params_db = self.obtener_parametros()
            config_params = {p[0]: (p[1], p[2], p[3], p[4]) for p in params_db}
            
            default_dias, default_quiebre, default_umbral, default_analisis = config_params.get(None, (25, 15, 0, 90))
            
            dias_obj = float(default_dias if default_dias else 25)
            umb_quiebre = float(default_quiebre if default_quiebre is not None else 15)
            umbral_auto = float(default_umbral if default_umbral is not None else 0)
            dias_analisis_base = int(default_analisis if default_analisis else 90)
            
            logger.info(f"Parámetros GLOBAL (Meta: {dias_obj}d, Gatillo: <{umb_quiebre}d, Análisis: Cascada {dias_analisis_base}d, {dias_analisis_base*2}d, {dias_analisis_base*3}d)")
            
            # 2a. Cargar Lista Roja para validación global
            sql_rojos = "SELECT producto_codigo, sede_destino FROM pal_productos_no_trasladables WHERE activo = 1"
            res_rojos = self.db_manager.fetch_data(sql_rojos)
            dict_rojos = {}
            for pr_cod, sd_dest in res_rojos:
                # Normalización: quitar ceros y espacios
                cod_norm = str(pr_cod).strip().lstrip('0')
                if not cod_norm: cod_norm = "0"
                
                if cod_norm not in dict_rojos: dict_rojos[cod_norm] = set()
                dict_rojos[cod_norm].add(sd_dest)

            # 2a2. Cargar ODC activas para validación global
            odc_dict = self._cargar_odc_activas()

            # 2b. Cargar compromisos actuales desde la nueva tabla centralizada
            dict_compromisos = self.get_compromisos_activos()
            
            total_compromisos = sum(qty for sedes in dict_compromisos.values() for qty in sedes.values())
            logger.info(f"Compromisos activos cargados: {len(dict_compromisos)} productos, {total_compromisos} unidades totales")
            if dict_compromisos:
                for cp, cs in list(dict_compromisos.items())[:5]:
                    logger.info(f"  Compromiso: {cp} -> {cs}")
            
            periodos_cascada = [int(dias_analisis_base), int(dias_analisis_base * 2), int(dias_analisis_base * 3)]

            # 3. Obtener Stock en CDTs (de todos los productos que podrían necesitarse)
            # Para optimizar, primero buscamos qué productos tienen stock en CDT
            sql_stock_cdt = f"""
                SELECT c_codarticulo, SUM(n_cantidad) as stock_total, MAX(c_coddeposito) as cdt_dep
                FROM MA_DEPOPROD WITH (NOLOCK)
                WHERE c_coddeposito IN ({','.join(['?']*len(cdts_almacenes))})
                AND n_cantidad > 0
                GROUP BY c_codarticulo
                HAVING SUM(n_cantidad) > 0
            """
            res_cdt = self.db_manager.fetch_data(sql_stock_cdt, tuple(cdts_almacenes))
            
            stock_cdt_global = {}
            for r in res_cdt:
                c_norm = str(r[0]).strip().lstrip('0') or "0"
                if c_norm not in stock_cdt_global:
                    stock_cdt_global[c_norm] = {"total": 0.0, "deposito": r[2]}
                stock_cdt_global[c_norm]["total"] += float(r[1])
                
            codigos_con_stock_cdt = list(stock_cdt_global.keys())

            if not codigos_con_stock_cdt:
                logger.info("No hay stock disponible en ningún CDT.")
                return []

            # 4. Obtener Stock en Sedes Destino para estos productos
            # (Filtramos por jerarquía si se especifica)
            where_filtros = ""
            filtros_params = []
            if dept_cod or group_cod or sub_cod:
                conds = []
                if dept_cod: conds.append("p.c_departamento = ?"); filtros_params.append(dept_cod)
                if group_cod: conds.append("p.c_grupo = ?"); filtros_params.append(group_cod)
                if sub_cod: conds.append("p.c_subgrupo = ?"); filtros_params.append(sub_cod)
                where_filtros = " AND " + " AND ".join(conds)

            # Para no saturar, procesamos por lotes de sedes o una query masiva
            # Vamos a consolidar todos los almacenes tratables de todas las sedes
            todos_almacenes_destino = []
            almacen_a_sede = {} # Mapping para saber a qué sede pertenece cada almacén
            for s_name, almacenes in sedes_destino.items():
                todos_almacenes_destino.extend(almacenes)
                for a in almacenes: almacen_a_sede[a] = s_name

            # Mejor opción: Query de stock para TODOS los productos en esas sedes que tengan los filtros
            sql_stock_sedes_opt = f"""
                SELECT d.c_codarticulo, d.c_coddeposito, SUM(d.n_cantidad), 
                       MAX(p.cu_descripcion_corta), MAX(p.C_DESCRI)
                FROM MA_DEPOPROD d WITH (NOLOCK)
                JOIN MA_PRODUCTOS p WITH (NOLOCK) ON d.c_codarticulo = p.c_codigo
                WHERE d.c_coddeposito IN ({','.join(['?']*len(todos_almacenes_destino))})
                {where_filtros}
                GROUP BY d.c_codarticulo, d.c_coddeposito
            """
            logger.info("Consultando stock en todas las sedes...")
            res_stock_sedes = self.db_manager.fetch_data(sql_stock_sedes_opt, tuple(todos_almacenes_destino) + tuple(filtros_params))
            
            # Organizar stock: {codigo: {sede: stock}}
            stock_por_sede = {}
            descripciones = {} # {codigo: {corta: 'desc', larga: 'desc'}}
            for r_cod, r_dep, r_qty, r_desc_corta, r_desc_larga in res_stock_sedes:
                s_name = almacen_a_sede.get(r_dep)
                if not s_name: continue
                if r_cod not in stock_por_sede: stock_por_sede[r_cod] = {}
                stock_por_sede[r_cod][s_name] = stock_por_sede[r_cod].get(s_name, 0) + float(r_qty)
                descripciones[r_cod] = {
                    "corta": str(r_desc_corta or r_desc_larga or "SIN DESCRIPCIÓN"),
                    "larga": str(r_desc_larga or "SIN DESCRIPCIÓN")
                }

            # 5. Obtener Ventas en Cascada para todos los códigos relevantes en todas las sedes
            codigos_a_analizar = list(stock_por_sede.keys())
            logger.info(f"Obteniendo ventas para {len(codigos_a_analizar)} productos en todas las sedes...")
            
            # Para el cálculo global, necesitamos ventas por sede. 
            # La función obtener_fechas_liquidacion_y_ventas actual no separa por depósito en el retorno.
            # Necesitamos una versión o llamar sede por sede (lento) o una nueva query.
            # Vamos a llamar a la query masiva pero agrupada por sede.
            
            datos_ventas_global = self._obtener_ventas_globales_por_sede(codigos_a_analizar, todos_almacenes_destino, periodos_cascada)
            
            # 6. Calcular Necesidades y Distribuir
            sugerencias_finales = []
            
            for codigo in codigos_a_analizar:
                # Normalización de código para búsqueda en diccionarios
                cod_norm = str(codigo).strip().lstrip('0') or "0"
                
                if cod_norm not in stock_cdt_global: continue
                
                stock_cdt_disp = stock_cdt_global[cod_norm]["total"]
                depo_cdt = stock_cdt_global[cod_norm]["deposito"]
                
                demandas = [] # [(sede, deficit, promedio_diario)]
                total_deficit = 0
                
                for s_name in sedes_destino.keys():
                    v_data = datos_ventas_global.get(codigo, {}).get(s_name)
                    if not v_data: continue
                    
                    promedio = v_data['promedio']
                    stock_actual = stock_por_sede.get(codigo, {}).get(s_name, 0)
                    qty_compromiso = dict_compromisos.get(cod_norm, {}).get(s_name.strip().upper(), 0)
                    
                    if qty_compromiso > 0:
                        stock_ideal_dbg = int(round(promedio * dias_obj * 1.25 * 1.15))
                        logger.info(f"[COMPROMISO GLOBAL] Prod {cod_norm} -> {s_name}: compromiso={qty_compromiso}, stock_actual={stock_actual}, ideal={stock_ideal_dbg}, deficit_sin_compromiso={max(0, stock_ideal_dbg - stock_actual)}")
                    
                    rojos_prod = dict_rojos.get(cod_norm, set())
                    es_rojo = (s_name in rojos_prod) or (None in rojos_prod)
                    
                    # FILTRO: "Gatillo de Resurtido" (Solo si cobertura < umbral_quiebre)
                    dias_para_quiebre = stock_actual / promedio if promedio > 0 else (0 if stock_actual <= 0 else 999)
                    # Usamos el global para el ICH por ahora
                    global_quiebre = float(config_params.get(None, (25, 25, 0, 365))[1])
                    if dias_para_quiebre >= global_quiebre and not es_rojo:
                        continue
                    
                    # Stock Ideal (misma lógica que individual)
                    stock_ideal = int(round(promedio * dias_obj * 1.25 * 1.15))
                    # NO restar compromiso aquí: se resta de la cantidad_sugerida FINAL después de distribución
                    deficit = max(0, int(stock_ideal - stock_actual))
                    
                    if deficit > 0:
                        demandas.append({
                            "sede": s_name,
                            "deficit": deficit,
                            "promedio": promedio,
                            "stock_actual": stock_actual,
                            "qty_compromiso": qty_compromiso
                        })
                        total_deficit += deficit
                
                if not demandas: continue
                
                # REGLA DE ORO: Si excede stock CDT -> Repartición por Peso de Ventas
                if total_deficit > stock_cdt_disp:
                    total_ventas_prod = sum(v_data.get('total', 0) for v_data in datos_ventas_global.get(codigo, {}).values())
                    if total_ventas_prod > 0:
                        for dem in demandas:
                            v_data = datos_ventas_global.get(codigo, {}).get(dem['sede'], {})
                            venta_sede = v_data.get('total', 0)
                            ratio = venta_sede / total_ventas_prod
                            dem['cantidad_sugerida'] = min(dem['deficit'], int(round(ratio * stock_cdt_disp)))
                    else:
                        # Fallback a proporcional por déficit si no hay ventas registradas
                        factor_ajuste = stock_cdt_disp / total_deficit
                        for dem in demandas:
                            dem['cantidad_sugerida'] = int(dem['deficit'] * factor_ajuste)
                else:
                    for dem in demandas:
                        dem['cantidad_sugerida'] = dem['deficit']

                for dem in demandas:
                    compromiso_dem = int(dem.get("qty_compromiso", 0))
                    cantidad_sugerida = max(0, dem["cantidad_sugerida"] - compromiso_dem)
                    if compromiso_dem > 0:
                        logger.info(f"[COMPROMISO AJUSTE] Prod {cod_norm} -> {dem['sede']}: distribuido={dem['cantidad_sugerida']}, compromiso={compromiso_dem}, final={cantidad_sugerida}")
                    if cantidad_sugerida <= 0: continue
                    
                    # Validar si es ROJO para esta sede
                    cod_norm = str(codigo).strip().lstrip('0') or "0"
                    rojos_prod = dict_rojos.get(cod_norm, set())
                    es_rojo = (dem["sede"] in rojos_prod) or (None in rojos_prod)

                    # Verificar si existe ODC activa para este producto en la localidad destino
                    sede_cfg = sedes_config.get(dem["sede"], {})
                    cod_localidad = sede_cfg.get("codigo_localidad", "")
                    tiene_odc, info_odc = self._verificar_odc_producto(odc_dict, codigo, cod_localidad)

                    sugerencias_finales.append({
                        "producto_codigo": codigo,
                        "producto_descripcion": descripciones.get(codigo, {}).get("corta", "SIN DESCRIPCIÓN"),
                        "producto_descripcion_larga": descripciones.get(codigo, {}).get("larga", "SIN DESCRIPCIÓN"),
                        "sucursal_destino": dem["sede"],
                        "sucursal_origen_sugerida": depo_cdt,
                        "cantidad_sugerida": cantidad_sugerida,
                        "stock_actual": dem["stock_actual"],
                        "stock_origen": stock_cdt_disp,
                        "requiere_autorizacion": 1 if es_rojo or tiene_odc or (umbral_auto > 0 and cantidad_sugerida > umbral_auto) else 0,
                        "es_rojo": es_rojo,
                        "tiene_odc_activa": tiene_odc,
                        "odc_info": info_odc,
                        "dias_stock_objetivo": dias_obj,
                        "promedio_diario": round(dem["promedio"], 4),
                        "ajustado": total_deficit > stock_cdt_disp
                    })
            
            logger.info(f"Cálculo global finalizado. Sugerencias generadas: {len(sugerencias_finales)}")
            return sugerencias_finales

        except Exception as e:
            logger.error(f"Error en cálculo global: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _obtener_ventas_globales_por_sede(self, codigos, depositos, periodos_cascada):
        """Helper para obtener ventas agrupadas por sede con búsqueda en cascada para el cálculo global."""
        if not codigos or not depositos or not periodos_cascada: return {}
        
        res_final = {} # {codigo: {sede: {promedio: X}}}
        
        from pal.core.config_manager import ConfigManager
        config_mgr = ConfigManager(self.db_manager)
        sedes_config = config_mgr.get_sedes_config()
        dep_to_sede = {}
        for s_name, s_cfg in sedes_config.items():
            for d in s_cfg.get("almacenes_tratables", []):
                dep_to_sede[d] = s_name

        max_dias = max(periodos_cascada)
        p1 = periodos_cascada[0]
        p2 = periodos_cascada[1] if len(periodos_cascada) > 1 else p1
        p3 = periodos_cascada[2] if len(periodos_cascada) > 2 else p2

        chunk_size = 500
        log_count = 0 # Counter for debug logs
        for i in range(0, len(codigos), chunk_size):
            chunk = codigos[i:i + chunk_size]
            placeholders_cods = ",".join(["?"] * len(chunk))
            placeholders_deps = ",".join(["?"] * len(depositos))
            
            sql = f"""
                SELECT c_Codarticulo, c_Deposito, 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p1}, GETDATE()) AND c_Concepto = 'VEN' THEN n_cantidad ELSE 0 END) - 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p1}, GETDATE()) AND c_Concepto = 'DEV' THEN n_cantidad ELSE 0 END) as neto_p1,
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p2}, GETDATE()) AND c_Concepto = 'VEN' THEN n_cantidad ELSE 0 END) - 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p2}, GETDATE()) AND c_Concepto = 'DEV' THEN n_cantidad ELSE 0 END) as neto_p2,
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p3}, GETDATE()) AND c_Concepto = 'VEN' THEN n_cantidad ELSE 0 END) - 
                       SUM(CASE WHEN f_fecha >= DATEADD(day, -{p3}, GETDATE()) AND c_Concepto = 'DEV' THEN n_cantidad ELSE 0 END) as neto_p3,
                       MAX(CASE WHEN c_Concepto = 'VEN' THEN f_fecha ELSE NULL END) as ultima_venta
                FROM TR_INVENTARIO WITH (NOLOCK)
                WHERE f_fecha >= DATEADD(day, -{max_dias}, GETDATE())
                AND c_Codarticulo IN ({placeholders_cods})
                AND c_Deposito IN ({placeholders_deps})
                AND c_Concepto IN ('VEN', 'DEV')
                GROUP BY c_Codarticulo, c_Deposito
            """
            rows = self.db_manager.fetch_data(sql, tuple(chunk) + tuple(depositos))
            
            temp_agrup = {}
            for r_cod, r_dep, net_p1, net_p2, net_p3, last_ven in rows:
                s_name = dep_to_sede.get(r_dep)
                if not s_name: continue
                if r_cod not in temp_agrup: temp_agrup[r_cod] = {}
                if s_name not in temp_agrup[r_cod]: 
                    temp_agrup[r_cod][s_name] = {'p1':0, 'p2':0, 'p3':0, 'last_ven': None}
                
                t = temp_agrup[r_cod][s_name]
                t['p1'] += float(net_p1 or 0)
                t['p2'] += float(net_p2 or 0)
                t['p3'] += float(net_p3 or 0)
                if last_ven:
                    if not t['last_ven'] or last_ven > t['last_ven']:
                        t['last_ven'] = last_ven

            for r_cod, sedes_data in temp_agrup.items():
                if r_cod not in res_final: res_final[r_cod] = {}
                for s_name, data in sedes_data.items():
                    promedio = 0
                    total_usado = 0
                    debug_msg = None
                    
                    if data['p1'] > 0:
                        promedio = data['p1'] / p1
                        total_usado = data['p1']
                        if log_count < 5: debug_msg = f"[{r_cod}] Global Cascada ({s_name}): Usando {p1}d -> Promedio: {promedio:.2f}/día"
                    elif data['p2'] > 0:
                        promedio = data['p2'] / p2
                        total_usado = data['p2']
                        if log_count < 5: debug_msg = f"[{r_cod}] Global Cascada ({s_name}): Sin ventas en {p1}d. Usando {p2}d -> Promedio: {promedio:.2f}/día"
                    elif data['p3'] > 0:
                        promedio = data['p3'] / p3
                        total_usado = data['p3']
                        if log_count < 5: debug_msg = f"[{r_cod}] Global Cascada ({s_name}): Sin ventas en {p2}d. Usando {p3}d -> Promedio: {promedio:.2f}/día"
                    
                    if debug_msg:
                        logger.debug(debug_msg)
                        log_count += 1
                    
                    res_final[r_cod][s_name] = {
                        "total": total_usado,
                        "promedio": promedio,
                        "ultima_venta": data['last_ven']
                    }

        return res_final
            
    def obtener_parametros(self):
        """Obtiene los parámetros configurados: categoria_id, dias_stock, umbral_quiebre, umbral_autorizacion, dias_analisis_ventas."""
        try:
            sql = "SELECT categoria_id, dias_stock, umbral_quiebre, umbral_autorizacion, dias_analisis_ventas FROM pal_parametros_abastecimiento"
            return self.db_manager.fetch_data(sql)
        except Exception as e:
            logger.error(f"Error obteniendo parámetros: {e}")
            return []

    def save_parametro(self, categoria_id, dias_stock, umbral_quiebre, umbral_auto, dias_analisis=365):
        """Guarda o actualiza un parámetro de abastecimiento."""
        try:
            # Check if exists
            check_sql = "SELECT id FROM pal_parametros_abastecimiento WHERE "
            params = []
            if categoria_id is None:
                check_sql += "categoria_id IS NULL"
            else:
                check_sql += "categoria_id = ?"
                params.append(categoria_id)
            
            exists = self.db_manager.fetch_data(check_sql, tuple(params))
            
            if exists:
                update_sql = """UPDATE pal_parametros_abastecimiento 
                               SET dias_stock = ?, umbral_quiebre = ?, umbral_autorizacion = ?, 
                                   dias_analisis_ventas = ?, fecha_actualizacion = GETDATE() 
                               WHERE """
                if categoria_id is None:
                    update_sql += "categoria_id IS NULL"
                    update_params = (dias_stock, umbral_quiebre, umbral_auto, dias_analisis)
                else:
                    update_sql += "categoria_id = ?"
                    update_params = (dias_stock, umbral_quiebre, umbral_auto, dias_analisis, categoria_id)
                self.db_manager.execute_query(update_sql, update_params)
            else:
                insert_sql = """INSERT INTO pal_parametros_abastecimiento 
                                (categoria_id, dias_stock, umbral_quiebre, umbral_autorizacion, dias_analisis_ventas) 
                                VALUES (?, ?, ?, ?, ?)"""
                self.db_manager.execute_query(insert_sql, (categoria_id, dias_stock, umbral_quiebre, umbral_auto, dias_analisis))
            return True
        except Exception as e:
            logger.error(f"Error guardando parámetro: {e}")
            return False
        
    def registrar_autorizacion(self, sugerencia_id, usuario_id, cantidad_autorizada, motivo):
        """Registra la autorización de una sugerencia en la tabla pal_sugerencias_transferencia."""
        try:
            # 1. Obtener datos de la sugerencia original (incluyendo maestro_id)
            sql_orig = "SELECT producto_codigo, sucursal_origen_sugerida, sucursal_destino, cantidad_sugerida, maestro_id FROM pal_sugerencias_transferencia WHERE id = ?"
            orig = self.db_manager.fetch_data(sql_orig, (sugerencia_id,))
            if not orig:
                return False
            
            prod, orig_sede, dest_sede, cant_orig, maestro_id = orig[0]

            # 2. Actualizar sugerencia
            sql_update = """
                UPDATE pal_sugerencias_transferencia 
                SET fue_autorizada = 1, 
                    usuario_autoriza = ?, 
                    fecha_autorizacion = GETDATE(), 
                    cantidad_sugerida = ?,
                    estado = 'aprobada'
                WHERE id = ?
            """
            self.db_manager.execute_query(sql_update, (usuario_id, cantidad_autorizada, sugerencia_id))
            
            # 3. Registrar en auditoría
            sql_aud = """
                INSERT INTO pal_auditoria_autorizaciones 
                (usuario_id, producto_codigo, sucursal_origen, sucursal_destino, cantidad_original, cantidad_autorizada, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_query(sql_aud, (usuario_id, prod, orig_sede, dest_sede, cant_orig, cantidad_autorizada, motivo))
            
            # 4. Registrar Compromiso en el Inventario Central (con referencia_maestro)
            sql_comp = """
                INSERT INTO pal_compromisos_inventario
                (producto_codigo, sucursal_origen, sucursal_destino, cantidad, estado, referencia_maestro, usuario_id)
                VALUES (?, ?, ?, ?, 'activo', ?, ?)
            """
            self.db_manager.execute_query(sql_comp, (prod, orig_sede, dest_sede, cantidad_autorizada, maestro_id, usuario_id))
            
            return True
        except Exception as e:
            logger.error(f"Error registrando autorización: {e}")
            return False

    def crear_solicitud_autorizacion_odc(self, producto_codigo, sucursal_destino, sucursal_origen,
                                          cantidad_sugerida, stock_actual, motivo, usuario_id=None):
        """
        Crea una solicitud de autorización para transferir un producto que tiene ODC activa.
        La solicitud queda en estado 'pendiente' esperando aprobación de un usuario con permiso.
        """
        try:
            # Verificar si ya existe una solicitud pendiente para este producto/destino
            sql_check = """
                SELECT id FROM pal_sugerencias_transferencia
                WHERE producto_codigo = ? AND sucursal_destino = ? 
                AND tipo_solicitud = 'odc' AND estado = 'pendiente'
            """
            existe = self.db_manager.fetch_data(sql_check, (producto_codigo, sucursal_destino))
            if existe:
                logger.warning(f"Ya existe solicitud ODC pendiente para {producto_codigo} -> {sucursal_destino}")
                return {"success": False, "error": "Ya existe una solicitud pendiente para este producto."}

            sql_insert = """
                INSERT INTO pal_sugerencias_transferencia
                (producto_codigo, sucursal_destino, sucursal_origen_sugerida, cantidad_sugerida,
                 cantidad_disponible, stock_actual, tiene_odc_activa, es_producto_rojo,
                 tipo_solicitud, requiere_autorizacion, fue_autorizada, estado)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0, 'odc', 1, 0, 'pendiente')
            """
            self.db_manager.execute_query(sql_insert, (
                producto_codigo, sucursal_destino, sucursal_origen,
                cantidad_sugerida, cantidad_sugerida, stock_actual
            ))

            # Registrar en auditoría el motivo de la solicitud
            sql_aud = """
                INSERT INTO pal_auditoria_autorizaciones
                (usuario_id, producto_codigo, sucursal_origen, sucursal_destino, cantidad_original, cantidad_autorizada, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_query(sql_aud, (
                usuario_id, producto_codigo, sucursal_origen, sucursal_destino,
                cantidad_sugerida, cantidad_sugerida, f"SOLICITUD ODC: {motivo}"
            ))

            logger.info(f"Solicitud ODC creada: {producto_codigo} -> {sucursal_destino}, cant={cantidad_sugerida}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error creando solicitud ODC: {e}")
            return {"success": False, "error": str(e)}

    def save_sugerencias(self, sugerencias, usuario_id=None):
        """
        Guarda las sugerencias generadas agrupándolas en órdenes de transferencia (Maestros).
        """
        try:
            from datetime import datetime
            
            # 1. Agrupar sugerencias por sede destino
            agrupadas = {}
            for s in sugerencias:
                destino = s["sucursal_destino"]
                if destino not in agrupadas:
                    agrupadas[destino] = []
                agrupadas[destino].append(s)
            
            # Verificar permisos para "auto-autorización"
            from pal.core.permissions import PermissionsManager
            perms_mgr = PermissionsManager(self.db_manager)
            puede_autorizar = perms_mgr.tiene_permiso(usuario_id, "LOGISTICA", "autorizar") if usuario_id else False

            for sede, items in agrupadas.items():
                # 2. Generar número de transferencia único para esta sede
                numero_transf = self.generar_numero_transferencia()
                
                # 3. Crear el Maestro
                sql_maestro = """
                    INSERT INTO pal_transferencias_maestro 
                    (numero_transf, sucursal_destino, usuario_crea, estado, fecha_creacion)
                    VALUES (?, ?, ?, 'en_transito', GETDATE())
                """
                self.db_manager.execute_query(sql_maestro, (numero_transf, sede, usuario_id))
                
                # Obtener el ID del maestro recién creado
                res_id = self.db_manager.fetch_data("SELECT IDENT_CURRENT('pal_transferencias_maestro')")
                maestro_id = int(res_id[0][0]) if res_id else None
                
                # 4. Insertar ítems vinculados al maestro
                sql_item = """
                    INSERT INTO pal_sugerencias_transferencia 
                    (producto_codigo, sucursal_destino, sucursal_origen_sugerida, cantidad_sugerida, 
                     cantidad_disponible, stock_actual, requiere_autorizacion, estado, fue_autorizada, 
                     fecha_autorizacion, usuario_autoriza, cantidad_pre_ajuste, es_producto_rojo, 
                     tipo_solicitud, maestro_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                for s in items:
                    requiere_aut = s.get("requiere_autorizacion", 1)
                    # Si el usuario tiene permiso, se autoriza automáticamente
                    es_auto = (requiere_aut == 0) or puede_autorizar
                    
                    estado_final = 'en_transito' if es_auto else 'pendiente'
                    fue_aut = 1 if es_auto else 0
                    fecha_aut = datetime.now() if es_auto else None
                    u_aut = usuario_id if es_auto else None
                    cant_sug = s["cantidad_sugerida"]
                    cant_orig = s.get("_cantidad_original", cant_sug)
                    
                    es_rojo = 1 if s.get("es_rojo", False) else 0
                    tiene_odc = 1 if s.get("tiene_odc_activa", False) else 0
                    if es_rojo:
                        tipo_sol = 'producto_rojo'
                    elif tiene_odc:
                        tipo_sol = 'odc'
                    else:
                        tipo_sol = 'normal'
                    
                    params = (
                        s["producto_codigo"],
                        s["sucursal_destino"],
                        s["sucursal_origen_sugerida"],
                        cant_sug,
                        s["stock_origen"],
                        s["stock_actual"],
                        requiere_aut,
                        estado_final,
                        fue_aut,
                        fecha_aut,
                        u_aut,
                        cant_orig,
                        es_rojo,
                        tipo_sol,
                        maestro_id
                    )
                    self.db_manager.execute_query(sql_item, params)
                    
                    # SI fue auto-autorizada y requería permiso, registrar en auditoría
                    if es_auto and requiere_aut == 1:
                        sql_aud = """
                            INSERT INTO pal_auditoria_autorizaciones 
                            (usuario_id, producto_codigo, sucursal_origen, sucursal_destino, cantidad_original, cantidad_autorizada, motivo)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        self.db_manager.execute_query(sql_aud, (
                            usuario_id, s["producto_codigo"], s["sucursal_origen_sugerida"], 
                            s["sucursal_destino"], cant_orig, cant_sug, 
                            "Auto-autorización por permisos de usuario"
                        ))
                    
                    # SI fue auto-autorizada (con o sin permiso explícito previo), generar compromiso en Inventario Central
                    if es_auto:
                        sql_comp = """
                            INSERT INTO pal_compromisos_inventario
                            (producto_codigo, sucursal_origen, sucursal_destino, cantidad, estado, referencia_maestro, usuario_id)
                            VALUES (?, ?, ?, ?, 'activo', ?, ?)
                        """
                        self.db_manager.execute_query(sql_comp, (
                            s["producto_codigo"], s["sucursal_origen_sugerida"], s["sucursal_destino"], 
                            cant_sug, maestro_id, usuario_id
                        ))
                    
            return True
        except Exception as e:
            logger.error(f"Error guardando sugerencias agrupadas: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generar_numero_transferencia(self):
        """Genera el siguiente número correlativo de transferencia (TRS-000001)."""
        try:
            sql = "SELECT MAX(id) FROM pal_transferencias_maestro"
            res = self.db_manager.fetch_data(sql)
            next_id = 1
            if res and res[0][0]:
                next_id = int(res[0][0]) + 1
            
            return f"TRS-{str(next_id).zfill(6)}"
        except Exception as e:
            logger.error(f"Error generando número de transferencia: {e}")
            return f"TRS-{datetime.now().strftime('%H%M%S')}"

    def get_ordenes_activas(self):
        """Obtiene las órdenes de transferencia que están en tránsito o recibidas parcialmente."""
        try:
            sql = """
                SELECT m.id, m.numero_transf, m.sucursal_destino, m.fecha_creacion, m.estado,
                       (SELECT COUNT(*) FROM pal_sugerencias_transferencia WHERE maestro_id = m.id) as total_items,
                       u.nombre_completo as usuario_nombre,
                       (SELECT COUNT(*) FROM pal_sugerencias_transferencia WHERE maestro_id = m.id AND estado_recepcion = 'completada') as items_completados
                FROM pal_transferencias_maestro m
                LEFT JOIN pal_usuarios u ON m.usuario_crea = u.id
                WHERE m.estado IN ('en_transito', 'recibida_parcial')
                ORDER BY m.fecha_creacion DESC
            """
            return self.db_manager.fetch_data(sql) or []
        except Exception as e:
            logger.error(f"Error obteniendo órdenes activas: {e}")
            return []

    def get_detalle_orden(self, maestro_id):
        """Obtiene los productos individuales de una orden de transferencia."""
        try:
            sql = """
                SELECT t.id, t.producto_codigo, COALESCE(p.cu_descripcion_corta, p.C_DESCRI, 'SIN DESCRIPCIÓN') as descripcion,
                       t.cantidad_sugerida, t.sucursal_origen_sugerida, t.es_producto_rojo,
                       ISNULL(t.cantidad_recibida_total, 0) as cantidad_recibida,
                       ISNULL(t.estado_recepcion, 'pendiente') as estado_recepcion
                FROM pal_sugerencias_transferencia t
                LEFT JOIN MA_PRODUCTOS p ON t.producto_codigo = p.C_CODIGO COLLATE DATABASE_DEFAULT
                WHERE t.maestro_id = ?
            """
            return self.db_manager.fetch_data(sql, (maestro_id,)) or []
        except Exception as e:
            logger.error(f"Error obteniendo detalle de orden {maestro_id}: {e}")
            return []

    def cerrar_transferencia(self, maestro_id, usuario_id):
        """Cierra una orden de transferencia, marcándola como recibida."""
        try:
            # 1. Actualizar maestro
            sql_m = "UPDATE pal_transferencias_maestro SET estado = 'recibida' WHERE id = ?"
            self.db_manager.execute_query(sql_m, (maestro_id,))
            
            # 2. Actualizar ítems
            sql_i = "UPDATE pal_sugerencias_transferencia SET estado = 'completada' WHERE maestro_id = ?"
            self.db_manager.execute_query(sql_i, (maestro_id,))
            
            # 3. Cerrar compromisos activos vinculados a este maestro (por referencia_maestro)
            sql_comp_directo = "UPDATE pal_compromisos_inventario SET estado = 'completado', fecha_actualizacion = GETDATE() WHERE referencia_maestro = ? AND estado = 'activo'"
            self.db_manager.execute_query(sql_comp_directo, (maestro_id,))
            
            # 3b. Cerrar compromisos sin referencia_maestro (creados por registrar_autorizacion)
            #     Buscando por producto + sede de los ítems del maestro
            sql_items = "SELECT producto_codigo, sucursal_destino, sucursal_origen_sugerida FROM pal_sugerencias_transferencia WHERE maestro_id = ?"
            items = self.db_manager.fetch_data(sql_items, (maestro_id,))
            if items:
                for prod, dest_sede, orig_sede in items:
                    sql_comp_ind = """UPDATE pal_compromisos_inventario SET estado = 'completado', fecha_actualizacion = GETDATE() 
                        WHERE producto_codigo = ? AND sucursal_destino = ? AND sucursal_origen = ? 
                        AND estado = 'activo' AND referencia_maestro IS NULL"""
                    self.db_manager.execute_query(sql_comp_ind, (prod, dest_sede, orig_sede))
            
            logger.info(f"Orden de transferencia {maestro_id} cerrada por usuario {usuario_id}")
            return True
        except Exception as e:
            logger.error(f"Error cerrando transferencia {maestro_id}: {e}")
            return False

    def generar_numero_recepcion(self):
        """Genera el siguiente número correlativo de recepción (REC-000001)."""
        try:
            sql = "SELECT MAX(id) FROM pal_recepciones_maestro"
            res = self.db_manager.fetch_data(sql)
            next_id = 1
            if res and res[0][0]:
                next_id = int(res[0][0]) + 1
            return f"REC-{str(next_id).zfill(6)}"
        except Exception as e:
            logger.error(f"Error generando número de recepción: {e}")
            return f"REC-{datetime.now().strftime('%H%M%S')}"

    def generar_lote_interno(self, semilla):
        """
        Genera un código de lote interno único.
        Formato: L-{YYMMDD}-{HHMM}-{HASH_CORTO}
        """
        import hashlib
        now = datetime.now()
        base = f"{semilla}{now.timestamp()}"
        hash_corto = hashlib.md5(base.encode()).hexdigest()[:4].upper()
        return f"L-{now.strftime('%y%m%d')}-{now.strftime('%H%M')}-{hash_corto}"

    def registrar_recepcion(self, transferencia_id, items_recibidos, usuario_id, observaciones=None):
        """
        Registra una recepción (parcial o total) para una orden de transferencia.
        items_recibidos: lista de dicts [{'sugerencia_id': int, 'cantidad': float, 'lotes': [...]}]
        """
        try:
            # 1. Generar correlativo REC
            numero_recepcion = self.generar_numero_recepcion()
            
            # 2. Crear maestro de recepción
            sql_rec = """
                INSERT INTO pal_recepciones_maestro 
                (numero_recepcion, transferencia_id, usuario_recibe, observaciones, fecha_recepcion)
                VALUES (?, ?, ?, ?, GETDATE())
            """
            self.db_manager.execute_query(sql_rec, (numero_recepcion, transferencia_id, usuario_id, observaciones))
            
            # Obtener ID de recepción
            res_id = self.db_manager.fetch_data("SELECT IDENT_CURRENT('pal_recepciones_maestro')")
            recepcion_id = int(res_id[0][0]) if res_id else None
            
            if not recepcion_id:
                raise Exception("No se pudo obtener el ID de la recepción creada")

            # 3. Procesar ítems
            for item in items_recibidos:
                sug_id = item['sugerencia_id']
                cant_rec = float(item['cantidad'])
                lotes = item.get('lotes', [])
                
                # Insertar detalle recepción
                sql_det = """
                    INSERT INTO pal_recepciones_detalle (recepcion_id, sugerencia_id, cantidad_recibida)
                    VALUES (?, ?, ?)
                """
                self.db_manager.execute_query(sql_det, (recepcion_id, sug_id, cant_rec))
                
                # Obtener ID del detalle para vincular lotes
                res_det = self.db_manager.fetch_data("SELECT IDENT_CURRENT('pal_recepciones_detalle')")
                detalle_id = int(res_det[0][0]) if res_det else None
                
                # Insertar lotes si existen
                if detalle_id and lotes:
                    for lote in lotes:
                        lote_interno = lote.get('lote_interno')
                        if not lote_interno:
                            lote_interno = self.generar_lote_interno(str(sug_id))
                            
                        lote_fabrica = lote.get('lote_fabrica')
                        vencimiento = lote.get('fecha_vencimiento') # YYYY-MM-DD o None
                        cant_lote = float(lote.get('cantidad', 0))
                        
                        if cant_lote > 0:
                            sql_lote = """
                                INSERT INTO pal_recepciones_lotes 
                                (recepcion_detalle_id, lote_interno, lote_fabrica, fecha_vencimiento, cantidad)
                                VALUES (?, ?, ?, ?, ?)
                            """
                            self.db_manager.execute_query(sql_lote, (detalle_id, lote_interno, lote_fabrica, vencimiento, cant_lote))
                
                # Actualizar acumulados en sugerencia
                # Calcular nuevo total y estado
                sql_upd = """
                    UPDATE pal_sugerencias_transferencia
                    SET cantidad_recibida_total = ISNULL(cantidad_recibida_total, 0) + ?,
                        estado_recepcion = CASE 
                            WHEN (ISNULL(cantidad_recibida_total, 0) + ?) >= cantidad_sugerida THEN 'completada'
                            ELSE 'parcial'
                        END,
                        estado = CASE 
                            WHEN (ISNULL(cantidad_recibida_total, 0) + ?) >= cantidad_sugerida THEN 'completada'
                            ELSE estado
                        END
                    WHERE id = ?
                """
                self.db_manager.execute_query(sql_upd, (cant_rec, cant_rec, cant_rec, sug_id))
                
                # Actualizar compromiso según recepción parcial o total
                # Buscar datos de la sugerencia para localizar el compromiso
                sql_sug_info = "SELECT producto_codigo, sucursal_origen_sugerida, sucursal_destino, cantidad_sugerida, maestro_id FROM pal_sugerencias_transferencia WHERE id = ?"
                sug_info = self.db_manager.fetch_data(sql_sug_info, (sug_id,))
                if sug_info:
                    s_prod, s_orig, s_dest, s_cant_sug, s_maestro = sug_info[0]
                    cant_recibida_total_nueva = float(self.db_manager.fetch_data(
                        "SELECT cantidad_recibida_total FROM pal_sugerencias_transferencia WHERE id = ?", (sug_id,)
                    )[0][0] or 0)
                    
                    es_recepcion_total = cant_recibida_total_nueva >= float(s_cant_sug)
                    
                    if es_recepcion_total:
                        # Recepción total: cerrar compromiso
                        if s_maestro:
                            sql_close = """UPDATE pal_compromisos_inventario SET estado = 'completado', fecha_actualizacion = GETDATE()
                                WHERE referencia_maestro = ? AND producto_codigo = ? AND sucursal_destino = ? AND estado = 'activo'"""
                            self.db_manager.execute_query(sql_close, (s_maestro, s_prod, s_dest))
                        else:
                            sql_close = """UPDATE pal_compromisos_inventario SET estado = 'completado', fecha_actualizacion = GETDATE()
                                WHERE producto_codigo = ? AND sucursal_origen = ? AND sucursal_destino = ? AND estado = 'activo' AND referencia_maestro IS NULL"""
                            self.db_manager.execute_query(sql_close, (s_prod, s_orig, s_dest))
                    else:
                        # Recepción parcial: restar cantidad recibida del compromiso
                        if s_maestro:
                            sql_reduce = """UPDATE pal_compromisos_inventario SET cantidad = cantidad - ?, fecha_actualizacion = GETDATE()
                                WHERE referencia_maestro = ? AND producto_codigo = ? AND sucursal_destino = ? AND estado = 'activo'"""
                            self.db_manager.execute_query(sql_reduce, (cant_rec, s_maestro, s_prod, s_dest))
                        else:
                            sql_reduce = """UPDATE pal_compromisos_inventario SET cantidad = cantidad - ?, fecha_actualizacion = GETDATE()
                                WHERE producto_codigo = ? AND sucursal_origen = ? AND sucursal_destino = ? AND estado = 'activo' AND referencia_maestro IS NULL"""
                            self.db_manager.execute_query(sql_reduce, (cant_rec, s_prod, s_orig, s_dest))
                        
                        # Si la cantidad llegó a 0 o menos, cerrar el compromiso
                        sql_check_zero = """UPDATE pal_compromisos_inventario SET estado = 'completado', fecha_actualizacion = GETDATE()
                            WHERE cantidad <= 0 AND estado = 'activo'"""
                        self.db_manager.execute_query(sql_check_zero)

            # 4. Actualizar estado global de la transferencia
            # Verificar si quedan items pendientes
            sql_check = """
                SELECT COUNT(*) 
                FROM pal_sugerencias_transferencia 
                WHERE maestro_id = ? AND estado_recepcion != 'completada'
            """
            pendientes = self.db_manager.fetch_data(sql_check, (transferencia_id,))
            count_pendientes = pendientes[0][0] if pendientes else 0
            
            nuevo_estado_trs = 'recibida_total' if count_pendientes == 0 else 'recibida_parcial'
            
            sql_trs = "UPDATE pal_transferencias_maestro SET estado = ? WHERE id = ?"
            self.db_manager.execute_query(sql_trs, (nuevo_estado_trs, transferencia_id))
            
            # 5. Si la transferencia está completamente recibida, cerrar TODOS los compromisos activos de esta TRS
            if nuevo_estado_trs == 'recibida_total':
                sql_close_all = """UPDATE pal_compromisos_inventario SET estado = 'completado', fecha_actualizacion = GETDATE()
                    WHERE referencia_maestro = ? AND estado = 'activo'"""
                self.db_manager.execute_query(sql_close_all, (transferencia_id,))
                logger.info(f"Todos los compromisos de TRS {transferencia_id} cerrados (recepción total)")
            
            logger.info(f"Recepción {numero_recepcion} registrada para TRS ID {transferencia_id}. Estado: {nuevo_estado_trs}")
            return {"success": True, "numero_recepcion": numero_recepcion, "estado_transferencia": nuevo_estado_trs}
            
        except Exception as e:
            logger.error(f"Error registrando recepción para TRS {transferencia_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
