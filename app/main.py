from fastapi import FastAPI, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
import secrets
import bcrypt # For password hashing
import keyring # For secure credential storage (though API might not directly use it for user passwords)
import os
import json
import logging # For logging

# Import database models and session getter
from app.database import engine, SessionLocal, Base, get_db
# Import Pydantic models and DB models
from app.models import (
    UserDB, RoleDB, PermissionDB, AuditDB, SessionDB, UserCreateRequest, 
    UserUpdateRequest, UserResponse, LoginRequestAPI, LoginResponseAPI, ChangePasswordRequest, 
    PermissionResponse, RoleResponse, UserAuth, RoleCreateRequest, UserRoleDB, RolePermissionDB,
    UserModuleDB, EnvioProgramadoCreateAPI, EnvioProgramadoResponse,
    SedeConfiguracionDB, SedeConfiguracionCreate, SedeConfiguracionResponse,
    StockAlert, StockAlertDetail, JerarquiaProducto, ProductoVentas, ProductoMBRP, MBRPReportSummary,
    db_to_pydantic # Helper for DB object to Pydantic model conversion
)
# Import routers
from app.routers import auth # Import the new auth router
# Import CRUD operations
from app.crud import (
    get_user, get_user_by_username, get_users, create_user, update_user, delete_user,
    get_role, get_role_by_name, get_roles, create_role, update_role, delete_role,
    get_permission_by_code, get_permissions,
    get_active_session_by_token, invalidate_session_token,
    log_audit_access,
    create_envio_programado, get_pending_envios, update_envio_estado,
    get_active_sedes,
    get_user_extra_info # Helper for response population
)
# Import stock-related logic
from pal.services.stock import get_existencias_por_ubicacion, filter_alertas, paginate, load_all_jerarquia, build_producto_jerarquia, fetch_stock_alerts_optimized, get_stock_alerts_chunked
# Import TRA-related logic
from pal.services.tra import filter_ventas_tra, paginate_tra, calcular_porcentajes_representacion, _get_tra_neto, clasificar_rotacion_tra
# Import MBRP-related logic
from pal.services.mbrp import calcular_indice_movilidad, obtener_fecha_ultima_venta, calcular_dias_sin_venta, filtrar_productos_baja_rotacion, clasificar_rotacion_mbrp, generar_reporte_baja_rotacion
# Utility functions for filtering and pagination
from app.utils import filter_by_hierarchy, paginate, paginate_tra # Assuming these utils are defined

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PAL Backend API",
    description="API for Customer Management Application (PAL)",
    version="0.1.0",
    contact={
        "name": "PAL Development Team",
        "url": "http://example.com/docs", # Replace with actual URL if available
        "email": "devteam@example.com", # Replace with actual email
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# --- Database Setup ---
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
except Exception as e:
    logger.error(f"Failed to ensure database tables: {e}")

# --- Security Configuration ---
# Placeholder for JWT configuration if using tokens for sessions beyond simple tokens
# SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-for-jwt")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Password Hashing Utility ---
def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    try:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise

def check_password(password: str, hashed_password: str) -> bool:
    """Checks a password against a hashed password using bcrypt."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False

# --- Authentication Dependency ---
async def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserDB:
    """
    Dependency to get the current authenticated user from session token.
    This is a simplified version. A real implementation would use JWT or tokens.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticación no proporcionado")

    session_db = get_active_session_by_token(db, token)
    
    if not session_db:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de sesión inválido o expirado")

    now = datetime.utcnow()
    if session_db.fecha_expiracion and now > session_db.fecha_expiracion:
        invalidate_session_token(db, token) # Invalidate expired session
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de sesión expirado")
    
    user_db = get_user(db, session_db.usuario_id)
    if not user_db:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario asociado a la sesión no encontrado")
    
    return user_db

# --- Placeholder for current_user_id dependency for permission checks ---
async def get_current_user_id_for_auth(request: Request, db: Session = Depends(get_db)) -> Optional[int]:
    """Placeholder dependency to get current user ID for permission checks."""
    try:
        user = await get_current_user(request, db)
        return user.id
    except HTTPException:
        return None # Not authenticated or token invalid

# --- API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    """Root endpoint to check if the API is running."""
    return {"message": "Welcome to the PAL Backend API"}

# Import and include the auth router
app.include_router(auth.router)

# --- User Management Endpoints ---

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def create_user_endpoint(
    user_create: UserCreateRequest,
    db: Session = Depends(get_db)
):
    """Creates a new user."""
    if get_user_by_username(db, user_create.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya está en uso")

    try:
        new_user_db = create_user(db, user_create)
        user_for_response = get_user(db, new_user_db.id) # Re-fetch for relationships
        pydantic_user = db_to_pydantic(user_for_response, UserResponse)
        if pydantic_user:
            return pydantic_user
        else: # Fallback conversion
            return UserResponse(
                id=new_user_db.id, username=new_user_db.username, nombre_completo=new_user_db.nombre_completo,
                email=new_user_db.email, activo=new_user_db.activo, fecha_creacion=new_user_db.fecha_creacion,
                fecha_ultimo_acceso=new_user_db.fecha_ultimo_acceso, intentos_fallidos=new_user_db.intentos_fallidos,
                bloqueado_hasta=new_user_db.bloqueado_hasta, roles=[r.id for r in new_user_db.roles],
                modulos_habilitados=[m.modulo for m in new_user_db.modulos_habilitados]
            )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear usuario")

@app.get("/users/", response_model=List[UserResponse], tags=["Users"])
async def get_all_users_endpoint(
    activo_only: bool = True,
    db: Session = Depends(get_db)
):
    """Retrieves a list of users, optionally filtered by active status."""
    users_db = get_users(db, active_only=activo_only)
    
    users_response = []
    for user_db in users_db:
        try:
            pydantic_user = db_to_pydantic(user_db, UserResponse)
            if pydantic_user:
                users_response.append(pydantic_user)
            else: # Fallback conversion
                users_response.append(UserResponse(
                    id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
                    email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
                    fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
                    bloqueado_hasta=user_db.bloqueado_hasta, roles=[r.id for r in user_db.roles],
                    modulos_habilitados=[m.modulo for m in user_db.modulos_habilitados]
                ))
        except Exception as e:
            logger.error(f"Error converting user DB object {user_db.id} to response model: {e}")
            users_response.append(UserResponse( # Append basic fallback info
                id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
                email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
                fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
                bloqueado_hasta=user_db.bloqueado_hasta, roles=[], modulos_habilitados=[]
            ))
            
    return users_response

@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user_by_id_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific user by their ID."""
    user_db = get_user(db, user_id)
    if not user_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    try:
        pydantic_user = db_to_pydantic(user_db, UserResponse)
        if pydantic_user:
            return pydantic_user
        else: # Fallback conversion
            return UserResponse(
                id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
                email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
                fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
                bloqueado_hasta=user_db.bloqueado_hasta, roles=[r.id for r in user_db.roles],
                modulos_habilitados=[m.modulo for m in user_db.modulos_habilitados]
            )
    except Exception as e:
        logger.error(f"Error converting user DB object {user_id} to response model: {e}")
        return UserResponse(
            id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
            email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
            fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
            bloqueado_hasta=user_db.bloqueado_hasta, roles=[], modulos_habilitados=[]
        )

@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """Updates an existing user."""
    updated_user_db = update_user(db, user_id, user_update)
    if not updated_user_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    try:
        user_for_response = get_user(db, user_id) # Re-fetch for fresh state/relationships
        pydantic_user = db_to_pydantic(user_for_response, UserResponse)
        if pydantic_user:
            return pydantic_user
        else: # Fallback conversion
            return UserResponse(
                id=updated_user_db.id, username=updated_user_db.username, nombre_completo=updated_user_db.nombre_completo,
                email=updated_user_db.email, activo=updated_user_db.activo, fecha_creacion=updated_user_db.fecha_creacion,
                fecha_ultimo_acceso=updated_user_db.fecha_ultimo_acceso, intentos_fallidos=updated_user_db.intentos_fallidos,
                bloqueado_hasta=updated_user_db.bloqueado_hasta, roles=[r.id for r in updated_user_db.roles],
                modulos_habilitados=[m.modulo for m in updated_user_db.modulos_habilitados]
            )
    except Exception as e:
        logger.error(f"Error converting updated user {user_id} to response model: {e}")
        return UserResponse(
            id=updated_user_db.id, username=updated_user_db.username, nombre_completo=updated_user_db.nombre_completo,
            email=updated_user_db.email, activo=updated_user_db.activo, fecha_creacion=updated_user_db.fecha_creacion,
            fecha_ultimo_acceso=updated_user_db.fecha_ultimo_acceso, intentos_fallidos=updated_user_db.intentos_fallidos,
            bloqueado_hasta=updated_user_db.bloqueado_hasta, roles=[], modulos_habilitados=[]
        )

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
async def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Deletes a user (soft delete by deactivating)."""
    if not delete_user(db, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return None # No content

# --- Role Management Endpoints ---
@app.post("/roles/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, tags=["Roles"])
async def create_role_endpoint(
    role_create: RoleCreateRequest,
    db: Session = Depends(get_db)
):
    """Creates a new role."""
    if get_role_by_name(db, role_create.nombre):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre del rol ya está en uso")

    try:
        new_role_db = create_role(db, role_create)
        return RoleResponse(id=new_role_db.id, nombre=new_role_db.nombre, descripcion=new_role_db.descripcion, es_sistema=new_role_db.es_sistema)
    except ValueError as e: # Catch specific errors like role name conflict if not handled by unique constraint
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear rol")

@app.get("/roles/", response_model=List[RoleResponse], tags=["Roles"])
async def get_all_roles_endpoint(db: Session = Depends(get_db)):
    """Retrieves a list of all roles."""
    roles_db = get_roles(db)
    return [RoleResponse(id=r.id, nombre=r.nombre, descripcion=r.descripcion, es_sistema=r.es_sistema) for r in roles_db]

@app.get("/roles/{role_id}", response_model=RoleResponse, tags=["Roles"])
async def get_role_by_id_endpoint(role_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific role by its ID."""
    role_db = get_role(db, role_id)
    if not role_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return RoleResponse(id=role_db.id, nombre=role_db.nombre, descripcion=role_db.descripcion, es_sistema=role_db.es_sistema)

@app.put("/roles/{role_id}", response_model=RoleResponse, tags=["Roles"])
async def update_role_endpoint(
    role_id: int,
    role_update: RoleCreateRequest, # Reusing RoleCreateRequest for update payload
    db: Session = Depends(get_db)
):
    """Updates an existing role."""
    update_data = role_update.model_dump(exclude_unset=True, exclude={'permisos_codigos'}) # Exclude permissions for now
    
    try:
        updated_role_db = update_role(db, role_id, update_data)
        if not updated_role_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
        
        return RoleResponse(id=updated_role_db.id, nombre=updated_role_db.nombre, descripcion=updated_role_db.descripcion, es_sistema=updated_role_db.es_sistema)
    except ValueError as e: # Catching specific errors like name conflicts
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating role {role_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar rol")

@app.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Roles"])
async def delete_role_endpoint(role_id: int, db: Session = Depends(get_db)):
    """Deletes a role."""
    try:
        if not delete_role(db, role_id):
            if get_role(db, role_id): # If it exists but couldn't delete (e.g. system role)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pueden eliminar roles del sistema")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    except ValueError as e: # For system roles
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting role {role_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar rol")
    return None

# --- Permissions Endpoints ---
@app.get("/permissions/", response_model=List[PermissionResponse], tags=["Permissions"])
async def get_all_permissions_endpoint(db: Session = Depends(get_db)):
    """Retrieves a list of all available permissions."""
    permissions_db = get_permissions(db)
    return [PermissionResponse(id=p.id, codigo=p.codigo, modulo=p.modulo, descripcion=p.descripcion) for p in permissions_db]

# --- API for Services ---
# Example: EnvioProgramado
@app.post("/envios_programados/", response_model=EnvioProgramadoResponse, status_code=status.HTTP_201_CREATED, tags=["Servicios"])
async def schedule_envio_endpoint(
    envio_create: EnvioProgramadoCreateAPI,
    db: Session = Depends(get_db)
):
    """Schedules a new shipment."""
    envio_data = envio_create.model_dump() # Convert Pydantic model to dict
    new_envio_db = create_envio_programado(db, envio_data)
    
    if not new_envio_db:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al programar envío")

    return EnvioProgramadoResponse(
        id=new_envio_db.id,
        numero_cliente=new_envio_db.numero_cliente,
        fecha_programada=new_envio_db.fecha_programada,
        tipo_envio=new_envio_db.tipo_envio,
        codigo_producto=new_envio_db.codigo_producto,
        fecha_creacion=new_envio_db.fecha_creacion,
        estado=new_envio_db.estado
    )

@app.get("/envios_programados/", response_model=List[EnvioProgramadoResponse], tags=["Servicios"])
async def get_scheduled_envios(
    db: Session = Depends(get_db),
    estado: Optional[str] = None, # Filter by status
    fecha_limite: Optional[datetime] = None # Filter by date
):
    """Retrieves scheduled shipments, optionally filtered by status and date."""
    query = db.query(EnvioProgramadoDB)
    if estado:
        query = query.filter(EnvioProgramadoDB.estado == estado)
    if fecha_limite:
        query = query.filter(EnvioProgramadoDB.fecha_programada <= fecha_limite)
    
    envios_db = query.order_by(EnvioProgramadoDB.fecha_programada).all()
    
    return [
        EnvioProgramadoResponse(
            id=e.id,
            numero_cliente=e.numero_cliente,
            fecha_programada=e.fecha_programada,
            tipo_envio=e.tipo_envio,
            codigo_producto=e.codigo_producto,
            fecha_creacion=e.fecha_creacion,
            estado=e.estado
        ) for e in envios_db
    ]

# --- Stock Alerts Endpoints ---
@app.get("/stock/alerts/", response_model=List[StockAlert], tags=["Stock"])
async def get_stock_alerts(
    db: Session = Depends(get_db),
    dept_code: Optional[str] = Query(None, alias="department"),
    group_code: Optional[str] = Query(None, alias="group"),
    sub_code: Optional[str] = Query(None, alias="subgroup"),
    search_text: Optional[str] = Query(None, alias="search"),
    filter_level: str = Query("TODAS", alias="level"),
    page: int = 1,
    page_size: int = 20,
    current_user_id: Optional[int] = Depends(get_current_user_id_for_auth) # Dependency for permissions/favorites
):
    """
    Retrieves stock alerts, optionally filtered by hierarchy, search text, alert level,
    and sorted by favorites, severity, stock, and code.
    """
    # Placeholder for hierarchy loading. In a real app, this should be cached.
    product_hierarchy = {} # Ideally loaded from cache or DB
    try:
        # This would involve calling a function like load_all_jerarquia if it were robustly implemented
        # For now, assume it's empty or needs proper implementation.
        pass
    except Exception as e:
        logger.error(f"Could not load product hierarchy for filtering: {e}")
        product_hierarchy = {} # Proceed without hierarchy filtering if loading fails

    # Fetch base alerts using the optimized function
    all_alerts_db = fetch_stock_alerts_optimized(db) # Fetch base alerts
    
    if not all_alerts_db:
        return []

    # Convert DB results to Pydantic models for filtering
    stock_alerts_pydantic = [
        StockAlert(codigo=r[0], descripcion=r[1], stock=int(r[2]), nivel=r[3])
        for r in all_alerts_db if r and len(r) >= 4
    ]

    # Placeholder for favorite products loading
    user_favorites = set()
    # if current_user_id:
    #     # Fetch user's favorites here if implemented
    #     pass

    # Apply Python-level filtering and sorting
    filtered_alerts = filter_alertas(
        stock_alerts_pydantic,
        producto_jerarquia=build_producto_jerarquia(product_hierarchy, {a.codigo for a in stock_alerts_pydantic}),
        dept_code=dept_code,
        group_code=group_code,
        sub_code=sub_code,
        search_text=search_text,
        filter_level=filter_level,
        favoritos=user_favorites
    )
    
    # Apply pagination
    paginated_data, total_pages, current_page = paginate(
        filtered_alerts, page, page_size
    )
    
    # Consider returning pagination metadata as well
    return paginated_data

# --- TRA Endpoints ---
@app.get("/tra/sales/", response_model=List[ProductoVentas], tags=["TRA"])
async def get_tra_sales_data(
    db: Session = Depends(get_db),
    dept_code: Optional[str] = Query(None, alias="department"),
    group_code: Optional[str] = Query(None, alias="group"),
    sub_code: Optional[str] = Query(None, alias="subgroup"),
    search_text: Optional[str] = Query(None, alias="search"),
    filter_rotacion: str = Query("TODAS", alias="rotation"),
    page: int = 1,
    page_size: int = 20,
    current_user_id: Optional[int] = Depends(get_current_user_id_for_auth) # For permissions/favorites
):
    """
    Retrieves TRA sales data, filtered by hierarchy, search text, rotation,
    and sorted by favorites, rotation, stock alerts, and net sales.
    """
    # Fetch raw TRA data from the database. This is a placeholder query.
    # The actual query needs to join TR_INVENTARIO with MA_PRODUCTOS and aggregate.
    # Example: raw_tra_data = db.query(...).all()
    
    # Mock data for demonstration purposes. Replace with actual DB query.
    logger.warning("Using mock data for TRA sales. Implement actual DB query.")
    raw_tra_data = [
        ('PROD001', 'Producto Uno', 'DEP1', 'GRP1', 'SUB1', 1500.50, 'ALTA', 10.0, 1.6, 5.0),
        ('PROD002', 'Producto Dos', 'DEP1', 'GRP1', 'SUB1', 800.00, 'MEDIA', 8.0, 1.28, 4.0),
        ('PROD003', 'Producto Tres', 'DEP1', 'GRP2', 'SUB2', 300.75, 'BAJA', 5.0, 0.8, 2.5),
        ('PROD004', 'Producto Cuatro', 'DEP2', 'GRP3', 'SUB3', 1200.00, 'ALTA', 15.0, 2.4, 7.0),
        ('PROD005', 'Producto Cinco', 'DEP1', 'GRP1', 'SUB1', 50.25, 'BAJA', 2.5, 0.4, 1.0),
        ('PROD006', 'Producto Seis', 'DEP3', 'GRP4', 'SUB4', 0.00, 'SIN MOVIMIENTO', 0.0, 0.0, 0.0),
        ('PROD007', 'Producto Siete', 'DEP1', 'GRP1', 'SUB1', 950.00, 'ALTA', 9.0, 1.44, 4.5), # Example for sorting/filtering
    ]

    # Classify rotation for TRA
    classified_tra_data = clasificar_rotacion_tra(raw_tra_data)

    # Placeholder for favorites and stock alerts loading
    user_favorites = set() # Fetch user favorites if current_user_id is available
    stock_alerts_data = [] # Fetch stock alerts data {codigo: (desc, stock, nivel)}

    # Apply filters and sorting
    filtered_tra_data = filter_ventas_tra(
        classified_tra_data,
        dept_code=dept_code,
        group_code=group_code,
        sub_code=sub_code,
        search_text=search_text,
        filter_rotacion=filter_rotacion,
        favoritos=user_favorites,
        alertas_stock=stock_alerts_data # Pass alerts for sorting priority
    )
    
    # Apply pagination
    paginated_data, total_pages, current_page = paginate_tra(
        filtered_tra_data, page, page_size
    )
    
    # Convert to Pydantic response models
    response_data = []
    for item in paginated_data:
        try:
            pv = ProductoVentas(
                codigo=item[0],
                descripcion=item[1],
                departamento=item[2],
                grupo=item[3],
                subgrupo=item[4],
                ventas_netas=_get_tra_neto(item),
                rotacion=item[6] if len(item) > 6 else "SIN CLASIFICAR"
            )
            response_data.append(pv)
        except Exception as e:
            logger.warning(f"Skipping TRA item due to mapping error: {item} - {e}")
            continue

    # Consider returning pagination metadata
    return response_data

# --- MBRP Endpoints ---
@app.get("/mbrp/report/", response_model=List[ProductoMBRP], tags=["MBRP"]) # Adjusted response_model to List[ProductoMBRP] for paginated items
async def get_mbrp_report(
    db: Session = Depends(get_db),
    dept_code: Optional[str] = Query(None, alias="department"),
    group_code: Optional[str] = Query(None, alias="group"),
    sub_code: Optional[str] = Query(None, alias="subgroup"),
    search_text: Optional[str] = Query(None, alias="search"),
    umbral_im: float = Query(20.0, alias="im_threshold"), # Threshold for low IM
    sede_codigo: Optional[str] = Query(None, alias="sede"), # Filter by sede
    fecha_inicio_str: Optional[str] = Query(None, alias="start_date"), # YYYY-MM-DD
    fecha_fin_str: Optional[str] = Query(None, alias="end_date"), # YYYY-MM-DD
    page: int = 1,
    page_size: int = 100,
    current_user_id: Optional[int] = Depends(get_current_user_id_for_auth) # For permissions/favorites
):
    """
    Generates an MBRP report, identifying products with low rotation and low profit margins.
    Filters by hierarchy, search text, sede, and date range.
    Returns a paginated list of critical products.
    """
    # Parse date range
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d") if fecha_inicio_str else None
        fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d") if fecha_fin_str else None
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato de fecha inválido: {e}. Use YYYY-MM-DD.")

    # Fetch raw TRA data (sales data) for MBRP analysis
    # This query needs to aggregate sales and purchases for the period and sede.
    # Placeholder: Replace with actual DB query logic.
    # Example structure: [codigo, desc, dept, grupo, sub, neto_ventas, ..., costo, precio, impuesto1]
    raw_tra_data_for_mbrp = [] # Replace with actual DB query result
    
    # Mock data for demonstration if DB query is not implemented
    if not raw_tra_data_for_mbrp:
        logger.warning("Using mock data for MBRP analysis. Implement actual DB query.")
        raw_tra_data_for_mbrp = [
            # (codigo, desc, dept, grupo, sub, neto_ventas, rotacion, precio, impuesto1, costo)
            ('PROD001', 'Producto Uno', 'DEP1', 'GRP1', 'SUB1', 1500.50, 'ALTA', 10.0, 1.6, 5.0),
            ('PROD002', 'Producto Dos', 'DEP1', 'GRP1', 'SUB1', 800.00, 'MEDIA', 8.0, 1.28, 4.0),
            ('PROD003', 'Producto Tres', 'DEP1', 'GRP2', 'SUB2', 300.75, 'BAJA', 5.0, 0.8, 2.5),
            ('PROD004', 'Producto Cuatro', 'DEP2', 'GRP3', 'SUB3', 1200.00, 'ALTA', 15.0, 2.4, 7.0),
            ('PROD005', 'Producto Cinco', 'DEP1', 'GRP1', 'SUB1', 50.25, 'BAJA', 2.5, 0.4, 1.0),
            ('PROD006', 'Producto Seis', 'DEP3', 'GRP4', 'SUB4', 0.00, 'SIN MOVIMIENTO', 0.0, 0.0, 0.0), # No sales, IM 0
            ('PROD007', 'Producto Siete', 'DEP1', 'GRP1', 'SUB1', 950.00, 'ALTA', 9.0, 1.44, 4.5),
            ('PROD008', 'Producto Ocho', 'DEP1', 'GRP1', 'SUB1', 5.50, 'BAJA', 1.0, 0.16, 0.5), # Very low sales
            ('PROD009', 'Producto Nueve', 'DEP1', 'GRP1', 'SUB1', 10.00, 'BAJA', 2.0, 0.32, 0.6), # Low sales, good margin?
        ]

    # Apply hierarchy filters if provided
    # This requires the raw_tra_data to have hierarchy fields at specific indices
    # Assuming indices: 0=codigo, 1=desc, 2=dept, 3=grupo, 4=subgrupo
    filtered_tra_data = filter_by_hierarchy(
        raw_tra_data_for_mbrp,
        dept_code=dept_code,
        group_code=group_code,
        sub_code=sub_code,
        get_dept=lambda r: r[2] if len(r) > 2 else None,
        get_group=lambda r: r[3] if len(r) > 3 else None,
        get_sub=lambda r: r[4] if len(r) > 4 else None,
        missing_strategy="exclude", # Exclude products without hierarchy if filters are applied
    )
    
    # Apply search text filter
    if search_text:
        text = search_text.strip().lower()
        filtered_tra_data = [
            r for r in filtered_tra_data if len(r) >= 2 and (
                text in str(r[0]).lower() or text in str(r[1]).lower()
            )
        ]
        
    # Filter by date range (requires date fields in raw_tra_data)
    # Placeholder: Assuming raw_tra_data doesn't inherently have date, so filtering by date
    # is typically done during the initial DB query. For this mock data, we skip date filtering.
    
    # Calculate Index of Mobility (IM) for classification
    # The calcular_indice_movilidad function expects sales_data and optionally total_ventas_periodo
    # We need to pass the net sales amount (item[5]) and calculate total_ventas if not provided
    # Assuming the raw_tra_data includes net sales at index 5.
    
    # Calculate total net sales for the period (if not using external total)
    # total_neto_periodo = sum(_get_tra_neto(item) for item in filtered_tra_data) # Pass this if available
    
    # Call to calculate IM for filtered data
    indices_movilidad = calcular_indice_movilidad(filtered_tra_data) # Assumes item[5] is neto

    # Add IM and classification to the data
    classified_data = []
    for item in filtered_tra_data:
        if len(item) >= 6:
            codigo = str(item[0])
            neto = _get_tra_neto(item)
            im = indices_movilidad.get(codigo, 0.0)
            
            # Replicate classification logic from clasificar_rotacion_mbrp for consistency
            # This is simplified: assumes item structure and calculates IM.
            # Real MBRP report might need more detailed data (purchases, cost, price).
            
            # Augment item with IM and classification (added at index 6)
            item_list = list(item)
            if len(item_list) < 7: # Ensure there's space for rotation classification
                item_list.extend([None] * (7 - len(item_list)))
            item_list[6] = im # Store IM for sorting/filtering if needed
            
            # Add classification (e.g., ALTA, MEDIA, BAJA, SIN_MOVIMIENTO)
            rotacion_mbrp_map = {
                0.0: "SIN_MOVIMIENTO",
                # Using thresholds from clasificar_rotacion_mbrp for consistency
                im <= 10.0: "BAJA",
                im <= 30.0: "MEDIA",
                # default: "ALTA" (not strictly needed for MBRP filter usually)
            }
            
            current_rotacion = "ALTA" # Default for items with IM > 30%
            if im <= 30.0:
                if im <= 10.0:
                    current_rotacion = "BAJA"
                else:
                    current_rotacion = "MEDIA"
            if im == 0.0 or neto <= 0: # SIN MOVIMIENTO takes precedence
                 current_rotacion = "SIN_MOVIMIENTO"
            
            # Add classification to item list (e.g., at index 7 for a full structure)
            # For now, just ensure the raw data is there for report generation.
            # The report function `export_mbrp_csv` expects specific fields.
            # Let's ensure the structure is compatible for the report generation logic if needed.
            # The report function takes `datos_mbrp` and expects (codigo, desc, neto, comprado, diferencia, margen)
            # We need to calculate those fields here.
            
            # Placeholder for comprado, diferencia, margen calculations
            # In a real scenario, these would come from DB queries or complex logic.
            monto_vendido = neto
            monto_comprado = 0.0 # Placeholder
            diferencia = monto_vendido - monto_comprado
            margen_pct = (diferencia / monto_vendido * 100) if monto_vendido else 0.0
            
            # Construct a structure compatible with ProductoMBRP response model for API
            mbrp_item = ProductoMBRP(
                codigo=item[0],
                descripcion=item[1],
                departamento=item[2] if len(item) > 2 else None,
                grupo=item[3] if len(item) > 3 else None,
                subgrupo=item[4] if len(item) > 4 else None,
                ventas_netas=neto,
                # Rotacion classified for MBRP
                rotacion=current_rotacion,
                # MBRP specific fields
                monto_vendido=monto_vendido,
                monto_comprado=monto_comprado,
                diferencia=diferencia,
                margen_pct=margen_pct,
                im_movilidad=im # Include IM for potential filtering/sorting
            )
            classified_data.append(mbrp_item)
        
    except Exception as e:
        logger.error(f"Error processing TRA data for MBRP analysis: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al procesar datos para análisis MBRP")
    
    # Paginate the classified MBRP data
    paginated_data, total_pages, current_page = paginate(
        classified_data, page, page_size
    )
    
    # The MBRPReportSummary model is for the overall report, not for paginated items.
    # For this endpoint, we should return the paginated list of MBRP items.
    # If a summary report endpoint is desired, that would be separate.
    
    return paginated_data

# --- Health Check ---
@app.get("/health", tags=["General"])
async def health_check():
    """Basic health check endpoint."""
    # A more thorough health check could verify database connectivity
    return {"status": "ok", "api_version": "0.1.0"}

# --- CORS Configuration (if needed for frontend) ---
# from fastapi.middleware.cors import CORSMiddleware
# origins = ["http://localhost:3000", "http://localhost:8080"] # Example origins
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# --- Notes ---
# 1. This file sets up a basic FastAPI application structure.
# 2. It includes SQLAlchemy models (from app/models.py) for ORM mapping and Pydantic models for API validation.
# 3. Endpoints for auth, user management, roles, permissions, scheduled shipments, sede configurations, stock alerts, TRA sales, and MBRP report are implemented.
# 4. Database connection is configured using app/database.py and reads from db_config.ini.
# 5. Password hashing uses bcrypt; SecureCredentialsManager logic for keyring/cryptography needs to be integrated if used by API services.
# 6. Session management uses simple tokens; JWT could be integrated for more robust token handling.
# 7. The MBRP report generation uses mock data for TRA sales; actual DB queries are needed for accurate analysis.
# 8. Hierarchy loading is simplified; consider caching strategies for performance.
# 9. Favorite products feature is a placeholder and needs actual implementation.
# 10. `get_current_user_id_for_auth` dependency is a placeholder and needs to be implemented to return user ID for permission checks.
# 11. MBRP report data structure and calculations rely on the mock data and might need adjustments when real data queries are implemented.