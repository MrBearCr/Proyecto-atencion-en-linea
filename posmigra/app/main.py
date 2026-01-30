from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path
from .db import get_auth_manager, get_db_manager, ensure_db_connected
from .routers import stock
from .dependencies import verify_token

app = FastAPI(
    title="NEXUS Posmigra API",
    description="Backend desacoplado para la migración descrita en posmigra/IMPROVEMENTS.md",
    version="0.1.0",
)

# CORS: necesario para que la SPA cargada desde `file://` o desde otro puerto
# pueda llamar a la API sin errores 405/blocked por el preflight OPTIONS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en desarrollo; en producción conviene restringir
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


class DashboardResponse(BaseModel):
    username: str
    user_id: int
    message: str
    stats: Dict[str, Any]
    widgets: List[Dict[str, Any]]


# Servir la UI web desde el servidor
UI_PATH = Path(__file__).parent.parent / "react_app" / "index.html"
STATIC_DIR = Path(__file__).parent.parent / "react_app"


@app.get("/", response_class=HTMLResponse, tags=["root"])
def read_root():
    """Sirve la UI web de login/dashboard."""
    if UI_PATH.exists():
        return FileResponse(UI_PATH)
    return HTMLResponse(
        content="""
        <html>
            <body>
                <h1>API de migración NEXUS en ejecución</h1>
                <p><a href="/docs">Documentación API (Swagger)</a></p>
                <p><a href="/redoc">Documentación API (ReDoc)</a></p>
            </body>
        </html>
        """
    )


