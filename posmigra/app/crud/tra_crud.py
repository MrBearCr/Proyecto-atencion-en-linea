from sqlalchemy.orm import Session
from sqlalchemy import text, func, case, and_, or_
from typing import List, Optional
from datetime import date
from app.models import MaProductosDB, MaDepoProdDB, TrInventarioDB, ProductoVentasResponse
import logging

logger = logging.getLogger(__name__)

def get_tra_sales_data(
    db: Session,
    start_date: date,
    end_date: date,
    dept_code: Optional[str] = None,
    group_code: Optional[str] = None,
    sub_code: Optional[str] = None,
    search_text: Optional[str] = None,
    filter_rotacion: str = "TODAS",
    sede_codigo: str = "00", # Default to Global/ICH
    page: int = 1,
    page_size: int = 20
) -> List[ProductoVentasResponse]:
    """
    Fetches TRA sales data using complex SQL logic migrated from legacy app.
    Supports global (ICH) and specific branch views.
    """
    try:
        # Determine if global query or specific branch
        is_global = sede_codigo in (None, '%', '00', 'ICH', 'ALL')
        
        # Calculate pagination offsets
        offset = (page - 1) * page_size
        
        # Format dates
        f_inicio = start_date.strftime("%Y%m%d")
        f_fin = end_date.strftime("%Y%m%d")
        
        # Base SQL Construction
        # We use strict raw SQL to maintain performance characteristics of the legacy system (NOLOCK, CTEs)
        
        sql_query = ""
        params = {
            "fecha_inicio": f_inicio,
            "fecha_fin": f_fin,
            "offset": offset,
            "limit": page_size
        }

        if is_global:
            # Global Query (Aggregated)
            sql_query = """
                WITH VentasAgregadas AS (
                    SELECT 
                        RTRIM(LTRIM(i.c_Codarticulo)) AS codigo,
                        SUM(CASE 
                            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                            ELSE 0 
                        END) AS neto
                    FROM TR_INVENTARIO i WITH (NOLOCK)
                    WHERE i.f_fecha BETWEEN CONVERT(DATE, :fecha_inicio, 112) AND CONVERT(DATE, :fecha_fin, 112)
                        AND i.c_Concepto IN ('VEN', 'DEV')
                    GROUP BY i.c_Codarticulo
                    HAVING SUM(CASE 
                        WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                        WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                        ELSE 0 
                    END) > 0
                )
                SELECT 
                    RTRIM(LTRIM(v.codigo)) AS codigo,
                    COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                    COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                    COALESCE(p.C_GRUPO, '') AS grupo,
                    COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                    v.neto,
                    COALESCE(p.n_precio1, 0) AS precio,
                    COALESCE(p.n_impuesto1, 0) AS impuesto1,
                    COALESCE(p.n_costoact, 0) AS costo,
                    -- Mock rotation and rep% for now, or calculate if data allows
                    'N/A' as rotacion,
                    0.0 as porcentaje_representacion
                FROM VentasAgregadas v
                LEFT JOIN MA_PRODUCTOS p WITH (NOLOCK) ON v.codigo = p.C_CODIGO
                ORDER BY v.neto DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """
        else:
            # Sede Specific Query
            params["sede"] = sede_codigo
            sql_query = """
                WITH VentasAgregadas AS (
                    SELECT 
                        RTRIM(LTRIM(i.c_Codarticulo)) AS codigo,
                        SUM(CASE 
                            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                            ELSE 0 
                        END) AS neto
                    FROM TR_INVENTARIO i WITH (NOLOCK)
                    WHERE i.f_fecha BETWEEN CONVERT(DATE, :fecha_inicio, 112) AND CONVERT(DATE, :fecha_fin, 112)
                        AND i.c_Concepto IN ('VEN', 'DEV')
                        AND i.c_Deposito = :sede
                    GROUP BY i.c_Codarticulo
                    HAVING SUM(CASE 
                        WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                        WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                        ELSE 0 
                    END) > 0
                )
                SELECT 
                    RTRIM(LTRIM(v.codigo)) AS codigo,
                    COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                    COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                    COALESCE(p.C_GRUPO, '') AS grupo,
                    COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                    v.neto,
                    COALESCE(p.n_precio1, 0) AS precio,
                    COALESCE(p.n_impuesto1, 0) AS impuesto1,
                    COALESCE(p.n_costoact, 0) AS costo,
                    'N/A' as rotacion,
                    0.0 as porcentaje_representacion
                FROM VentasAgregadas v
                LEFT JOIN MA_PRODUCTOS p WITH (NOLOCK) ON v.codigo = p.C_CODIGO
                ORDER BY v.neto DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """
            
        # Execute Query
        result = db.execute(text(sql_query), params).fetchall()
        
        # Map to Pydantic Models
        mapped_results = []
        for row in result:
            mapped_results.append(ProductoVentasResponse(
                codigo=row.codigo,
                descripcion=row.descripcion,
                departamento=row.departamento,
                grupo=row.grupo,
                subgrupo=row.subgrupo,
                ventas_netas=row.neto,
                rotacion=row.rotacion,
                porcentaje_representacion=row.porcentaje_representacion
            ))
            
        return mapped_results

    except Exception as e:
        logger.error(f"Error fetching TRA/Sales data: {e}")
        return []
