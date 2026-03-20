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
        
    def calcular_sugerencias(self, sede_destino, dept_cod=None, group_cod=None, sub_cod=None):
        """
        Calcula sugerencias de transferencia para una sede destino.
        Permite filtrar por departamento, grupo y subgrupo.
        """
        try:
            logger.info(f"Iniciando cálculo de abastecimiento para {sede_destino}")
            
            # 1. Obtener configuración de sedes desde ConfigManager
            from pal.core.config_manager import ConfigManager
            config_mgr = ConfigManager(self.db_manager)
            sedes_config = config_mgr.get_sedes_config()
            
            # 2. Identificar almacenes tratables para la sede destino
            if sede_destino not in sedes_config:
                logger.error(f"Sede {sede_destino} no configurada.")
                return []
                
            almacenes_destino = sedes_config[sede_destino].get("almacenes_tratables", [])
            if not almacenes_destino:
                logger.warning(f"Sede {sede_destino} no tiene almacenes tratables configurados.")
                return []

            # 3. Obtener parámetros dinámicos
            params_db = self.obtener_parametros()
            # Convertir a dict para fácil acceso {categoria_id: (dias_stock, quiebre, auto, analisis)}
            # categoria_id=None es el global
            config_params = {p[0]: (p[1], p[2], p[3], p[4]) for p in params_db}
            default_dias, default_quiebre, default_umbral, default_analisis = config_params.get(None, (25, 50, 0, 365))
            
            # Aplicar valores por defecto si son 0 o None (según requerimiento: 25 días si es 0)
            if not default_dias: default_dias = 25
            if default_umbral is None: default_umbral = 0

            # 4a. Identificar CDTs (necesario antes para excluirlos del stock sede)
            cdts_pre = []
            for s_cfg_pre in sedes_config.values():
                if s_cfg_pre.get("almacenes_cdt"):
                    cdts_pre.extend(s_cfg_pre["almacenes_cdt"])

            # Excluir CDTs del stock de la sede destino
            # (el stock de un CDT no cuenta como stock disponible en la sede)
            almacenes_no_cdt = [a for a in almacenes_destino if a not in cdts_pre]
            almacenes_stock = almacenes_no_cdt if almacenes_no_cdt else almacenes_destino

            dest_placeholders = ",".join(["?"] * len(almacenes_stock))

            join_productos = ""
            where_filtros = ""
            filtros_params = []

            if dept_cod or group_cod or sub_cod:
                join_productos = "JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.c_codigo"
                filtros_cond = []
                if dept_cod:
                    filtros_cond.append("p.c_departamento = ?")
                    filtros_params.append(dept_cod)
                if group_cod:
                    filtros_cond.append("p.c_grupo = ?")
                    filtros_params.append(group_cod)
                if sub_cod:
                    filtros_cond.append("p.c_subgrupo = ?")
                    filtros_params.append(sub_cod)

                if filtros_cond:
                    where_filtros = " AND " + " AND ".join(filtros_cond)

            sql_stock_destino = f"""
                SELECT d.c_codarticulo, SUM(d.n_cantidad) as stock_actual, MAX(p.c_grupo) as cat_id, 
                       MAX(p.cu_descripcion_corta) as desc_corta,
                       MAX(p.C_DESCRI) as desc_larga
                FROM MA_DEPOPROD d WITH (NOLOCK)
                JOIN MA_PRODUCTOS p WITH (NOLOCK) ON d.c_codarticulo = p.c_codigo
                WHERE d.c_coddeposito IN ({dest_placeholders}){where_filtros}
                GROUP BY d.c_codarticulo
            """

            logger.info(f"Ejecutando consulta de stock destino (excluyendo CDTs {cdts_pre})...")
            params = tuple(almacenes_stock) + tuple(filtros_params)
            stock_dest = self.db_manager.fetch_data(sql_stock_destino, params)
            total_candidatos = len(stock_dest)
            logger.info(f"Se analizarán {total_candidatos} productos con presencia en la sede.")
            
            # 5. Cargar productos "ROJOS" (no trasladables)
            logger.info("Cargando productos rojos...")
            sql_rojos = "SELECT producto_codigo FROM pal_productos_no_trasladables WHERE (sede_destino = ? OR sede_destino IS NULL) AND activo = 1"
            res_rojos = self.db_manager.fetch_data(sql_rojos, (sede_destino,))
            # Normalizar: quitar ceros a la izquierda y espacios
            productos_rojos = set()
            for r in res_rojos:
                cod_norm = str(r[0]).strip().lstrip('0')
                if not cod_norm: cod_norm = "0"
                productos_rojos.add(cod_norm)
            logger.info(f"Productos rojos obtenidos: {len(productos_rojos)}")

            # 6. Identificar CDTs
            logger.info("Identificando CDTs...")
            cdts = []
            for s_name, s_cfg in sedes_config.items():
                if s_cfg.get("almacenes_cdt"):
                    cdts.extend(s_cfg["almacenes_cdt"])
            
            if not cdts:
                logger.warning("No hay CDTs configurados.")
                return []
            logger.info(f"CDTs identificados: {cdts}")
            
            # 7. Cargar compromisos actuales para evitar sobre-solicitar
            logger.info("Cargando compromisos...")
            sql_comp = "SELECT producto_codigo, cantidad_sugerida FROM pal_sugerencias_transferencia WHERE sucursal_destino = ? AND estado IN ('pendiente', 'aprobada')"
            res_comp = self.db_manager.fetch_data(sql_comp, (sede_destino,))
            dict_compromisos = {}
            for c_cod, c_qty in res_comp:
                dict_compromisos[c_cod] = dict_compromisos.get(c_cod, 0) + float(c_qty)
            logger.info(f"Compromisos cargados para {len(dict_compromisos)} productos")

            # Ya NO filtramos codigos aquí, los procesaremos y restaremos en la fórmula de necesidad
            codigos_filtrados = [item[0] for item in stock_dest]
            
            if not codigos_filtrados:
                logger.info("No hay nuevos productos que requieran abastecimiento tras filtros.")
                return []

            # 8. Consultar datos críticos — búsqueda en cascada de períodos
            # Obtenemos parámetros globales (Default 25 días si es 0, umbral 0 = desactivado)
            params_vals = config_params.get(None, (25, 25, 0, 365))
            dias_obj = float(params_vals[0] if params_vals[0] else 25)
            umb_quiebre = float(params_vals[1] if params_vals[1] else 25)
            umbral_auto = float(params_vals[2] if params_vals[2] is not None else 0)

            # Ventanas en cascada: [N, 2N, 3N] — máximo = dias_obj × 3
            max_dias = int(dias_obj * 3)
            periodos_cascada = [int(dias_obj), int(dias_obj * 2), max_dias]

            logger.info(f"Buscando ventas en cascada: {periodos_cascada} días (máx {max_dias})")
            dict_fechas = self.db_manager.obtener_fechas_liquidacion_y_ventas(
                codigos_filtrados, almacenes_destino, dias_obj=int(dias_obj)
            )
            logger.info(f"Datos críticos obtenidos para {len(dict_fechas)} productos.")

            # Consultar stock en CDTs
            cdt_placeholders = ",".join(["?"] * len(cdts))

            dict_stock_cdt = {}
            chunk_size = 500
            for i in range(0, len(codigos_filtrados), chunk_size):
                chunk = codigos_filtrados[i:i + chunk_size]
                placeholders_cods = ",".join(["?"] * len(chunk))

                sql_bulk_cdt = f"""
                    SELECT c_codarticulo, c_coddeposito, n_cantidad
                    FROM MA_DEPOPROD WITH (NOLOCK)
                    WHERE c_codarticulo IN ({placeholders_cods})
                    AND c_coddeposito IN ({cdt_placeholders})
                    AND n_cantidad > 0
                """
                res_bulk = self.db_manager.fetch_data(sql_bulk_cdt, tuple(chunk) + tuple(cdts))

                for r_cod, r_dep, r_qty in res_bulk:
                    if r_cod not in dict_stock_cdt:
                        dict_stock_cdt[r_cod] = []
                    dict_stock_cdt[r_cod].append((r_dep, r_qty))

            # 9. Generar sugerencias — lógica de búsqueda en cascada
            sugerencias = []
            for item in stock_dest:
                codigo = item[0]
                stock_actual = float(item[1])
                # Usar desc_corta preferentemente para la UI, fallback a desc_larga
                desc_corta = str(item[3] or item[4] or "SIN DESCRIPCIÓN")
                desc_larga = str(item[4] or "SIN DESCRIPCIÓN")

                qty_compromiso = dict_compromisos.get(codigo, 0)

                # Normalización para check de Lista Roja
                cod_norm = str(codigo).strip().lstrip('0')
                if not cod_norm: cod_norm = "0"
                es_rojo = cod_norm in productos_rojos

                datos_ri = dict_fechas.get(codigo)
                if not datos_ri:
                    continue

                last_ven = datos_ri['ultima_venta']
                periodos_vals = datos_ri.get('periodos', {})

                hoy = datetime.now()
                dias_desde_ultima_venta = (hoy - last_ven).days if last_ven else 999

                # Buscar el período más corto que tenga ventas > 0
                promedio_diario = 0
                periodo_usado = None
                for per in periodos_cascada:
                    units_en_periodo = periodos_vals.get(per, 0)
                    if units_en_periodo > 0:
                        promedio_diario = units_en_periodo / per
                        periodo_usado = per
                        break

                # Si no encontró ventas en ningún período → stock muerto
                if promedio_diario <= 0:
                    # Excepción: si tiene stock 0 y vendió algo recientemente, sugerimos mínimo
                    if stock_actual <= 0 and dias_desde_ultima_venta <= int(dias_obj):
                        promedio_diario = 1 / int(dias_obj)  # mínimo representativo
                        periodo_usado = int(dias_obj)
                    elif stock_actual > 0:
                        continue  # Stock positivo sin demanda → no sugerir
                    else:
                        continue

                # Filtro de actividad: si la última venta fue hace más de dias_obj días y no tiene ventas → muerto
                if stock_actual > 0 and dias_desde_ultima_venta > max_dias:
                    continue

                # FILTRO: "Gatillo de Resurtido" (Solo si cobertura < umb_quiebre)
                dias_para_quiebre = stock_actual / promedio_diario if promedio_diario > 0 else (0 if stock_actual <= 0 else 999)

                if dias_para_quiebre >= umb_quiebre and not es_rojo:
                    continue

                # Stock Ideal = promedio_diario × dias_obj × 1.25 (seguridad) × 1.15 (logistica)
                stock_ideal_teorico = promedio_diario * dias_obj * 1.25 * 1.15
                stock_ideal = max(0, int(round(stock_ideal_teorico)))
                
                # Necesidad = Ideal - Actual - Comprometido
                necesidad = stock_ideal - stock_actual - qty_compromiso

                if necesidad > 0:
                    # Redondear hacia arriba para reabastecimiento
                    necesidad_final = int(necesidad) + (1 if necesidad % 1 > 0 else 0)
                    
                    # Obtener stock disponible en CDTs
                    disponibles = dict_stock_cdt.get(codigo, [])
                    
                    if not disponibles:
                        # Si no hay stock en CDT, igual sugerimos pero con origen "S/S" (Sin Stock)
                        # para que aparezca en morado en la UI
                        sugerencias.append({
                            "producto_codigo": codigo,
                            "producto_descripcion": desc_corta,
                            "producto_descripcion_larga": desc_larga,
                            "sucursal_destino": sede_destino,
                            "sucursal_origen_sugerida": "SIN STOCK CDT",
                            "cantidad_sugerida": necesidad_final,
                            "stock_actual": stock_actual,
                            "stock_origen": 0,
                            "requiere_autorizacion": 0,
                            "es_rojo": es_rojo,
                            "dias_stock_objetivo": dias_obj,
                            "promedio_diario": round(promedio_diario, 4)
                        })
                    else:
                        for cdt_dep, cdt_qty in disponibles:
                            cantidad_a_mover = min(necesidad_final, cdt_qty)
                            if cantidad_a_mover <= 0: continue
                            
                            sugerencias.append({
                                "producto_codigo": codigo,
                                "producto_descripcion": desc_corta,
                                "producto_descripcion_larga": desc_larga,
                                "sucursal_destino": sede_destino,
                                "sucursal_origen_sugerida": cdt_dep,
                                "cantidad_sugerida": cantidad_a_mover,
                                "stock_actual": stock_actual,
                                "stock_origen": cdt_qty,
                                "requiere_autorizacion": 1 if es_rojo or (umbral_auto > 0 and cantidad_a_mover > umbral_auto) else 0,
                                "es_rojo": es_rojo,
                                "dias_stock_objetivo": dias_obj,
                                "promedio_diario": round(promedio_diario, 4)
                            })
                            break
            
            return sugerencias
        except Exception as e:
            logger.error(f"Error calculando abastecimiento: {e}")
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
            
            # 1. Obtener configuración
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

            # 2. Parámetros (Default 25 días si es 0, umbral 0 = desactivado)
            params_db = self.obtener_parametros()
            config_params = {p[0]: (p[1], p[2], p[3], p[4]) for p in params_db}
            default_dias, _, default_umbral, _ = config_params.get(None, (25, 50, 0, 365))
            
            dias_obj = float(default_dias if default_dias else 25)
            umbral_auto = float(default_umbral if default_umbral is not None else 0)
            
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
                
            # 2b. Cargar compromisos actuales (Sugerencias Pendientes o Aprobadas)
            sql_comp = "SELECT producto_codigo, sucursal_destino, cantidad_sugerida FROM pal_sugerencias_transferencia WHERE estado IN ('pendiente', 'aprobada')"
            res_comp = self.db_manager.fetch_data(sql_comp)
            dict_compromisos = {} # {codigo: {sede: cantidad}}
            for c_cod, c_sede, c_qty in res_comp:
                if c_cod not in dict_compromisos: dict_compromisos[c_cod] = {}
                dict_compromisos[c_cod][c_sede] = dict_compromisos[c_cod].get(c_sede, 0) + float(c_qty)
                
            periodos_cascada = [int(dias_obj), int(dias_obj * 2), int(dias_obj * 3)]

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
            stock_cdt_global = {r[0]: {"total": float(r[1]), "deposito": r[2]} for r in res_cdt}
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
                if codigo not in stock_cdt_global: continue
                
                stock_cdt_disp = stock_cdt_global[codigo]["total"]
                depo_cdt = stock_cdt_global[codigo]["deposito"]
                
                demandas = [] # [(sede, deficit, promedio_diario)]
                total_deficit = 0
                
                for s_name in sedes_destino.keys():
                    v_data = datos_ventas_global.get(codigo, {}).get(s_name)
                    if not v_data: continue
                    
                    promedio = v_data['promedio']
                    stock_actual = stock_por_sede.get(codigo, {}).get(s_name, 0)
                    qty_compromiso = dict_compromisos.get(codigo, {}).get(s_name, 0)
                    
                    # Validar si es ROJO para esta sede (con normalización)
                    cod_norm = str(codigo).strip().lstrip('0')
                    if not cod_norm: cod_norm = "0"
                    
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
                    deficit = max(0, int(stock_ideal - stock_actual - qty_compromiso))
                    
                    if deficit > 0:
                        demandas.append({
                            "sede": s_name,
                            "deficit": deficit,
                            "promedio": promedio,
                            "stock_actual": stock_actual
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
                    cantidad_sugerida = dem["cantidad_sugerida"]
                    if cantidad_sugerida <= 0: continue
                    
                    # Validar si es ROJO para esta sede
                    rojos_prod = dict_rojos.get(codigo, set())
                    es_rojo = (dem["sede"] in rojos_prod) or (None in rojos_prod)
                    
                    sugerencias_finales.append({
                        "producto_codigo": codigo,
                        "producto_descripcion": descripciones.get(codigo, {}).get("corta", "SIN DESCRIPCIÓN"),
                        "producto_descripcion_larga": descripciones.get(codigo, {}).get("larga", "SIN DESCRIPCIÓN"),
                        "sucursal_destino": dem["sede"],
                        "sucursal_origen_sugerida": depo_cdt,
                        "cantidad_sugerida": cantidad_sugerida,
                        "stock_actual": dem["stock_actual"],
                        "stock_origen": stock_cdt_disp,
                        "requiere_autorizacion": 1 if es_rojo or (umbral_auto > 0 and cantidad_sugerida > umbral_auto) else 0,
                        "es_rojo": es_rojo,
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
                    if data['p1'] > 0:
                        promedio = data['p1'] / p1
                    elif data['p2'] > 0:
                        promedio = data['p2'] / p2
                    elif data['p3'] > 0:
                        promedio = data['p3'] / p3
                    
                    res_final[r_cod][s_name] = {
                        "total": data['p1'] if promedio > 0 else 0,
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
            # 1. Obtener datos de la sugerencia original para auditoría
            sql_orig = "SELECT producto_codigo, sucursal_origen_sugerida, sucursal_destino, cantidad_sugerida FROM pal_sugerencias_transferencia WHERE id = ?"
            orig = self.db_manager.fetch_data(sql_orig, (sugerencia_id,))
            if not orig:
                return False
            
            prod, orig_sede, dest_sede, cant_orig = orig[0]

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
            
            return True
        except Exception as e:
            logger.error(f"Error registrando autorización: {e}")
            return False

    def save_sugerencias(self, sugerencias, usuario_id=None):
        """Guarda las sugerencias generadas en la tabla pal_sugerencias_transferencia."""
        try:
            sql = """
                INSERT INTO pal_sugerencias_transferencia 
                (producto_codigo, sucursal_destino, sucursal_origen_sugerida, cantidad_sugerida, 
                 cantidad_disponible, stock_actual, requiere_autorizacion, estado, fue_autorizada, 
                 fecha_autorizacion, usuario_autoriza, cantidad_pre_ajuste, es_producto_rojo, tipo_solicitud)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            from datetime import datetime
            for s in sugerencias:
                es_auto = (s.get("requiere_autorizacion", 1) == 0)
                estado_final = 'aprobada' if es_auto else 'pendiente'
                fue_aut = 1 if es_auto else 0
                fecha_aut = datetime.now() if es_auto else None
                u_aut = usuario_id if es_auto else None
                cant_sug = s["cantidad_sugerida"]
                cant_orig = s.get("_cantidad_original", cant_sug)
                
                es_rojo = 1 if s.get("es_rojo", False) else 0
                tipo_sol = 'producto_rojo' if es_rojo else 'normal'
                
                params = (
                    s["producto_codigo"],
                    s["sucursal_destino"],
                    s["sucursal_origen_sugerida"],
                    cant_sug,
                    s["stock_origen"],
                    s["stock_actual"],
                    s["requiere_autorizacion"],
                    estado_final,
                    fue_aut,
                    fecha_aut,
                    u_aut,
                    cant_orig,
                    es_rojo,
                    tipo_sol
                )
                self.db_manager.execute_query(sql, params)
            return True
        except Exception as e:
            logger.error(f"Error guardando sugerencias: {e}")
            return False
