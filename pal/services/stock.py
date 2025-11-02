"""
Módulo de gestión de stock para la aplicación PAL
"""
import json
import os
import math
from datetime import datetime, timedelta
from .filters import filter_by_hierarchy
from pal.core.log import get_logger

logger = get_logger("STOCK")

def get_existencias_por_ubicacion(db_manager, codigo, depositos, use_cache=True):
    """
    Obtiene existencias de un producto en ubicaciones específicas con cache y optimizaciones
    
    Args:
        db_manager: Instancia de DatabaseManager
        codigo: Código del producto
        depositos: Lista de códigos de depósito
        use_cache: Si usar cache local (default True)
        
    Returns:
        int: Total de existencias
    """
    import hashlib
    import time
    
    # Cache con TTL de 5 minutos para existencias
    cache_key = hashlib.md5(f"{codigo}_{','.join(sorted(depositos))}".encode()).hexdigest()
    cache_ttl = 300  # 5 minutos
    
    if use_cache and hasattr(get_existencias_por_ubicacion, '_cache'):
        cached_data = get_existencias_por_ubicacion._cache.get(cache_key)
        if cached_data and time.time() - cached_data['timestamp'] < cache_ttl:
            return cached_data['value']
    
    # Consulta optimizada con índices
    try:
        placeholders = ','.join('?' for _ in depositos)
        sql = (
            f"SELECT ISNULL(SUM(n_cantidad), 0) "
            f"FROM MA_DEPOPROD WITH (NOLOCK) "
            f"WHERE c_codarticulo = ? AND c_coddeposito IN ({placeholders}) "
            f"AND n_cantidad > 0"
        )
        params = [codigo] + depositos
        
        # Usar conexión thread-safe si está disponible
        if hasattr(db_manager, 'fetch_data_threadsafe'):
            result = db_manager.fetch_data_threadsafe(sql, params, thread_name="stock_existencias")
        else:
            result = db_manager.fetch_data(sql, params)
        
        existencias = int(result[0][0] or 0) if result else 0
        
        # Guardar en cache
        if use_cache:
            if not hasattr(get_existencias_por_ubicacion, '_cache'):
                get_existencias_por_ubicacion._cache = {}
            get_existencias_por_ubicacion._cache[cache_key] = {
                'value': existencias,
                'timestamp': time.time()
            }
            
            # Limpiar cache antiguo (máximo 100 entradas)
            if len(get_existencias_por_ubicacion._cache) > 100:
                current_time = time.time()
                keys_to_remove = [
                    k for k, v in get_existencias_por_ubicacion._cache.items()
                    if current_time - v['timestamp'] > cache_ttl
                ]
                for k in keys_to_remove:
                    del get_existencias_por_ubicacion._cache[k]
        
        return existencias
        
    except Exception as e:
        logger.error(f"Error obteniendo existencias: {e}")
        return 0