# Servir archivos estáticos (logo, etc.)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Registrar routers
app.include_router(stock.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.options("/api/login")
async def options_login():
    """Handler explícito para preflight OPTIONS de CORS."""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.post("/api/login", response_model=LoginResponse, tags=["auth"])
def api_login(payload: LoginRequest, request: Request) -> LoginResponse:
    """
    Login real usando AuthManager de pal/core/auth.py.
    Conecta con la base de datos y valida credenciales reales.
    """
    try:
        # Asegurar conexión a BD
        if not ensure_db_connected():
            return LoginResponse(
                success=False,
                token=None,
                message="Error de conexión a la base de datos. Verifique la configuración."
            )
        
        # Obtener IP del cliente
        client_ip = request.client.host if request.client else None
        
        # Usar AuthManager real
        auth_manager = get_auth_manager()
        result = auth_manager.login(payload.username, payload.password, client_ip)
        
        if result.get("success"):
            return LoginResponse(
                success=True,
                token=result.get("token"),
                message=result.get("message", "Login exitoso")
            )
        else:
            return LoginResponse(
                success=False,
                token=None,
                message=result.get("message", "Usuario o contraseña inválidos")
            )
    except Exception as e:
        return LoginResponse(
            success=False,
            token=None,
            message=f"Error interno: {str(e)}"
        )


@app.get("/api/login")
def api_login_get():
    """Endpoint GET para debug: informa que el login requiere POST."""
    return JSONResponse(
        status_code=405,
        content={
            "error": "Method Not Allowed",
            "message": "El endpoint /api/login requiere método POST. Use POST con {username, password} en el body.",
            "allowed_methods": ["POST", "OPTIONS"],
        },
        headers={"Allow": "POST, OPTIONS"},
    )


class LogoutRequest(BaseModel):
    token: str


@app.post("/api/logout", tags=["auth"])
def api_logout(payload: LogoutRequest):
    """Cierra la sesión del usuario."""
    try:
        auth_manager = get_auth_manager()
        auth_manager.logout(payload.token)
        return {"success": True, "message": "Sesión cerrada correctamente"}
    except Exception as e:
        return {"success": False, "message": f"Error al cerrar sesión: {str(e)}"}


@app.get("/api/dashboard", response_model=DashboardResponse, tags=["dashboard"])
def api_dashboard(user_info: Dict[str, Any] = Depends(verify_token)):
    """
    Dashboard completo con datos reales de la base de datos.
    Valida el token de sesión y retorna estadísticas y widgets con información real.
    """
    try:
        # Asegurar conexión a BD
        if not ensure_db_connected():
            raise HTTPException(status_code=503, detail="Base de datos no disponible")
        
        user_id = user_info["id"]
        username = user_info["username"]
        db_manager = get_db_manager()
        
        # Obtener estadísticas reales
        stats = {}
        widgets = []
        
        # Widget 1: Total de productos en stock
        try:
            stock_rows = db_manager.fetch_data(
                "SELECT COUNT(*) FROM MA_PRODUCTOS WHERE ESTADO = 'A'"
            )
            total_productos = stock_rows[0][0] if stock_rows else 0
            widgets.append({
                "id": "total_productos",
                "title": "Productos Activos",
                "value": f"{total_productos:,}",
                "icon": "📦",
                "color": "#3b82f6"
            })
        except Exception as e:
            print(f"[DASHBOARD] Error obteniendo productos: {e}")
        
        # Widget 2: Alertas de stock bajo (usando función de stock)
        try:
            # from pal.services.stock import fetch_stock_alerts_optimized
            # alertas = fetch_stock_alerts_optimized(db_manager, limit=1000)
            
            # Re-implementación con la consulta corregida
            fixed_query = """
                SELECT TOP (1000) * FROM (
                    SELECT
                        p.C_CODIGO as codigo,
                        COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') as descripcion,
                        ISNULL(d.n_cantidad, 0) as stock,
                        CASE
                            WHEN ISNULL(d.n_cantidad, 0) <= 7 THEN 'CRÍTICA'
                            WHEN ISNULL(d.n_cantidad, 0) <= 15 THEN 'MEDIA'
                            ELSE 'LEVE'
                        END as nivel
                    FROM MA_PRODUCTOS p WITH (NOLOCK)
                    LEFT JOIN MA_DEPOPROD d ON p.C_CODIGO = d.c_codarticulo AND d.c_coddeposito = '0301'
                    WHERE p.ESTADO = 'A'
                        AND (d.n_cantidad IS NULL OR d.n_cantidad <= 50)
                        AND p.C_CODIGO IS NOT NULL
                        AND (p.cu_descripcion_corta IS NOT NULL AND LTRIM(RTRIM(p.cu_descripcion_corta)) <> '')
                ) AS subquery
                ORDER BY stock ASC, codigo ASC
            """
            alertas = db_manager.fetch_data(fixed_query)

            # Contar alertas críticas
            alertas_criticas = sum(1 for a in alertas if len(a) > 3 and str(a[3]).upper() == "CRÍTICA")
            alertas_media = sum(1 for a in alertas if len(a) > 3 and str(a[3]).upper() == "MEDIA")
            total_alertas = len(alertas)
            widgets.append({
                "id": "alertas_stock",
                "title": "Alertas de Stock",
                "value": f"{total_alertas:,}",
                "subtitle": f"{alertas_criticas} críticas, {alertas_media} medias",
                "icon": "⚠️",
                "color": "#f59e0b"
            })
        except Exception as e:
            print(f"[DASHBOARD] Error obteniendo alertas: {e}")
        
        # Widget 3: Total de clientes
        try:
            clientes_rows = db_manager.fetch_data(
                "SELECT COUNT(*) FROM MA_CLIENTES WHERE ESTADO = 'A'"
            )
            total_clientes = clientes_rows[0][0] if clientes_rows else 0
            widgets.append({
                "id": "total_clientes",
                "title": "Clientes Activos",
                "value": f"{total_clientes:,}",
                "icon": "👥",
                "color": "#10b981"
            })
        except Exception as e:
            print(f"[DASHBOARD] Error obteniendo clientes: {e}")
        
        # Widget 4: Últimos accesos (desde auditoría)
        try:
            accesos_rows = db_manager.fetch_data(
                """
                SELECT TOP 5 u.username, a.fecha, a.accion
                FROM pal_auditoria_accesos a
                LEFT JOIN pal_usuarios u ON a.usuario_id = u.id
                WHERE a.exitoso = 1
                ORDER BY a.fecha DESC
                """
            )
            ultimos_accesos = [
                {
                    "usuario": row[0] or "N/A",
                    "fecha": str(row[1]) if row[1] else "N/A",
                    "accion": row[2] or "N/A"
                }
                for row in accesos_rows
            ]
            widgets.append({
                "id": "ultimos_accesos",
                "title": "Últimos Accesos",
                "value": f"{len(ultimos_accesos)}",
                "icon": "🔐",
                "color": "#8b5cf6",
                "data": ultimos_accesos
            })
        except Exception as e:
            print(f"[DASHBOARD] Error obteniendo accesos: {e}")
        
        # Estadísticas generales
        stats = {
            "total_productos": widgets[0]["value"] if len(widgets) > 0 else "0",
            "alertas_stock": widgets[1]["value"] if len(widgets) > 1 else "0",
            "total_clientes": widgets[2]["value"] if len(widgets) > 2 else "0",
        }
        
        return DashboardResponse(
            username=username,
            user_id=user_id,
            message=f"Bienvenido, {username}",
            stats=stats,
            widgets=widgets
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar dashboard: {str(e)}")


# Nota: normalmente se levanta con (desde posmigra/):
#   poetry run uvicorn app.main:app --reload --port 8000


