"""
Módulo de servicios de exportación para la aplicación PAL
"""
import csv
import os
from typing import List, Dict, Any, Callable, Optional
from pal.core.log import get_logger

logger = get_logger("EXPORTS")

# Función auxiliar para limpiar texto para Excel
def clean_for_excel(text):
    """Limpia texto para que sea compatible con Excel"""
    if text is None:
        return ""
    # Convertir a string y limpiar caracteres de control
    text = str(text)
    # Remover caracteres de control (0x00-0x1F excepto 0x09, 0x0A, 0x0D)
    cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
    # Truncar si es muy largo (Excel tiene límite de 32767 caracteres por celda)
    return cleaned[:32760] if len(cleaned) > 32760 else cleaned

# Intentar importar openpyxl para Excel
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.formatting.rule import ColorScaleRule, CellIsRule, FormulaRule
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("openpyxl no está disponible. Instale con: pip install openpyxl")


def export_stock_csv(filename: str, datos_exportar: List, seleccionadas: List[str], 
                    location_groups: Dict[str, List[str]], db_manager, 
                    progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
    """
    Exporta datos de stock a un archivo CSV con existencias por ubicación
    
    Args:
        filename: Nombre del archivo CSV a crear
        datos_exportar: Lista de datos de stock a exportar
        seleccionadas: Lista de ubicaciones seleccionadas para incluir
        location_groups: Diccionario con grupos de ubicaciones
        db_manager: Instancia del gestor de base de datos
        progress_cb: Callback opcional para reportar progreso
        
    Returns:
        int: Número total de registros exportados
    """
    from datetime import datetime
    try:
        total_registros = len(datos_exportar)
        logger.info(f"Iniciando exportación de {total_registros} registros a {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # ENCABEZADO DESCRIPTIVO DEL REPORTE
            writer.writerow([f'REPORTE DE ALERTAS DE STOCK - GENERADO EL {datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")}'])
            writer.writerow([''])
            writer.writerow([f'Total de productos en alerta: {total_registros}'])
            writer.writerow([f'Ubicaciones incluidas: {", ".join(seleccionadas)}'])
            writer.writerow([f'Depósitos consultados: {sum(len(location_groups[u]) for u in seleccionadas)}'])
            writer.writerow([''])
            writer.writerow(['NIVELES DE ALERTA:'])
            writer.writerow(['- CRÍTICA: Stock menor a 8 unidades'])
            writer.writerow(['- MEDIA: Stock entre 8 y 14 unidades'])
            writer.writerow(['- LEVE: Stock entre 15 y 20 unidades'])
            writer.writerow([''])
            writer.writerow(['DETALLE DE PRODUCTOS:'])
            writer.writerow([''])
            
            # Preparar headers de datos
            headers = ['Código Producto', 'Descripción del Producto', 'Stock Depósito Principal (0301)', 'Nivel de Alerta']
            
            # Agregar columnas por ubicación seleccionada
            for ubicacion in seleccionadas:
                headers.append(f'Existencias en {ubicacion}')
            
            writer.writerow(headers)
            # Fila separadora
            writer.writerow(['-' * 15 for _ in headers])
            
            for i, (codigo, desc, stock, nivel) in enumerate(datos_exportar):
                try:
                    # Fila base con datos principales (formato más legible)
                    nivel_texto = {
                        'critica': '⚠️ CRÍTICA',
                        'media': '🟡 MEDIA', 
                        'leve': '🟢 LEVE'
                    }.get(nivel.lower(), nivel.upper())
                    
                    fila = [
                        codigo,
                        desc,
                        f'{stock} unidades',
                        nivel_texto
                    ]
                    
                    # Agregar stock por ubicación
                    for ubicacion in seleccionadas:
                        deps = location_groups.get(ubicacion, [])
                        try:
                            # Importar función para obtener existencias
                            from pal.services.stock import get_existencias_por_ubicacion
                            existencias = get_existencias_por_ubicacion(db_manager, codigo, deps)
                            fila.append(f'{existencias} unidades' if existencias > 0 else 'Sin stock')
                        except Exception as e:
                            logger.warning(f"Error consultando stock en {ubicacion} para {codigo}: {e}")
                            fila.append('Error consulta')
                    
                    writer.writerow(fila)
                    
                    # Callback de progreso
                    if progress_cb:
                        progress_cb(i + 1, total_registros)
                        
                except Exception as e:
                    logger.error(f"Error procesando registro {i}: {codigo} - {e}")
                    continue
            
            # PIE DEL REPORTE
            writer.writerow([''])
            writer.writerow(['===== FIN DEL REPORTE ====='])
            writer.writerow([f'Archivo generado por: Sistema PAL (Proyecto Atención en Línea)'])
            writer.writerow([f'Fecha de generación: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
        
        logger.info(f"Exportación completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación CSV: {e}")
        raise


def export_tra_csv(filename: str, datos_tra: List, progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
    """
    Exporta datos TRA a un archivo CSV
    
    Args:
        filename: Nombre del archivo CSV a crear
        datos_tra: Lista de datos TRA a exportar
        progress_cb: Callback opcional para reportar progreso
        
    Returns:
        int: Número total de registros exportados
    """
    from datetime import datetime
    try:
        total_registros = len(datos_tra)
        logger.info(f"Iniciando exportación TRA de {total_registros} registros a {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # ENCABEZADO DESCRIPTIVO DEL REPORTE TRA
            writer.writerow([f'REPORTE DE TIEMPO DE ROTACIÓN Y ABASTECIMIENTO (TRA) - {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
            writer.writerow([''])
            writer.writerow([f'Total de productos analizados: {total_registros}'])
            writer.writerow([''])
            writer.writerow(['CLASIFICACIÓN DE ROTACIÓN:'])
            writer.writerow(['- ALTA: Productos con alta rotación de ventas'])
            writer.writerow(['- MEDIA: Productos con rotación moderada'])
            writer.writerow(['- BAJA: Productos con baja rotación'])
            writer.writerow(['- SIN MOVIMIENTO: Productos sin ventas en el período'])
            writer.writerow([''])
            writer.writerow(['DETALLE DE PRODUCTOS:'])
            writer.writerow([''])
            
            headers = ['Código Producto', 'Descripción del Producto', 'Departamento', 'Grupo', 'Subgrupo', 'Ventas Netas', 'Clasificación de Rotación']
            writer.writerow(headers)
            writer.writerow(['-' * 20 for _ in headers])
            
            for i, fila in enumerate(datos_tra):
                try:
                    # Manejar diferentes longitudes de fila
                    if len(fila) >= 7:
                        codigo, desc, dept, grupo, sub, neto, rotacion = fila[:7]
                    elif len(fila) >= 6:
                        codigo, desc, dept, grupo, sub, neto = fila[:6]
                        rotacion = "SIN CLASIFICAR"
                    else:
                        logger.warning(f"Fila con formato incorrecto: {fila}")
                        continue
                    
                    # Formatear datos para mejor legibilidad
                    rotacion_texto = {
                        'alta': '🟢 ALTA ROTACIÓN',
                        'media': '🟡 ROTACIÓN MEDIA',
                        'baja': '🔴 BAJA ROTACIÓN',
                        'sin_movimiento': '⚫ SIN MOVIMIENTO'
                    }.get(str(rotacion).lower(), str(rotacion).upper())
                    
                    writer.writerow([
                        codigo, 
                        desc, 
                        dept or 'Sin clasificar', 
                        grupo or 'Sin clasificar', 
                        sub or 'Sin clasificar', 
                        f'${round(float(neto or 0), 2):,.2f}', 
                        rotacion_texto
                    ])
                    
                    # Callback de progreso
                    if progress_cb:
                        progress_cb(i + 1, total_registros)
                        
                except Exception as e:
                    logger.error(f"Error procesando fila TRA {i}: {fila} - {e}")
                    continue
            
            # PIE DEL REPORTE TRA
            writer.writerow([''])
            writer.writerow(['===== FIN DEL REPORTE TRA ====='])
            writer.writerow([f'Archivo generado por: Sistema PAL (Proyecto Atención en Línea)'])
            writer.writerow([f'Fecha de generación: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
        
        logger.info(f"Exportación TRA completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación TRA CSV: {e}")
        raise


def export_mbrp_csv(filename: str, datos_mbrp: List, progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
    """
    Exporta datos MBRP a un archivo CSV
    
    Args:
        filename: Nombre del archivo CSV a crear
        datos_mbrp: Lista de datos MBRP a exportar
        progress_cb: Callback opcional para reportar progreso
        
    Returns:
        int: Número total de registros exportados
    """
    from datetime import datetime
    try:
        total_registros = len(datos_mbrp)
        logger.info(f"Iniciando exportación MBRP de {total_registros} registros a {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # ENCABEZADO DESCRIPTIVO DEL REPORTE MBRP
            writer.writerow([f'REPORTE DE MERCANCÍA DE BAJA ROTACIÓN DE PRODUCTOS (MBRP) - {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
            writer.writerow([''])
            writer.writerow([f'Total de productos analizados: {total_registros}'])
            writer.writerow([''])
            writer.writerow(['DESCRIPCIÓN DEL REPORTE:'])
            writer.writerow(['- Identifica productos con baja movilidad en inventario'])
            writer.writerow(['- Analiza relación entre ventas, compras y rentabilidad'])
            writer.writerow(['- Ayuda a optimizar la gestión de inventario'])
            writer.writerow([''])
            writer.writerow(['DETALLE DE PRODUCTOS:'])
            writer.writerow([''])
            
            headers = ['Código Producto', 'Descripción del Producto', 'Monto Vendido', 'Monto Comprado', 'Diferencia (Ganancia/Pérdida)', 'Margen de Ganancia %']
            writer.writerow(headers)
            writer.writerow(['-' * 25 for _ in headers])
            
            for i, fila in enumerate(datos_mbrp):
                try:
                    if len(fila) >= 6:
                        codigo, desc, vendido, comprado, diferencia, margen = fila[:6]
                        
                        # Formatear para mejor legibilidad
                        vendido_fmt = f'${round(float(vendido or 0), 2):,.2f}'
                        comprado_fmt = f'${round(float(comprado or 0), 2):,.2f}'
                        diferencia_val = round(float(diferencia or 0), 2)
                        diferencia_fmt = f'${diferencia_val:,.2f}' if diferencia_val >= 0 else f'-${abs(diferencia_val):,.2f}'
                        margen_val = round(float(margen or 0), 2)
                        margen_fmt = f'{margen_val:,.2f}%' + (' 🟢' if margen_val > 20 else ' 🟡' if margen_val > 5 else ' 🔴')
                        
                        writer.writerow([
                            codigo, 
                            desc, 
                            vendido_fmt,
                            comprado_fmt,
                            diferencia_fmt,
                            margen_fmt
                        ])
                    else:
                        logger.warning(f"Fila MBRP con formato incorrecto: {fila}")
                        continue
                    
                    # Callback de progreso
                    if progress_cb:
                        progress_cb(i + 1, total_registros)
                        
                except Exception as e:
                    logger.error(f"Error procesando fila MBRP {i}: {fila} - {e}")
                    continue
            
            # PIE DEL REPORTE MBRP
            writer.writerow([''])
            writer.writerow(['INTERPRETACIÓN DE INDICADORES:'])
            writer.writerow(['🟢 Margen > 20%: Excelente rentabilidad'])
            writer.writerow(['🟡 Margen 5-20%: Rentabilidad aceptable'])
            writer.writerow(['🔴 Margen < 5%: Requiere atención'])
            writer.writerow([''])
            writer.writerow(['===== FIN DEL REPORTE MBRP ====='])
            writer.writerow([f'Archivo generado por: Sistema PAL (Proyecto Atención en Línea)'])
            writer.writerow([f'Fecha de generación: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
        
        logger.info(f"Exportación MBRP completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación MBRP CSV: {e}")
        raise


# ============== FUNCIONES DE EXPORTACIÓN EXCEL ==============

def export_stock_excel(filename: str, datos_exportar: List, seleccionadas: List[str], 
                      location_groups: Dict[str, List[str]], db_manager, 
                      progress_cb: Optional[Callable[[int, int], None]] = None,
                      current_localidad: Optional[str] = None) -> int:
    """
    Exporta datos de stock a un archivo Excel con formato profesional,
    filtros, formato condicional y múltiples hojas de análisis.
    
    Args:
        filename: Nombre del archivo Excel a crear
        datos_exportar: Lista de datos de stock a exportar
        seleccionadas: Lista de ubicaciones seleccionadas
        location_groups: Diccionario con grupos de ubicaciones
        db_manager: Instancia del gestor de base de datos
        progress_cb: Callback opcional para reportar progreso
        
    Returns:
        int: Número total de registros exportados
    """
    if not EXCEL_AVAILABLE:
        logger.error("openpyxl no está disponible. Use export_stock_csv en su lugar.")
        raise ImportError("openpyxl es requerido para exportación Excel")
        
    from datetime import datetime
    import time
    
    try:
        tiempo_inicio = time.time()
        total_registros = len(datos_exportar)
        logger.info(f"[EXPORT TIMER] Iniciando exportación Excel de {total_registros} registros a {filename}")
        
        # Crear workbook
        tiempo_pre_wb = time.time()
        wb = Workbook()
        wb.remove(wb.active)  # Remover hoja por defecto
        ws_main = wb.create_sheet("Alertas de Stock")
        logger.info(f"[EXPORT TIMER] Workbook preparado en {time.time() - tiempo_pre_wb:.2f}s")
        
        # Encabezado del reporte
        ws_main['A1'] = f'REPORTE DE ALERTAS DE STOCK'
        ws_main['A2'] = f'Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")}'
        ws_main['A4'] = f'Total de productos: {total_registros}'
        ws_main['A5'] = f'Ubicaciones: {", ".join(seleccionadas)}'
        
        # Formato del encabezado
        header_font = Font(size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        ws_main['A1'].font = header_font
        ws_main['A1'].fill = header_fill
        ws_main.merge_cells('A1:G1')
        
        # Obtener nombres de depósitos desde la BD antes de crear headers
        depositos_info = {}
        try:
            depositos_result = db_manager.obtener_depositos()  # Retorna [(codigo, descripcion), ...]
            depositos_info = {codigo: descripcion for codigo, descripcion in depositos_result}
            logger.info(f"[EXPORT TIMER] Cargados {len(depositos_info)} nombres de depósitos")
        except Exception as e:
            logger.warning(f"No se pudieron cargar nombres de depósitos: {e}")
        
        # Headers de la tabla (fila 8)
        # Determinar nombres de columnas por sede según localidad actual
        sede_names = ['Cabudare', 'Barinas', 'Guanare']
        loc_actual = current_localidad if current_localidad in sede_names else 'Cabudare'
        otras = [s for s in sede_names if s != loc_actual]
        headers = ['Código', 'Descripción', 'Nivel', f'Stock {loc_actual}', f'Stock {otras[0]}', f'Stock {otras[1]}', 'Total Existencias']
        for ubicacion in seleccionadas:
            nombre_deposito = depositos_info.get(ubicacion, ubicacion)
            header_text = f'{ubicacion} - {nombre_deposito}' if nombre_deposito != ubicacion else ubicacion
            headers.append(header_text)
        
        start_row = 8
        for col, header in enumerate(headers, 1):
            cell = ws_main.cell(row=start_row, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Datos de productos - OPTIMIZADO: Obtener todas las existencias en una sola consulta
        tiempo_pre_datos = time.time()
        
        # Obtener todos los códigos de productos
        codigos_productos = [codigo for codigo, _, _, _ in datos_exportar]
        
        # Obtener existencias en BATCH con chunking para evitar límites de parámetros SQL
        logger.info(f"[EXPORT TIMER] Obteniendo existencias batch para {len(codigos_productos)} productos x {len(seleccionadas)} depósitos...")
        tiempo_pre_batch = time.time()
        
        try:
            # Inicializar mapa de existencias
            existencias_map = {codigo: {} for codigo in codigos_productos}
            for deposito in seleccionadas:
                for codigo in codigos_productos:
                    existencias_map[codigo][deposito] = 0
            
            # SQL Server tiene un límite de ~2100 parámetros
            # Con N depósitos, podemos usar (2000 - N) / 1 productos por chunk para seguridad
            max_params_per_chunk = 2000 - len(seleccionadas)
            chunk_size = max(100, max_params_per_chunk)  # Al menos 100, pero respetar límite
            
            total_chunks = (len(codigos_productos) + chunk_size - 1) // chunk_size
            logger.info(f"[EXPORT TIMER] Procesando en {total_chunks} chunks de máximo {chunk_size} productos")
            
            # Procesar en chunks con progreso
            result_batch = []
            # Reservar 10% del progreso total para la carga de chunks
            chunk_progress_weight = 0.10
            data_progress_weight = 0.90
            
            for chunk_idx in range(0, len(codigos_productos), chunk_size):
                chunk_productos = codigos_productos[chunk_idx:chunk_idx + chunk_size]
                chunk_num = (chunk_idx // chunk_size) + 1
                
                # Construir consulta para este chunk
                codigo_placeholders = ','.join('?' * len(chunk_productos))
                deposito_placeholders = ','.join('?' * len(seleccionadas))
                
                sql_chunk = (
                    f"SELECT c_codarticulo, c_coddeposito, ISNULL(SUM(n_cantidad), 0) as total "
                    f"FROM MA_DEPOPROD WITH (NOLOCK) "
                    f"WHERE c_codarticulo IN ({codigo_placeholders}) "
                    f"AND c_coddeposito IN ({deposito_placeholders}) "
                    f"GROUP BY c_codarticulo, c_coddeposito "
                    f"HAVING ISNULL(SUM(n_cantidad), 0) != 0"
                )
                
                params_chunk = chunk_productos + seleccionadas
                logger.info(f"[EXPORT TIMER] Ejecutando chunk {chunk_num}/{total_chunks} ({len(chunk_productos)} productos, {len(params_chunk)} params)")
                
                chunk_result = db_manager.fetch_data(sql_chunk, params_chunk)
                if chunk_result:
                    result_batch.extend(chunk_result)
                
                # Reportar progreso de carga de chunks (0-10% del total)
                if progress_cb:
                    chunk_progress = int((chunk_num / total_chunks) * chunk_progress_weight * total_registros)
                    progress_cb(chunk_progress, total_registros)
            
            # Poblar mapa con resultados
            if result_batch:
                for codigo, deposito, cantidad in result_batch:
                    if codigo in existencias_map:
                        existencias_map[codigo][deposito] = int(cantidad or 0)
            
            tiempo_post_batch = time.time()
            logger.info(f"[EXPORT TIMER] Existencias batch obtenidas en {tiempo_post_batch - tiempo_pre_batch:.2f}s ({total_chunks} consultas chunked, {len(result_batch)} resultados)")
            
        except Exception as e:
            logger.error(f"Error en consulta batch: {e}")
            existencias_map = {codigo: {dep: 0 for dep in seleccionadas} for codigo in codigos_productos}
        
        # Ahora procesar los datos usando el mapa precargado
        data_start_row = start_row + 1

        # Reordenar datos por severidad y por stock de la localidad actual para que las CRÍTICAS queden primero
        def _norm_nivel(n):
            s = str(n or '').upper()
            for a,b in [('Á','A'),('É','E'),('Í','I'),('Ó','O'),('Ú','U')]:
                s = s.replace(a,b)
            return s
        def _rank(n):
            s = _norm_nivel(n)
            return 0 if s == 'CRITICA' else 1 if s == 'MEDIA' else 2 if s == 'LEVE' else 3

        # Determinar orden de sedes según localidad actual (ya calculado arriba)
        sede_order = ['Cabudare', 'Barinas', 'Guanare']
        if current_localidad in sede_order:
            sede_order.remove(current_localidad)
            sede_order.insert(0, current_localidad)
        selected_by_sede = {
            'Cabudare': [d for d in seleccionadas if str(d).startswith('03')],
            'Barinas':  [d for d in seleccionadas if str(d).startswith('01')],
            'Guanare':  [d for d in seleccionadas if str(d).startswith('04')],
        }
        def _local_stock(codigo):
            dep_qty = existencias_map.get(codigo, {})
            deps_local = selected_by_sede.get(sede_order[0], [])
            return sum(int(dep_qty.get(d, 0)) for d in deps_local)

        datos_exportar = sorted(
            datos_exportar,
            key=lambda r: (
                _rank(r[3] if len(r) > 3 else ''),
                _local_stock(r[0]),
                str(r[0])
            )
        )

        # Precalcular depósitos seleccionados por sede (solo los elegidos en exportación)
        selected_by_sede = {
            'Cabudare': [d for d in seleccionadas if str(d).startswith('03')],
            'Barinas':  [d for d in seleccionadas if str(d).startswith('01')],
            'Guanare':  [d for d in seleccionadas if str(d).startswith('04')],
        }
        
        for i, (codigo, desc, stock, nivel) in enumerate(datos_exportar):
            try:
                row = data_start_row + i
                
                # Limpiar caracteres inválidos para Excel
                ws_main.cell(row=row, column=1, value=clean_for_excel(codigo))
                ws_main.cell(row=row, column=2, value=clean_for_excel(desc))
                # Normalizar nivel a MAYÚSCULAS sin acento
                nivel_excel = str(nivel).upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                ws_main.cell(row=row, column=3, value=clean_for_excel(nivel_excel))

                # Calcular stock por sedes (según prefijo de depósito)
                # Construir map rápido depósito->cantidad (filtrando SOLO los depósitos seleccionados)
                dep_qty = existencias_map.get(codigo, {})
                sum_cabu = sum(int(dep_qty.get(d, 0)) for d in selected_by_sede['Cabudare'])
                sum_bari = sum(int(dep_qty.get(d, 0)) for d in selected_by_sede['Barinas'])
                sum_guan = sum(int(dep_qty.get(d, 0)) for d in selected_by_sede['Guanare'])

                # Determinar orden según localidad actual (si se pasó)
                try:
                    current_localidad = locals().get('current_localidad', None)
                except Exception:
                    current_localidad = None
                if not current_localidad:
                    current_localidad = 'Cabudare'
                sede_order = ['Cabudare', 'Barinas', 'Guanare']
                if current_localidad in sede_order:
                    sede_order.remove(current_localidad)
                    sede_order.insert(0, current_localidad)
                # Map sede->valor
                sede_vals = {
                    'Cabudare': sum_cabu,
                    'Barinas': sum_bari,
                    'Guanare': sum_guan
                }
                stock_local = sede_vals.get(sede_order[0], 0)
                stock_o1 = sede_vals.get(sede_order[1], 0)
                stock_o2 = sede_vals.get(sede_order[2], 0)

                # Escribir columnas especiales: Stock Localidad, Stock Otras, Total
                ws_main.cell(row=row, column=4, value=int(stock_local))
                ws_main.cell(row=row, column=5, value=int(stock_o1))
                ws_main.cell(row=row, column=6, value=int(stock_o2))

                # Calcular total de existencias sumando todos los depósitos
                total_existencias = int(stock_local + stock_o1 + stock_o2)
                ws_main.cell(row=row, column=7, value=total_existencias)
                
                # Existencias por ubicación seleccionada (mantener columnas por depósito)
                start_dep_col = 8
                for j, ubicacion in enumerate(seleccionadas):
                    existencias = existencias_map.get(codigo, {}).get(ubicacion, 0)
                    ws_main.cell(row=row, column=start_dep_col + j, value=int(existencias))
                
                # Reportar progreso de procesamiento de datos (10-100% del total)
                if progress_cb:
                    chunk_progress_weight = 0.10
                    data_progress_weight = 0.90
                    base_progress = int(chunk_progress_weight * total_registros)
                    data_progress = int(((i + 1) / total_registros) * data_progress_weight * total_registros)
                    progress_cb(base_progress + data_progress, total_registros)
                    
            except Exception as e:
                logger.error(f"Error procesando registro {i}: {codigo} - {e}")
                continue
        
        tiempo_post_datos = time.time()
        logger.info(f"[EXPORT TIMER] Procesamiento de datos: {tiempo_post_datos - tiempo_pre_datos:.2f}s (1 consulta batch)")
        
        # Crear tabla con filtros
        end_col_letter = get_column_letter(len(headers))
        table_range = f"A{start_row}:{end_col_letter}{data_start_row + total_registros - 1}"
        # Actualizar o crear tabla 'TablaStock'
        existing_table = None
        try:
            for tbl in getattr(ws_main, 'tables', {}).values():
                if getattr(tbl, 'displayName', '') == 'TablaStock':
                    existing_table = tbl
                    break
        except Exception:
            pass
        if existing_table:
            existing_table.ref = table_range
        else:
            table = Table(displayName="TablaStock", ref=table_range)
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium9", showFirstColumn=False,
                showLastColumn=False, showRowStripes=True, showColumnStripes=False
            )
            ws_main.add_table(table)
        
        # Formato condicional solo para la columna Nivel
        data_range = f"C{data_start_row}:C{data_start_row + total_registros - 1}"
        
        # Crítica = Rojo (valor normalizado a MAYÚSCULAS sin acentos)
        ws_main.conditional_formatting.add(
            data_range,
            CellIsRule(operator='equal', formula=['"CRITICA"'],
                       fill=PatternFill(start_color="FF6B6B", end_color="FF6B6B"))
        )
        
        # Media = Amarillo
        ws_main.conditional_formatting.add(
            data_range,
            CellIsRule(operator='equal', formula=['"MEDIA"'],
                       fill=PatternFill(start_color="FFD93D", end_color="FFD93D"))
        )
        
        # Leve = Verde
        ws_main.conditional_formatting.add(
            data_range,
            CellIsRule(operator='equal', formula=['"LEVE"'],
                       fill=PatternFill(start_color="6BCF7F", end_color="6BCF7F"))
        )
        
        # Ajustar anchos de columna
        ws_main.column_dimensions['A'].width = 12  # Código
        ws_main.column_dimensions['B'].width = 40  # Descripción
        ws_main.column_dimensions['C'].width = 12  # Nivel
        ws_main.column_dimensions['D'].width = 15  # Stock Localidad
        ws_main.column_dimensions['E'].width = 15  # Stock Sede 1
        ws_main.column_dimensions['F'].width = 15  # Stock Sede 2
        ws_main.column_dimensions['G'].width = 15  # Total
        # Columnas por depósito comienzan en H
        for i in range(len(seleccionadas)):
            col_letter = get_column_letter(8 + i)  # 8 -> H, luego I, J, ... AA, AB, etc.
            ws_main.column_dimensions[col_letter].width = 15
        
        # === HOJA 2: RESUMEN POR NIVEL ===
        ws_summary = wb.create_sheet("Resumen por Nivel")
        
        # Contar por niveles (normalizando acentos)
        nivel_counts = {'CRITICA': 0, 'MEDIA': 0, 'LEVE': 0}
        for _, _, _, nivel in datos_exportar:
            nivel_upper = str(nivel).upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
            if nivel_upper in nivel_counts:
                nivel_counts[nivel_upper] += 1
        
        # Crear tabla resumen
        ws_summary['A1'] = 'RESUMEN POR NIVEL DE ALERTA'
        ws_summary['A1'].font = Font(size=14, bold=True)
        ws_summary.merge_cells('A1:C1')
        
        ws_summary['A3'] = 'Nivel'
        ws_summary['B3'] = 'Cantidad'
        ws_summary['C3'] = 'Porcentaje'
        
        for i, cell in enumerate(['A3', 'B3', 'C3']):
            ws_summary[cell].font = Font(bold=True)
            ws_summary[cell].fill = PatternFill(start_color="4472C4", end_color="4472C4")
            ws_summary[cell].font = Font(bold=True, color="FFFFFF")
        
        row = 4
        for nivel, count in nivel_counts.items():
            porcentaje = (count / total_registros * 100) if total_registros > 0 else 0
            ws_summary.cell(row=row, column=1, value=nivel)
            ws_summary.cell(row=row, column=2, value=count)
            ws_summary.cell(row=row, column=3, value=f"{porcentaje:.1f}%")
            row += 1
        
        # === HOJA 3: PRODUCTOS CRÍTICOS ===
        ws_critical = wb.create_sheet("Productos Críticos")
        
        productos_criticos = [(codigo, desc, stock, nivel) for codigo, desc, stock, nivel in datos_exportar 
                             if str(nivel).upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U') == 'CRITICA']
        
        ws_critical['A1'] = f'PRODUCTOS CRÍTICOS ({len(productos_criticos)} productos)'
        ws_critical['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_critical['A1'].fill = PatternFill(start_color="FF6B6B", end_color="FF6B6B")
        ws_critical.merge_cells('A1:D1')
        
        # Headers
        headers_criticos = ['Código', 'Descripción', 'Stock Actual', 'Acción Requerida']
        for col, header in enumerate(headers_criticos, 1):
            cell = ws_critical.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FFA500", end_color="FFA500")
        
        # Datos críticos
        for i, (codigo, desc, stock, _) in enumerate(productos_criticos, 4):
            ws_critical.cell(row=i, column=1, value=clean_for_excel(codigo))
            ws_critical.cell(row=i, column=2, value=clean_for_excel(desc))
            ws_critical.cell(row=i, column=3, value=int(stock))
            ws_critical.cell(row=i, column=4, value="REABASTECER URGENTE")
        
        # Ajustar columnas
        ws_critical.column_dimensions['A'].width = 12
        ws_critical.column_dimensions['B'].width = 40
        ws_critical.column_dimensions['C'].width = 15
        ws_critical.column_dimensions['D'].width = 20
        
        # Guardar archivo
        tiempo_pre_save = time.time()
        wb.save(filename)
        tiempo_post_save = time.time()
        logger.info(f"[EXPORT TIMER] Guardado de archivo: {tiempo_post_save - tiempo_pre_save:.2f}s")
        
        tiempo_total = tiempo_post_save - tiempo_inicio
        logger.info(f"[EXPORT TIMER] TOTAL exportación Excel: {tiempo_total:.2f}s para {total_registros} registros")
        logger.info(f"Exportación Excel completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación Excel: {e}")
        raise


def export_tra_excel(filename: str, datos_tra: List, db_manager=None, progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
    """
    Exporta datos TRA a un archivo Excel con formato profesional y múltiples hojas de análisis.
    
    Args:
        filename: Nombre del archivo Excel a crear
        datos_tra: Lista de datos TRA a exportar
        progress_cb: Callback opcional para reportar progreso
        
    Returns:
        int: Número total de registros exportados
    """
    if not EXCEL_AVAILABLE:
        logger.error("openpyxl no está disponible. Use export_tra_csv en su lugar.")
        raise ImportError("openpyxl es requerido para exportación Excel")
        
    from datetime import datetime
    try:
        total_registros = len(datos_tra)
        logger.info(f"Iniciando exportación TRA Excel de {total_registros} registros a {filename}")
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)  # Remover hoja por defecto
        
        # Crear diccionarios de mapeo código -> descripción para jerarquía
        dept_desc_map = {}
        group_desc_map = {}
        sub_desc_map = {}
        
        if db_manager and db_manager.ensure_connection():
            try:
                # Obtener departamentos
                depts = db_manager.fetch_data("SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS WHERE C_CODIGO IS NOT NULL AND C_DESCRIPCIO IS NOT NULL")
                dept_desc_map = {codigo: desc for codigo, desc in depts if codigo and desc}
                
                # Obtener grupos
                groups = db_manager.fetch_data("SELECT C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS WHERE C_CODIGO IS NOT NULL AND C_DESCRIPCIO IS NOT NULL")
                group_desc_map = {codigo: desc for codigo, desc in groups if codigo and desc}
                
                # Obtener subgrupos
                subs = db_manager.fetch_data("SELECT C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS WHERE C_CODIGO IS NOT NULL AND C_DESCRIPCIO IS NOT NULL")
                sub_desc_map = {codigo: desc for codigo, desc in subs if codigo and desc}
                
                logger.info(f"Mapeos cargados - Departamentos: {len(dept_desc_map)}, Grupos: {len(group_desc_map)}, Subgrupos: {len(sub_desc_map)}")
            except Exception as e:
                logger.warning(f"No se pudieron cargar las descripciones de jerarquía: {e}")
        
        # === HOJA 1: DATOS PRINCIPALES TRA ===
        ws_main = wb.create_sheet("Datos TRA")
        
        # Encabezado del reporte
        ws_main['A1'] = f'REPORTE TIEMPO DE ROTACIÓN Y ABASTECIMIENTO (TRA)'
        ws_main['A2'] = f'Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")}'
        ws_main['A4'] = f'Total de productos analizados: {total_registros}'
        
        # Formato del encabezado
        header_font = Font(size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        ws_main['A1'].font = header_font
        ws_main['A1'].fill = header_fill
        ws_main.merge_cells('A1:H1')
        
        # Headers de la tabla (fila 7)
        headers = ['Código', 'Descripción', 'Departamento', 'Grupo', 'Subgrupo', 'Ventas Netas', 'Rotación', 'Representación %']
        
        start_row = 7
        for col, header in enumerate(headers, 1):
            cell = ws_main.cell(row=start_row, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Datos de productos
        data_start_row = start_row + 1
        logger.info(f"[EXPORT DEBUG] Iniciando procesamiento de {len(datos_tra)} filas")
        
        for i, fila in enumerate(datos_tra):
            try:
                row = data_start_row + i
                
                # Manejar diferentes longitudes de fila
                if len(fila) >= 7:
                    codigo, desc, dept, grupo, sub, neto, rotacion = fila[:7]
                elif len(fila) >= 6:
                    codigo, desc, dept, grupo, sub, neto = fila[:6]
                    rotacion = "SIN CLASIFICAR"
                else:
                    continue
                
                # Convertir códigos a descripciones legibles
                dept_desc = dept_desc_map.get(dept, dept) if dept else 'Sin clasificar'
                grupo_desc = group_desc_map.get(grupo, grupo) if grupo else 'Sin clasificar'
                sub_desc = sub_desc_map.get(sub, sub) if sub else 'Sin clasificar'
                
                ws_main.cell(row=row, column=1, value=clean_for_excel(codigo))
                ws_main.cell(row=row, column=2, value=clean_for_excel(desc))
                ws_main.cell(row=row, column=3, value=clean_for_excel(dept_desc))
                ws_main.cell(row=row, column=4, value=clean_for_excel(grupo_desc))
                ws_main.cell(row=row, column=5, value=clean_for_excel(sub_desc))
                # DEBUG: Log del valor neto para los primeros 3 registros
                if i < 3:
                    logger.info(f"[EXPORT DEBUG] Fila {i}: codigo={codigo}, neto_raw={neto} (tipo={type(neto)})")
                
                neto_valor = float(neto or 0)
                # DEBUG: Log del valor convertido
                if i < 3:
                    logger.info(f"[EXPORT DEBUG] Fila {i}: neto_convertido={neto_valor}")
                
                # Aplicar el mismo formateo que en la interfaz: enteros sin decimales
                neto_formateado = int(neto_valor) if neto_valor == int(neto_valor) else round(neto_valor, 2)
                
                ws_main.cell(row=row, column=6, value=neto_formateado)
                ws_main.cell(row=row, column=7, value=clean_for_excel(str(rotacion).upper()))
                
                # Calcular porcentaje si hay datos suficientes
                total_ventas = sum(float(f[5] or 0) for f in datos_tra if len(f) >= 6)
                porcentaje = (float(neto or 0) / total_ventas * 100) if total_ventas > 0 else 0
                ws_main.cell(row=row, column=8, value=round(porcentaje, 2))
                
                if progress_cb:
                    progress_cb(i + 1, total_registros)
                    
            except Exception as e:
                logger.error(f"Error procesando fila TRA {i}: {fila} - {e}")
                continue
        
        # Crear tabla con filtros
        end_col_letter = get_column_letter(len(headers))
        table_range = f"A{start_row}:{end_col_letter}{data_start_row + total_registros - 1}"
        table = Table(displayName="TablaTRA", ref=table_range)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        ws_main.add_table(table)
        
        # Formato condicional para rotación
        rotacion_range = f"G{data_start_row}:G{data_start_row + total_registros - 1}"
        
        # Alta = Verde
        ws_main.conditional_formatting.add(rotacion_range, 
            CellIsRule(operator='equal', formula=['"ALTA"'], 
                      fill=PatternFill(start_color="4CAF50", end_color="4CAF50")))
        
        # Media = Amarillo  
        ws_main.conditional_formatting.add(rotacion_range,
            CellIsRule(operator='equal', formula=['"MEDIA"'],
                      fill=PatternFill(start_color="FF9800", end_color="FF9800")))
        
        # Baja = Rojo
        ws_main.conditional_formatting.add(rotacion_range,
            CellIsRule(operator='equal', formula=['"BAJA"'],
                      fill=PatternFill(start_color="F44336", end_color="F44336")))
        
        # Ajustar anchos de columna
        ws_main.column_dimensions['A'].width = 12  # Código
        ws_main.column_dimensions['B'].width = 40  # Descripción
        ws_main.column_dimensions['C'].width = 20  # Departamento
        ws_main.column_dimensions['D'].width = 20  # Grupo
        ws_main.column_dimensions['E'].width = 20  # Subgrupo
        ws_main.column_dimensions['F'].width = 15  # Neto
        ws_main.column_dimensions['G'].width = 12  # Rotación
        ws_main.column_dimensions['H'].width = 15  # Porcentaje
        
        # === HOJA 2: RESUMEN POR ROTACIÓN ===
        ws_summary = wb.create_sheet("Resumen por Rotación")
        
        # Contar por rotación
        rotacion_counts = {'ALTA': 0, 'MEDIA': 0, 'BAJA': 0, 'SIN MOVIMIENTO': 0, 'SIN CLASIFICAR': 0}
        for fila in datos_tra:
            if len(fila) >= 7:
                rotacion = str(fila[6]).upper()
                if rotacion in rotacion_counts:
                    rotacion_counts[rotacion] += 1
            else:
                rotacion_counts['SIN CLASIFICAR'] += 1
        
        # Crear tabla resumen
        ws_summary['A1'] = 'RESUMEN POR ROTACIÓN TRA'
        ws_summary['A1'].font = Font(size=14, bold=True)
        ws_summary.merge_cells('A1:C1')
        
        ws_summary['A3'] = 'Rotación'
        ws_summary['B3'] = 'Cantidad'
        ws_summary['C3'] = 'Porcentaje'
        
        for i, cell in enumerate(['A3', 'B3', 'C3']):
            ws_summary[cell].font = Font(bold=True, color="FFFFFF")
            ws_summary[cell].fill = PatternFill(start_color="4472C4", end_color="4472C4")
        
        row = 4
        for rotacion, count in rotacion_counts.items():
            porcentaje = (count / total_registros * 100) if total_registros > 0 else 0
            ws_summary.cell(row=row, column=1, value=rotacion)
            ws_summary.cell(row=row, column=2, value=count)
            ws_summary.cell(row=row, column=3, value=f"{porcentaje:.1f}%")
            row += 1
        
        # === HOJA 3: PRODUCTOS DE BAJA ROTACIÓN ===
        ws_low = wb.create_sheet("Baja Rotación")
        
        productos_baja = [fila for fila in datos_tra if len(fila) >= 7 and str(fila[6]).upper() == 'BAJA']
        
        ws_low['A1'] = f'PRODUCTOS DE BAJA ROTACIÓN ({len(productos_baja)} productos)'
        ws_low['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_low['A1'].fill = PatternFill(start_color="F44336", end_color="F44336")
        ws_low.merge_cells('A1:E1')
        
        # Headers
        headers_baja = ['Código', 'Descripción', 'Ventas Netas', 'Departamento', 'Acción Recomendada']
        for col, header in enumerate(headers_baja, 1):
            cell = ws_low.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="FF9800", end_color="FF9800")
        
        # Datos de baja rotación
        for i, fila in enumerate(productos_baja, 4):
            # Convertir código de departamento a descripción
            dept_codigo = fila[2] if len(fila) > 2 else None
            dept_desc = dept_desc_map.get(dept_codigo, dept_codigo) if dept_codigo else 'Sin clasificar'
            
            ws_low.cell(row=i, column=1, value=clean_for_excel(fila[0]))
            ws_low.cell(row=i, column=2, value=clean_for_excel(fila[1]))
            # Aplicar el mismo formateo que en la interfaz
            neto_valor = float(fila[5] or 0)
            neto_formateado = int(neto_valor) if neto_valor == int(neto_valor) else round(neto_valor, 2)
            ws_low.cell(row=i, column=3, value=neto_formateado)
            ws_low.cell(row=i, column=4, value=clean_for_excel(dept_desc))
            ws_low.cell(row=i, column=5, value="REVISAR ESTRATEGIA")
        
        # Ajustar columnas
        ws_low.column_dimensions['A'].width = 12
        ws_low.column_dimensions['B'].width = 40
        ws_low.column_dimensions['C'].width = 15
        ws_low.column_dimensions['D'].width = 20
        ws_low.column_dimensions['E'].width = 20
        
        # Guardar archivo
        wb.save(filename)
        logger.info(f"Exportación TRA Excel completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación TRA Excel: {e}")
        raise


def export_mbrp_excel(filename: str, datos_mbrp: List, db_manager=None, progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
    """
    Exporta datos MBRP a un archivo Excel con formato profesional y análisis de rentabilidad.
    
    Args:
        filename: Nombre del archivo Excel a crear
        datos_mbrp: Lista de datos MBRP a exportar
        progress_cb: Callback opcional para reportar progreso
        
    Returns:
        int: Número total de registros exportados
    """
    if not EXCEL_AVAILABLE:
        logger.error("openpyxl no está disponible. Use export_mbrp_csv en su lugar.")
        raise ImportError("openpyxl es requerido para exportación Excel")
        
    from datetime import datetime
    try:
        total_registros = len(datos_mbrp)
        logger.info(f"Iniciando exportación MBRP Excel de {total_registros} registros a {filename}")
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)  # Remover hoja por defecto
        
        # === HOJA 1: DATOS PRINCIPALES MBRP ===
        ws_main = wb.create_sheet("Datos MBRP")
        
        # Encabezado del reporte
        ws_main['A1'] = f'REPORTE MERCANCÍA DE BAJA ROTACIÓN (MBRP)'
        ws_main['A2'] = f'Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")}'
        ws_main['A4'] = f'Total de productos analizados: {total_registros}'
        
        # Formato del encabezado
        header_font = Font(size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        ws_main['A1'].font = header_font
        ws_main['A1'].fill = header_fill
        ws_main.merge_cells('A1:G1')
        
        # Headers de la tabla (fila 7)
        headers = ['Código', 'Descripción', 'Monto Vendido', 'Monto Comprado', 'Diferencia', 'Margen %', 'Estado']
        
        start_row = 7
        for col, header in enumerate(headers, 1):
            cell = ws_main.cell(row=start_row, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Datos de productos
        data_start_row = start_row + 1
        for i, fila in enumerate(datos_mbrp):
            try:
                if len(fila) < 6:
                    continue
                    
                row = data_start_row + i
                codigo, desc, vendido, comprado, diferencia, margen = fila[:6]
                
                ws_main.cell(row=row, column=1, value=clean_for_excel(codigo))
                ws_main.cell(row=row, column=2, value=clean_for_excel(desc))
                ws_main.cell(row=row, column=3, value=round(float(vendido or 0), 2))
                ws_main.cell(row=row, column=4, value=round(float(comprado or 0), 2))
                ws_main.cell(row=row, column=5, value=round(float(diferencia or 0), 2))
                
                margen_val = round(float(margen or 0), 2)
                ws_main.cell(row=row, column=6, value=margen_val)
                
                # Determinar estado según margen
                if margen_val > 20:
                    estado = "EXCELENTE"
                elif margen_val > 5:
                    estado = "ACEPTABLE"
                else:
                    estado = "REQUIERE ATENCIÓN"
                
                ws_main.cell(row=row, column=7, value=estado)
                
                if progress_cb:
                    progress_cb(i + 1, total_registros)
                    
            except Exception as e:
                logger.error(f"Error procesando fila MBRP {i}: {fila} - {e}")
                continue
        
        # Crear tabla con filtros
        end_col_letter = get_column_letter(len(headers))
        table_range = f"A{start_row}:{end_col_letter}{data_start_row + total_registros - 1}"
        table = Table(displayName="TablaMBRP", ref=table_range)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        ws_main.add_table(table)
        
        # Formato condicional para margen
        margen_range = f"F{data_start_row}:F{data_start_row + total_registros - 1}"
        
        # Margen > 20 = Verde
        ws_main.conditional_formatting.add(margen_range, 
            CellIsRule(operator='greaterThan', formula=[20], 
                      fill=PatternFill(start_color="4CAF50", end_color="4CAF50")))
        
        # Margen 5-20 = Amarillo  
        ws_main.conditional_formatting.add(margen_range,
            CellIsRule(operator='between', formula=[5, 20],
                      fill=PatternFill(start_color="FF9800", end_color="FF9800")))
        
        # Margen < 5 = Rojo
        ws_main.conditional_formatting.add(margen_range,
            CellIsRule(operator='lessThan', formula=[5],
                      fill=PatternFill(start_color="F44336", end_color="F44336")))
        
        # Ajustar anchos de columna
        ws_main.column_dimensions['A'].width = 12  # Código
        ws_main.column_dimensions['B'].width = 40  # Descripción
        ws_main.column_dimensions['C'].width = 15  # Vendido
        ws_main.column_dimensions['D'].width = 15  # Comprado
        ws_main.column_dimensions['E'].width = 15  # Diferencia
        ws_main.column_dimensions['F'].width = 12  # Margen
        ws_main.column_dimensions['G'].width = 18  # Estado
        
        # === HOJA 2: RESUMEN POR RENTABILIDAD ===
        ws_summary = wb.create_sheet("Resumen por Rentabilidad")
        
        # Clasificar productos
        excelente = sum(1 for fila in datos_mbrp if len(fila) >= 6 and float(fila[5] or 0) > 20)
        aceptable = sum(1 for fila in datos_mbrp if len(fila) >= 6 and 5 <= float(fila[5] or 0) <= 20)
        critico = sum(1 for fila in datos_mbrp if len(fila) >= 6 and float(fila[5] or 0) < 5)
        
        # Crear tabla resumen
        ws_summary['A1'] = 'RESUMEN POR RENTABILIDAD MBRP'
        ws_summary['A1'].font = Font(size=14, bold=True)
        ws_summary.merge_cells('A1:C1')
        
        ws_summary['A3'] = 'Categoría'
        ws_summary['B3'] = 'Cantidad'
        ws_summary['C3'] = 'Porcentaje'
        
        for i, cell in enumerate(['A3', 'B3', 'C3']):
            ws_summary[cell].font = Font(bold=True, color="FFFFFF")
            ws_summary[cell].fill = PatternFill(start_color="4472C4", end_color="4472C4")
        
        categorias = [
            ('EXCELENTE (>20%)', excelente),
            ('ACEPTABLE (5-20%)', aceptable),
            ('CRÍTICO (<5%)', critico)
        ]
        
        for i, (categoria, count) in enumerate(categorias, 4):
            porcentaje = (count / total_registros * 100) if total_registros > 0 else 0
            ws_summary.cell(row=i, column=1, value=categoria)
            ws_summary.cell(row=i, column=2, value=count)
            ws_summary.cell(row=i, column=3, value=f"{porcentaje:.1f}%")
        
        # === HOJA 3: PRODUCTOS CRÍTICOS ===
        ws_critical = wb.create_sheet("Productos Críticos")
        
        productos_criticos = [fila for fila in datos_mbrp if len(fila) >= 6 and float(fila[5] or 0) < 5]
        
        ws_critical['A1'] = f'PRODUCTOS CRÍTICOS - MARGEN < 5% ({len(productos_criticos)} productos)'
        ws_critical['A1'].font = Font(size=12, bold=True, color="FFFFFF")
        ws_critical['A1'].fill = PatternFill(start_color="F44336", end_color="F44336")
        ws_critical.merge_cells('A1:E1')
        
        # Headers
        headers_criticos = ['Código', 'Descripción', 'Margen %', 'Pérdida/Ganancia', 'Acción Requerida']
        for col, header in enumerate(headers_criticos, 1):
            cell = ws_critical.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="FF9800", end_color="FF9800")
        
        # Datos críticos
        for i, fila in enumerate(productos_criticos, 4):
            ws_critical.cell(row=i, column=1, value=clean_for_excel(fila[0]))
            ws_critical.cell(row=i, column=2, value=clean_for_excel(fila[1]))
            ws_critical.cell(row=i, column=3, value=round(float(fila[5] or 0), 2))
            ws_critical.cell(row=i, column=4, value=round(float(fila[4] or 0), 2))
            
            # Acción según margen
            margen = float(fila[5] or 0)
            if margen < 0:
                accion = "DESCONTINUAR URGENTE"
            elif margen < 2:
                accion = "REVISAR PRECIOS"
            else:
                accion = "OPTIMIZAR COSTOS"
            
            ws_critical.cell(row=i, column=5, value=accion)
        
        # Ajustar columnas
        ws_critical.column_dimensions['A'].width = 12
        ws_critical.column_dimensions['B'].width = 40
        ws_critical.column_dimensions['C'].width = 12
        ws_critical.column_dimensions['D'].width = 15
        ws_critical.column_dimensions['E'].width = 20
        
        # Guardar archivo
        wb.save(filename)
        logger.info(f"Exportación MBRP Excel completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación MBRP Excel: {e}")
        raise