def filter_alertas(alertas, producto_jerarquia, dept_code=None, group_code=None, 
                   sub_code=None, search_text="", filter_level="TODAS", favoritos=None):
    """
    Filtra las alertas de stock según múltiples criterios
    
    Args:
        alertas: Lista de alertas desde cache
        producto_jerarquia: Dict con jerarquía de productos 
        dept_code: Código de departamento a filtrar
        group_code: Código de grupo a filtrar
        sub_code: Código de subgrupo a filtrar
        search_text: Texto para buscar en código/descripción
        filter_level: Nivel de alerta ('TODAS', 'CRÍTICA', 'MEDIA', 'LEVE')
        favoritos: Set de códigos favoritos
        
    Returns:
        list: Lista filtrada de alertas
    """
    if not alertas:
        return []
        
    datos_filtrados = list(alertas)
    favoritos = favoritos or set()
    
    # Filtro jerárquico unificado (estricto): si hay filtros activos y el producto no está en la jerarquía, se excluye
    datos_filtrados = filter_by_hierarchy(
        datos_filtrados,
        dept_code=dept_code,
        group_code=group_code,
        sub_code=sub_code,
        get_code=lambda r: r[0],
        jerarquia_map=producto_jerarquia or {},
        missing_strategy="exclude",
    )
    if any([dept_code, group_code, sub_code]):
        logger.debug(f"Filtro jerárquico aplicado - de {len(alertas)} a {len(datos_filtrados)} productos")
    
    # Filtro de texto en descripción y código
    texto_busqueda = search_text.strip().lower()
    if texto_busqueda:
        datos_filtrados = [
            r for r in datos_filtrados 
            if texto_busqueda in (str(r[1]).lower() + str(r[0]).lower())
        ]
    
    # Filtro de nivel de alerta
    filtro_nivel = filter_level.upper()
    if filtro_nivel != 'TODAS':
        datos_filtrados = [r for r in datos_filtrados if str(r[3]).upper() == filtro_nivel]
    
    # Ordenar por severidad (CRÍTICA, MEDIA, LEVE), luego por stock asc, luego favoritos (como desempate), luego código
    def _norm_nivel(n):
        s = str(n or '').upper()
        for a,b in [('Á','A'),('É','E'),('Í','I'),('Ó','O'),('Ú','U')]:
            s = s.replace(a,b)
        return s
    def _rank(n):
        s = _norm_nivel(n)
        return 0 if s == 'CRITICA' else 1 if s == 'MEDIA' else 2 if s == 'LEVE' else 3
    def _fav(code):
        try:
            return 0 if str(code) in favoritos else 1
        except Exception:
            return 1

    datos_ordenados = sorted(
        datos_filtrados,
        key=lambda r: (
            _rank(r[3] if len(r) > 3 else ''),
            int(r[2] or 0) if len(r) > 2 and r[2] is not None else 0,
            _fav(r[0]),
            str(r[0])
        )
    )
    
    return datos_ordenados


def paginate(datos, current_page, page_size):
    """
    Realiza paginación de los datos
    
    Args:
        datos: Lista de datos a paginar
        current_page: Página actual (1-indexed)
        page_size: Tamaño de página
        
    Returns:
        tuple: (datos_pagina, total_paginas, pagina_actual)
    """
    if not datos:
        return [], 1, 1
        
    total_items = len(datos)
    total_paginas = max(1, math.ceil(total_items / page_size))
    
    # Asegurar que la página actual sea válida
    current_page = max(1, min(current_page, total_paginas))
    
    # Obtener slice de datos para la página actual
    inicio = (current_page - 1) * page_size
    fin = inicio + page_size
    datos_pagina = datos[inicio:fin]
    
    return datos_pagina, total_paginas, current_page

