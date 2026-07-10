# Errores conocidos (gotchas)

> Las trampas que ya te han mordido. Cada una ahorra una hora de Claude (y tuya).

## Problemas de Jerarquía y Rendimiento (N+1 queries)
- **Pasa cuando:** Haces consultas complejas que involucran jerarquía de productos y el sistema se cuelga.
- **Causa real:** Leer la jerarquía producto por producto desde BD en lugar de usar un diccionario en memoria.
- **Solución:** Usar `cargar_jerarquia_unificada()` en `app.py` que almacena en caché o usar `load_all_jerarquia()` del servicio de stock.

## Bloqueos de la Interfaz Gráfica (Tkinter Frozen)
- **Pasa cuando:** Al presionar "Filtrar", "Exportar" o "Buscar", la aplicación deja de responder por varios segundos.
- **Causa real:** Ejecución de queries pesados (`database.py`) o procesamiento de grandes volúmenes de datos en el hilo principal de Tkinter.
- **Solución:** Enviar el proceso a un pool de conexión por hilo (Thread) y usar el patrón de callbacks con `app.after()` para actualizar la UI con el progreso.

## Inconsistencia en Códigos de Producto
- **Pasa cuando:** Un producto "0015" de la BD no hace "match" con su código de venta "15".
- **Causa real:** Los sistemas legacy guardan ceros a la izquierda a veces, a veces no.
- **Solución:** Usar siempre la función de normalización (ej. `_normalize_code(value)` que aplica `lstrip('0')`) antes de comparar códigos o buscar en diccionarios.

## Exportación a Excel Corrupta
- **Pasa cuando:** Se genera un reporte Excel masivo, finaliza con éxito, pero al intentar abrirlo MS Excel lanza un error de "Archivo corrupto" o "Problema con el contenido".
- **Causa real:** Caracteres de control invisibles en la descripción larga (`C_DESCRI`) del producto que corrompen el XML subyacente del XLSX.
- **Solución:** Aplicar SIEMPRE `clean_for_excel()` o expresiones regulares para limpiar caracteres de control antes de escribir datos de texto en celdas de Excel.
