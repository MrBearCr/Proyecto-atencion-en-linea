"""
Utilidades compartidas de filtrado para módulos PAL (stock, tra, mbrp).
Unifican el comportamiento de filtros jerárquicos para evitar duplicación y
mantener consistencia entre módulos.
"""
from typing import Callable, Iterable, Dict, Any, Optional, List


def _normalize(value: Any) -> str:
    return str(value) if value is not None else ""


def match_hierarchy_from_map(
    codigo: Any,
    jerarquia_map: Dict[str, tuple],
    dept_code: Optional[Any] = None,
    group_code: Optional[Any] = None,
    sub_code: Optional[Any] = None,
    *,
    missing_strategy: str = "exclude",
) -> bool:
    """
    Determina si un código coincide con filtros jerárquicos usando un mapa de jerarquía.

    missing_strategy:
      - "exclude": si no hay jerarquía para el producto y hay filtros activos, se EXCLUYE
      - "include": si no hay jerarquía para el producto y hay filtros activos, se INCLUYE
    """
    # Si no hay filtros activos, no restringir
    if not any([dept_code, group_code, sub_code]):
        return True

    jerarquia = jerarquia_map.get(str(codigo)) if jerarquia_map else None
    if not jerarquia:
        return missing_strategy == "include"

    try:
        dep, grp, sub = jerarquia
        dep = _normalize(dep)
        grp = _normalize(grp)
        sub = _normalize(sub)
        dept_code = _normalize(dept_code)
        group_code = _normalize(group_code)
        sub_code = _normalize(sub_code)

        return (
            (not dept_code or dep == dept_code)
            and (not group_code or grp == group_code)
            and (not sub_code or sub == sub_code)
        )
    except Exception:
        # En caso de estructura inesperada, aplicar estrategia de faltantes
        return missing_strategy == "include"


def match_hierarchy_from_record(
    record: Any,
    dept_code: Optional[Any] = None,
    group_code: Optional[Any] = None,
    sub_code: Optional[Any] = None,
    *,
    get_dept: Callable[[Any], Any],
    get_group: Callable[[Any], Any],
    get_sub: Callable[[Any], Any],
    missing_strategy: str = "exclude",
) -> bool:
    """
    Determina si un registro coincide con filtros jerárquicos leyendo los campos
    desde el propio registro (por ejemplo, índices 2,3,4 en TRA/MBRP).
    """
    # Sin filtros activos, no restringir
    if not any([dept_code, group_code, sub_code]):
        return True

    try:
        dep = _normalize(get_dept(record))
        grp = _normalize(get_group(record))
        sub = _normalize(get_sub(record))
        dept_code = _normalize(dept_code)
        group_code = _normalize(group_code)
        sub_code = _normalize(sub_code)

        # Si faltan campos en el registro y hay filtros activos
        if dep == grp == sub == "":
            return missing_strategy == "include"

        return (
            (not dept_code or dep == dept_code)
            and (not group_code or grp == group_code)
            and (not sub_code or sub == sub_code)
        )
    except Exception:
        # En caso de excepciones al leer campos, aplicar estrategia
        return missing_strategy == "include"


esstrategias_validas = {"exclude", "include"}


def filter_by_hierarchy(
    records: Iterable[Any],
    dept_code: Optional[Any] = None,
    group_code: Optional[Any] = None,
    sub_code: Optional[Any] = None,
    *,
    get_code: Optional[Callable[[Any], Any]] = None,
    jerarquia_map: Optional[Dict[str, tuple]] = None,
    get_dept: Optional[Callable[[Any], Any]] = None,
    get_group: Optional[Callable[[Any], Any]] = None,
    get_sub: Optional[Callable[[Any], Any]] = None,
    missing_strategy: str = "exclude",
) -> List[Any]:
    """
    Aplica un filtro jerárquico unificado sobre una colección de registros.

    Dos modos de uso:
      1) Con jerarquía externa (mapa codigo->(dep,grp,sub)) pasando get_code y jerarquia_map
      2) Leyendo jerarquía del propio registro pasando get_dept/get_group/get_sub

    missing_strategy: "exclude" (por defecto) o "include"
    """
    if missing_strategy not in esstrategias_validas:
        missing_strategy = "exclude"

    # Sin filtros activos, devolver tal cual (evitar trabajo extra)
    if not any([dept_code, group_code, sub_code]):
        return list(records)

    result = []
    if jerarquia_map is not None and get_code is not None:
        for r in records:
            codigo = get_code(r)
            if match_hierarchy_from_map(
                codigo,
                jerarquia_map,
                dept_code,
                group_code,
                sub_code,
                missing_strategy=missing_strategy,
            ):
                result.append(r)
        return result

    if get_dept is not None and get_group is not None and get_sub is not None:
        for r in records:
            if match_hierarchy_from_record(
                r,
                dept_code,
                group_code,
                sub_code,
                get_dept=get_dept,
                get_group=get_group,
                get_sub=get_sub,
                missing_strategy=missing_strategy,
            ):
                result.append(r)
        return result

    # Si no se proporcionan estrategias válidas, devolver registros originales
    return list(records)