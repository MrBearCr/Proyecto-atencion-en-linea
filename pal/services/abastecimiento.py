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
            default_dias, default_quiebre, default_umbral, default_analisis = config_params.get(None, (7, 50, 10, 365))

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
                SELECT d.c_codarticulo, SUM(d.n_cantidad) as stock_actual, MAX(p.c_grupo) as cat_id, MAX(p.c_descri) as descripcion
                FROM MA_DEPOPROD d WITH (NOLOCK)
                JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.c_codigo
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
            productos_rojos = {r[0] for r in res_rojos}
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
            
            # 7. Cargar compromisos actuales para evitar duplicar sugerencias
            logger.info("Cargando compromisos...")
            sql_comp = "SELECT producto_codigo FROM pal_sugerencias_transferencia WHERE sucursal_destino = ? AND estado IN ('pendiente', 'aprobada')"
            res_comp = self.db_manager.fetch_data(sql_comp, (sede_destino,))
            compromisos_activos = {c[0] for c in res_comp}
            logger.info(f"Compromisos cargados: {len(compromisos_activos)}")

            # Solo procesamos productos que no tengan compromisos activos
            # (YA NO filtramos los rojos aquí porque queremos mostrarlos en la UI)
            codigos_filtrados = [item[0] for item in stock_dest if item[0] not in compromisos_activos]
            
            if not codigos_filtrados:
                logger.info("No hay nuevos productos que requieran abastecimiento tras filtros.")
                return []

            # 8. Consultar datos críticos — búsqueda en cascada de períodos
            # Obtenemos parámetros globales
            params_vals = config_params.get(None, (30, 50, 10, 365))
            dias_obj = float(params_vals[0] if params_vals[0] is not None else 30)
            umbral_auto = float(params_vals[2] if params_vals[2] is not None else 10)

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

                if codigo in compromisos_activos:
                    continue

                es_rojo = codigo in productos_rojos

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

                # FILTRO: "Posible Quiebre" (< dias_obj días de cobertura)
                dias_para_quiebre = stock_actual / promedio_diario if promedio_diario > 0 else (0 if stock_actual <= 0 else 999)

                if dias_para_quiebre >= dias_obj and not es_rojo:
                    continue

                # Stock Ideal = promedio_diario × dias_obj × 1.25 (seguridad) × 1.15 (logistica)
                stock_ideal_teorico = promedio_diario * dias_obj * 1.25 * 1.15
                stock_ideal = max(0, int(round(stock_ideal_teorico)))
                
                # Necesidad = Ideal - Actual
                necesidad = stock_ideal - stock_actual

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
                            "producto_descripcion": item[3],
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
                                "producto_descripcion": item[3],
                                "sucursal_destino": sede_destino,
                                "sucursal_origen_sugerida": cdt_dep,
                                "cantidad_sugerida": cantidad_a_mover,
                                "stock_actual": stock_actual,
                                "stock_origen": cdt_qty,
                                "requiere_autorizacion": 1 if cantidad_a_mover > umbral_auto else 0,
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

    def save_sugerencias(self, sugerencias):
        """Guarda las sugerencias generadas en la tabla pal_sugerencias_transferencia."""
        try:
            sql = """
                INSERT INTO pal_sugerencias_transferencia 
                (producto_codigo, sucursal_destino, sucursal_origen_sugerida, cantidad_sugerida, 
                 cantidad_disponible, stock_actual, requiere_autorizacion, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            for s in sugerencias:
                params = (
                    s["producto_codigo"],
                    s["sucursal_destino"],
                    s["sucursal_origen_sugerida"],
                    s["cantidad_sugerida"],
                    s["stock_origen"],
                    s["stock_actual"],
                    s["requiere_autorizacion"],
                    'pendiente'
                )
                self.db_manager.execute_query(sql, params)
            return True
        except Exception as e:
            logger.error(f"Error guardando sugerencias: {e}")
            return False
