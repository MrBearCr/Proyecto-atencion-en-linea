"""
Módulo de servicios de exportación para la aplicación PAL
"""
import csv
import os
from typing import List, Dict, Any, Callable, Optional
from pal.core.log import get_logger

logger = get_logger("EXPORTS")


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
    try:
        total_registros = len(datos_exportar)
        logger.info(f"Iniciando exportación de {total_registros} registros a {filename}")
        
        # Preparar headers del CSV
        headers = ['Código', 'Descripción', 'Stock Principal', 'Nivel']
        
        # Agregar columnas por ubicación seleccionada
        for ubicacion in seleccionadas:
            headers.append(f'Stock {ubicacion}')
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for i, (codigo, desc, stock, nivel) in enumerate(datos_exportar):
                try:
                    # Fila base con datos principales
                    fila = [codigo, desc, stock, nivel]
                    
                    # Agregar stock por ubicación
                    for ubicacion in seleccionadas:
                        deps = location_groups.get(ubicacion, [])
                        try:
                            # Importar función para obtener existencias
                            from pal.services.stock import get_existencias_por_ubicacion
                            existencias = get_existencias_por_ubicacion(db_manager, codigo, deps)
                            fila.append(existencias)
                        except Exception as e:
                            logger.warning(f"Error consultando stock en {ubicacion} para {codigo}: {e}")
                            fila.append(0)
                    
                    writer.writerow(fila)
                    
                    # Callback de progreso
                    if progress_cb:
                        progress_cb(i + 1, total_registros)
                        
                except Exception as e:
                    logger.error(f"Error procesando registro {i}: {codigo} - {e}")
                    continue
        
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
    try:
        total_registros = len(datos_tra)
        logger.info(f"Iniciando exportación TRA de {total_registros} registros a {filename}")
        
        headers = ['Código', 'Descripción', 'Departamento', 'Grupo', 'Subgrupo', 'Neto', 'Rotación']
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
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
                    
                    writer.writerow([codigo, desc, dept, grupo, sub, round(float(neto or 0), 2), rotacion])
                    
                    # Callback de progreso
                    if progress_cb:
                        progress_cb(i + 1, total_registros)
                        
                except Exception as e:
                    logger.error(f"Error procesando fila TRA {i}: {fila} - {e}")
                    continue
        
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
    try:
        total_registros = len(datos_mbrp)
        logger.info(f"Iniciando exportación MBRP de {total_registros} registros a {filename}")
        
        headers = ['Código', 'Descripción', 'Vendido', 'Comprado', 'Diferencia', 'Margen %']
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for i, fila in enumerate(datos_mbrp):
                try:
                    if len(fila) >= 6:
                        codigo, desc, vendido, comprado, diferencia, margen = fila[:6]
                        writer.writerow([
                            codigo, desc, 
                            round(float(vendido or 0), 2),
                            round(float(comprado or 0), 2),
                            round(float(diferencia or 0), 2),
                            f"{round(float(margen or 0), 2)}%"
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
        
        logger.info(f"Exportación MBRP completada: {total_registros} registros en {filename}")
        return total_registros
        
    except Exception as e:
        logger.error(f"Error en exportación MBRP CSV: {e}")
        raise