def load_all_jerarquia(db_manager, cache_file, cache_ttl_seconds):
    """
    Carga el mapeo completo de productos a jerarquía con caché local
    
    Args:
        db_manager: Instancia de DatabaseManager
        cache_file: Ruta del archivo de caché
        cache_ttl_seconds: TTL del caché en segundos
        
    Returns:
        dict: Mapeo de código producto -> (departamento, grupo, subgrupo)
    """
    try:
        # Verificar si existe caché válido
        if os.path.exists(cache_file):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - mtime < timedelta(seconds=cache_ttl_seconds):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    # Validar que el cache tenga estructura correcta
                    if isinstance(cache_data, dict) and len(cache_data) > 0:
                        logger.success(f"Cache de jerarquía cargado: {len(cache_data)} productos")
                        return cache_data
                    else:
                        logger.warning("Cache vacío o inválido, se reconstruirá")
                except json.JSONDecodeError as e:
                    # Caché corrupto: eliminar y reconstruir
                    logger.warning(f"Cache corrupto detectado, eliminando: {e}")
                    try:
                        os.remove(cache_file)
                        logger.success("Cache corrupto eliminado")
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Error leyendo cache: {e}")
        
        # Cargar desde BD
        filas = db_manager.fetch_data(
            "SELECT C_CODIGO, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO FROM MA_PRODUCTOS"
        )
        # Incluir productos con código válido aunque algunos campos sean None, normalizando strings
        def _s(x):
            try:
                s = str(x).strip()
                return s if s and s.lower() != 'none' else ""
            except Exception:
                return ""
        jerarquia = {}
        sin_dept = 0
        sin_grupo = 0
        sin_sub = 0
        completos = 0
        for fila in filas or []:
            try:
                if not fila:
                    continue
                cod = _s(fila[0])
                if not cod:
                    continue
                dep = _s(fila[1]) if len(fila) > 1 else ""
                grp = _s(fila[2]) if len(fila) > 2 else ""
                sub = _s(fila[3]) if len(fila) > 3 else ""
                jerarquia[cod] = (dep, grp, sub)
                # Diagnóstico
                if not dep:
                    sin_dept += 1
                if not grp:
                    sin_grupo += 1
                if not sub:
                    sin_sub += 1
                if dep and grp and sub:
                    completos += 1
            except Exception:
                continue
        logger.info(f"Jerarquía cargada: {len(jerarquia)} productos | Completos: {completos} | Sin dept: {sin_dept} | Sin grupo: {sin_grupo} | Sin sub: {sin_sub}")
        
        # Guardar en caché con escritura atómica (evitar corrupción)
        try:
            # Escribir en archivo temporal primero
            temp_cache_file = cache_file + ".tmp"
            with open(temp_cache_file, 'w', encoding='utf-8') as f:
                json.dump(jerarquia, f, ensure_ascii=False, indent=2)
            
            # Validar que el archivo temporal sea válido
            with open(temp_cache_file, 'r', encoding='utf-8') as f:
                test_load = json.load(f)
                if not isinstance(test_load, dict):
                    raise ValueError("Cache inválido generado")
            
            # Si es válido, reemplazar el cache original
            if os.path.exists(cache_file):
                os.remove(cache_file)
            os.rename(temp_cache_file, cache_file)
            logger.success(f"Cache guardado exitosamente: {cache_file}")
            
        except Exception as e:
            logger.warning(f"Error guardando cache: {e}")
            # Limpiar archivo temporal si existe
            try:
                if os.path.exists(temp_cache_file):
                    os.remove(temp_cache_file)
            except Exception:
                pass
            
        return jerarquia
        
    except Exception as e:
        logger.error(f"Error cargando jerarquía: {e}")
        return {}

def build_producto_jerarquia(all_jerarquia, codigos_en_alerta):
    """
    Filtra la jerarquía usando solo los códigos actualmente en alerta, normalizando códigos.
    
    Args:
        all_jerarquia: Dict completo de jerarquía
        codigos_en_alerta: Set de códigos que están en alerta
        
    Returns:
        dict: Jerarquía filtrada solo con códigos en alerta
    """
    if not all_jerarquia or not codigos_en_alerta:
        return {}
        
    # Normalizar claves
    def _s(x):
        try:
            return str(x).strip()
        except Exception:
            return ""
    norm_map = { _s(k): v for k, v in (all_jerarquia or {}).items() }
    norm_codes = { _s(c) for c in (codigos_en_alerta or set()) }
    return {cod: norm_map[cod] for cod in norm_codes if cod in norm_map}


