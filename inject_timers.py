import os

filepath = r"c:\Users\IT y Sistemas\post-warp\Proyecto-atencion-en-linea\pal\services\exports.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replacements for export_tra_excel
replacements = [
    (
        '    try:\n        total_registros = len(datos_tra)',
        '    try:\n        import time\n        t_export_start = time.time()\n        t_last = t_export_start\n        total_registros = len(datos_tra)'
    ),
    (
        '                logger.info(f"Mapeos cargados - Departamentos: {len(dept_desc_map)}, Grupos: {len(group_desc_map)}, Subgrupos: {len(sub_desc_map)}, Marcas: {len(marca_map)}")',
        '                logger.info(f"Mapeos cargados - Departamentos: {len(dept_desc_map)}, Grupos: {len(group_desc_map)}, Subgrupos: {len(sub_desc_map)}, Marcas: {len(marca_map)}")\n                t_now = time.time()\n                logger.info(f"[EXPORT TIMER] Mapeos cargados en {t_now - t_last:.2f}s")\n                t_last = t_now'
    ),
    (
        '                    logger.info(f"[EXPORT TRA] Datos económicos cargados - Impuestos: {len(impuestos_map)}, Precios/Costos: {len(precio_map_tra)}")',
        '                    logger.info(f"[EXPORT TRA] Datos económicos cargados - Impuestos: {len(impuestos_map)}, Precios/Costos: {len(precio_map_tra)}")\n                    t_now = time.time()\n                    logger.info(f"[EXPORT TIMER] Datos económicos consultados en {t_now - t_last:.2f}s")\n                    t_last = t_now'
    ),
    (
        '            logger.info(f"[EXPORT TRA] Ofertas consultadas para {len(ofertas_map_tra)} productos")',
        '            logger.info(f"[EXPORT TRA] Ofertas consultadas para {len(ofertas_map_tra)} productos")\n            t_now = time.time()\n            logger.info(f"[EXPORT TIMER] Stocks, proveedores y ofertas procesados en {t_now - t_last:.2f}s")\n            t_last = t_now'
    ),
    (
        '        logger.info(f"[EXPORT DEBUG] Iniciando procesamiento de {len(datos_tra)} filas")',
        '        logger.info(f"[EXPORT DEBUG] Iniciando procesamiento de {len(datos_tra)} filas")\n        t_loop_start = time.time()'
    ),
    (
        '        # Crear tabla con filtros\n        end_col_letter = get_column_letter(len(headers))',
        '        t_loop_end = time.time()\n        logger.info(f"[EXPORT TIMER] Bucle de procesamiento de {total_registros} filas completado en {t_loop_end - t_loop_start:.2f}s")\n        t_last = t_loop_end\n\n        # Crear tabla con filtros\n        end_col_letter = get_column_letter(len(headers))'
    ),
    (
        '        # Guardar archivo\n        wb.save(filename)\n        logger.info(f"Exportación RI Excel completada: {total_registros} registros en {filename}")',
        '        t_now = time.time()\n        logger.info(f"[EXPORT TIMER] Generación de hojas secundarias y gráficos completada en {t_now - t_last:.2f}s")\n        t_last = t_now\n        \n        # Guardar archivo\n        wb.save(filename)\n        t_now = time.time()\n        logger.info(f"[EXPORT TIMER] Guardado del archivo Excel completado en {t_now - t_last:.2f}s")\n        logger.info(f"[EXPORT TIMER] TOTAL exportación TRA: {t_now - t_export_start:.2f}s")\n        logger.info(f"Exportación RI Excel completada: {total_registros} registros en {filename}")'
    )
]

for old, new in replacements:
    content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("done")
