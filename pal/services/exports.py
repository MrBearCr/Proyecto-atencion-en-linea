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
    from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.worksheet.table import Table, TableStyleInfo
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
                      progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
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
    try:
        total_registros = len(datos_exportar)
        logger.info(f"Iniciando exportación Excel de {total_registros} registros a {filename}")
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)  # Remover hoja por defecto
        
        # === HOJA 1: DATOS PRINCIPALES ===
        ws_main = wb.create_sheet("Alertas de Stock")
        
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
        
        # Headers de la tabla (fila 8)
        headers = ['Código', 'Descripción', 'Stock Principal', 'Nivel', 'Total Existencias']
        headers.extend([f'{ubicacion}' for ubicacion in seleccionadas])
        
        start_row = 8
        for col, header in enumerate(headers, 1):
            cell = ws_main.cell(row=start_row, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Datos de productos
        data_start_row = start_row + 1
        for i, (codigo, desc, stock, nivel) in enumerate(datos_exportar):
            try:
                row = data_start_row + i
                
                # Limpiar caracteres inválidos para Excel
                ws_main.cell(row=row, column=1, value=clean_for_excel(codigo))
                ws_main.cell(row=row, column=2, value=clean_for_excel(desc))
                ws_main.cell(row=row, column=3, value=int(stock))
                ws_main.cell(row=row, column=4, value=clean_for_excel(nivel.upper()))
                
                total_existencias = int(stock)
                
                # Existencias por ubicación
                for j, ubicacion in enumerate(seleccionadas):
                    deps = location_groups.get(ubicacion, [])
                    try:
                        from pal.services.stock import get_existencias_por_ubicacion
                        existencias = get_existencias_por_ubicacion(db_manager, codigo, deps)
                        ws_main.cell(row=row, column=6+j, value=int(existencias))
                        total_existencias += existencias
                    except Exception as e:
                        ws_main.cell(row=row, column=6+j, value=0)
                        logger.warning(f"Error consultando {ubicacion} para {codigo}: {e}")
                
                ws_main.cell(row=row, column=5, value=total_existencias)
                
                if progress_cb:
                    progress_cb(i + 1, total_registros)
                    
            except Exception as e:
                logger.error(f"Error procesando registro {i}: {codigo} - {e}")
                continue
        
        # Crear tabla con filtros
        table_range = f"A{start_row}:{chr(65 + len(headers) - 1)}{data_start_row + total_registros - 1}"
        table = Table(displayName="TablaStock", ref=table_range)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        ws_main.add_table(table)
        
        # Formato condicional para niveles
        data_range = f"D{data_start_row}:D{data_start_row + total_registros - 1}"
        
        # Crítica = Rojo
        ws_main.conditional_formatting.add(data_range, 
            CellIsRule(operator='equal', formula=['"CRITICA"'], 
                      fill=PatternFill(start_color="FF6B6B", end_color="FF6B6B")))
        
        # Media = Amarillo  
        ws_main.conditional_formatting.add(data_range,
            CellIsRule(operator='equal', formula=['"MEDIA"'],
                      fill=PatternFill(start_color="FFD93D", end_color="FFD93D")))
        
        # Leve = Verde
        ws_main.conditional_formatting.add(data_range,
            CellIsRule(operator='equal', formula=['"LEVE"'],
                      fill=PatternFill(start_color="6BCF7F", end_color="6BCF7F")))
        
        # Ajustar anchos de columna
        ws_main.column_dimensions['A'].width = 12  # Código
        ws_main.column_dimensions['B'].width = 40  # Descripción
        ws_main.column_dimensions['C'].width = 15  # Stock
        ws_main.column_dimensions['D'].width = 12  # Nivel
        ws_main.column_dimensions['E'].width = 15  # Total
        
        for i in range(len(seleccionadas)):
            col_letter = chr(70 + i)  # F, G, H...
            ws_main.column_dimensions[col_letter].width = 15
        
        # === HOJA 2: RESUMEN POR NIVEL ===
        ws_summary = wb.create_sheet("Resumen por Nivel")
        
        # Contar por niveles
        nivel_counts = {'CRITICA': 0, 'MEDIA': 0, 'LEVE': 0}
        for _, _, _, nivel in datos_exportar:
            nivel_upper = nivel.upper()
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
                             if nivel.upper() == 'CRITICA']
        
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
        wb.save(filename)
        logger.info(f"Exportación Excel completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación Excel: {e}")
        raise