def fetch_stock_alerts_optimized(db_manager, limit=None, offset=0, use_indices=True):
    """
    Obtiene alertas de stock usando consulta optimizada con índices y paginación
    
    Args:
        db_manager: Instancia de DatabaseManager
        limit: Límite de registros (None para todos)
        offset: Desplazamiento para paginación
        use_indices: Si usar hints de índices para optimización
        
    Returns:
        list: Lista de tuplas (codigo, descripcion, stock, nivel)
    """
    try:
        # Consulta optimizada con índices y filtros eficientes
        base_query = """
        SELECT 
            p.C_CODIGO as codigo,
            p.C_DESCRI as descripcion,
            ISNULL(d.n_cantidad, 0) as stock,
            CASE 
                WHEN ISNULL(d.n_cantidad, 0) <= 7 THEN 'CRÍTICA'
                WHEN ISNULL(d.n_cantidad, 0) <= 15 THEN 'MEDIA'
                ELSE 'LEVE'
            END as nivel
        FROM MA_PRODUCTOS p {index_hint}
        LEFT JOIN MA_DEPOPROD d ON p.C_CODIGO = d.c_codarticulo AND d.c_coddeposito = '0301'
        WHERE p.C_ESTADO = 'A'
            AND (d.n_cantidad IS NULL OR d.n_cantidad <= 50)
            AND p.C_CODIGO IS NOT NULL
            AND p.C_DESCRI IS NOT NULL
        """
        
        # Aplicar hints de índices si están habilitados
        index_hint = "WITH (NOLOCK)" if use_indices else ""
        query = base_query.format(index_hint=index_hint)
        
        # Agregar ORDER BY y paginación
        query += "\nORDER BY ISNULL(d.n_cantidad, 0) ASC, p.C_CODIGO"
        
        if limit is not None:
            if offset > 0:
                query += f"\nOFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
            else:
                query = f"SELECT TOP ({limit}) * FROM ({query}) AS subquery"
        
        result = db_manager.fetch_data(query)
        return result if result else []
        
    except Exception as e:
        logger.error(f"Error en consulta optimizada de stock: {e}")
        return []


def get_stock_alerts_chunked(db_manager, chunk_size=500, max_chunks=None, progress_callback=None):
    """
    Obtiene alertas de stock en chunks para evitar bloquear la UI
    
    Args:
        db_manager: Instancia de DatabaseManager
        chunk_size: Tamaño de cada chunk
        max_chunks: Máximo número de chunks (None para todos)
        progress_callback: Función callback para reportar progreso
        
    Yields:
        list: Chunks de alertas de stock
    """
    try:
        chunk_count = 0
        offset = 0
        
        while max_chunks is None or chunk_count < max_chunks:
            chunk_data = fetch_stock_alerts_optimized(
                db_manager, limit=chunk_size, offset=offset
            )
            
            if not chunk_data:
                break
            
            chunk_count += 1
            offset += chunk_size
            
            if progress_callback:
                progress_callback(chunk_count, len(chunk_data), offset)
            
            yield chunk_data
            
            # Si el chunk es menor que el tamaño esperado, probablemente sea el último
            if len(chunk_data) < chunk_size:
                break
                
    except Exception as e:
        logger.error(f"Error en carga chunked de stock: {e}")
        return


def cache_stock_data(cache_key, data, ttl_hours=1):
    """
    Guarda datos de stock en cache local con TTL
    
    Args:
        cache_key: Clave única para el cache
        data: Datos a cachear
        ttl_hours: TTL en horas
    """
    try:
        import json
        from datetime import datetime, timedelta
        
        cache_file = f"stock_cache_{cache_key}.json"
        cache_data = {
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'ttl_hours': ttl_hours
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, default=str)
            
    except Exception as e:
        logger.error(f"Error guardando cache de stock: {e}")


def load_cached_stock_data(cache_key):
    """
    Carga datos de stock desde cache si están válidos
    
    Args:
        cache_key: Clave única del cache
        
    Returns:
        list or None: Datos cacheados o None si no existen/expiraron
    """
    try:
        import json
        from datetime import datetime, timedelta
        import os
        
        cache_file = f"stock_cache_{cache_key}.json"
        
        if not os.path.exists(cache_file):
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Verificar TTL
        cached_time = datetime.fromisoformat(cache_data['timestamp'])
        ttl = timedelta(hours=cache_data.get('ttl_hours', 1))
        
        if datetime.now() - cached_time > ttl:
            # Cache expirado
            try:
                os.remove(cache_file)
            except Exception:
                pass
            return None
        
        return cache_data['data']
        
    except Exception as e:
        logger.error(f"Error cargando cache de stock: {e}")
        return None
