from fastapi import FastAPI, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator, model_validator
from datetime import datetime, timedelta
import secrets
import bcrypt
import keyring
import os
import json
import logging

from app.database import engine, SessionLocal, Base, get_db, init_db_connection
from app.models import (
    UserDB, RoleDB, PermissionDB, AuditDB, SessionDB, UserCreateRequest,
    UserUpdateRequest, UserResponse, LoginRequestAPI, LoginResponseAPI, ChangePasswordRequest,
    PermissionResponse, RoleResponse, UserAuth, RoleCreateRequest, UserRoleDB, RolePermissionDB,
    UserModuleDB, EnvioProgramadoCreateAPI, EnvioProgramadoResponse,
    SedeConfiguracionDB, SedeConfiguracionCreate, SedeConfiguracionResponse,
    StockAlert, StockAlertDetail, JerarquiaProducto, ProductoVentas, ProductoMBRP, MBRPReportSummary,
    db_to_pydantic
)
from app.routers import auth, config as config_router
from app.crud import (
    get_user, get_user_by_username, get_users, create_user, update_user, delete_user,
    get_role, get_role_by_name, get_roles, create_role, update_role, delete_role,
    get_permission_by_code, get_permissions,
    get_active_session_by_token, invalidate_session_token,
    log_audit_access,
    create_envio_programado, get_pending_envios, update_envio_estado,
    get_active_sedes,
    get_user_extra_info, get_all_roles_db, get_user_permissions # New CRUD function to get user permissions
)
from pal.services.stock import get_existencias_por_ubicacion, filter_alertas, paginate, load_all_jerarquia, build_producto_jerarquia, fetch_stock_alerts_optimized, get_stock_alerts_chunked
from pal.services.tra import filter_ventas_tra, paginate_tra, calcular_porcentajes_representacion, _get_tra_neto, clasificar_rotacion_tra
from pal.services.mbrp import calcular_indice_movilidad, obtener_fecha_ultima_venta, calcular_dias_sin_venta, filtrar_productos_baja_rotacion, clasificar_rotacion_mbrp, generar_reporte_baja_rotacion
from app.utils import filter_by_hierarchy, paginate, paginate_tra, hash_password, check_password

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
        "url": "http://example.com/docs",
        "email": "devteam@example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# --- Database Startup ---
@app.on_event("startup")
def startup_db_client():
    if init_db_connection():
        logger.info("Base de datos inicializada correctamente.")
        try:
            # Ensure tables exist only if we have a connection
            if engine:
                 Base.metadata.create_all(bind=engine)
                 logger.info("Tablas de base de datos verificadas.")
                 # Seed initial data
                 from app.database import seed_initial_data
                 seed_initial_data()
        except Exception as e:
            logger.error(f"Error al verificar tablas o sembrar datos: {e}")
    else:
        logger.warning("No se pudo conectar a la base de datos al inicio. Esperando configuración a través de API.")

# --- Database Setup ---
# Removed global create_all here, moved to startup event to handle lazy connection

# --- Security Configuration ---
# ... (omitted for brevity)

# --- Authentication Dependency ---
async def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserDB:
    """
    Dependency to get the current authenticated user from session token.
    Requires Authorization header with a Bearer token.
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
        invalidate_session_token(db, token) # Clean up session if user no longer exists
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario asociado a la sesión no encontrado")

    return user_db

# --- New Dependency for Permission Checking ---
async def require_permission(permission_code: str, user: UserDB = Depends(get_current_user)):
    """
    Dependency to check if the current authenticated user has a specific permission code.
    This function expects the user object to have roles loaded, and roles to have permissions loaded.
    """
    # user is already authenticated by get_current_user
    # Fetch all permission codes associated with the user's roles
    user_permissions = get_user_permissions(user.id) # Assumes CRUD function exists and returns set of permission codes

    if permission_code not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario no tiene el permiso '{permission_code}' requerido."
        )
    # If permission is found, continue execution
    return user # Return user object

# --- Placeholder for current_user_id dependency for permission checks ---
async def get_current_user_id_for_auth(request: Request, db: Session = Depends(get_db)) -> Optional[int]:
    """Helper dependency to get current user ID for permission checks. Returns None if not authenticated."""
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

# Include the auth router
app.include_router(auth.router)
app.include_router(config_router.router)

# --- User Management Endpoints ---
# Define permission codes for user management
USER_MANAGEMENT_CREATE = "USER_MANAGEMENT_CREATE"
USER_MANAGEMENT_READ = "USER_MANAGEMENT_READ"
USER_MANAGEMENT_UPDATE = "USER_MANAGEMENT_UPDATE"
USER_MANAGEMENT_DELETE = "USER_MANAGEMENT_DELETE"

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def create_user_endpoint(
    user_create_req: UserCreateRequest,
    db: Session = Depends(get_db),
    # Requires the specific permission to create users
    user: UserDB = Depends(lambda p_code=USER_MANAGEMENT_CREATE: require_permission(p_code))
):
    """Creates a new user. Requires USER_MANAGEMENT_CREATE permission."""
    if get_user_by_username(db, user_create_req.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso."
        )
    if get_user(db, email=user_create_req.email):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está en uso."
        )

    try:
        new_user_db = create_user(db, user_create_req)
        user_for_response = get_user(db, new_user_db.id)
        if not user_for_response:
            logger.error(f"User created with ID {new_user_db.id} but could not be re-fetched for response.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al recuperar el usuario recién creado.")

        pydantic_user = db_to_pydantic(user_for_response, UserResponse)
        if pydantic_user:
            return pydantic_user
        else:
            logger.warning(f"db_to_pydantic failed for user {user_for_response.id}, using manual fallback.")
            return UserResponse(
                id=user_for_response.id, username=user_for_response.username, nombre_completo=user_for_response.nombre_completo,
                email=user_for_response.email, activo=user_for_response.activo, fecha_creacion=user_for_response.fecha_creacion,
                fecha_ultimo_acceso=user_for_response.fecha_ultimo_acceso, intentos_fallidos=user_for_response.intentos_fallidos,
                bloqueado_hasta=user_for_response.bloqueado_hasta,
                roles=[r.id for r in user_for_response.roles] if user_for_response.roles else [],
                modulos_habilitados=[m.modulo for m in user_for_response.modulos_habilitados] if user_for_response.modulos_habilitados else []
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear usuario.")

@app.get("/users/", response_model=List[UserResponse], tags=["Users"])
async def get_all_users_endpoint(
    activo_only: bool = True,
    db: Session = Depends(get_db),
    # Requires the specific permission to read all users
    user: UserDB = Depends(lambda p_code=USER_MANAGEMENT_READ: require_permission(p_code))
):
    """Retrieves a list of users, optionally filtered by active status. Requires USER_MANAGEMENT_READ permission."""
    users_db = get_users(db, active_only=activo_only)

    users_response = []
    for user_db in users_db:
        try:
            pydantic_user = db_to_pydantic(user_db, UserResponse)
            if pydantic_user:
                users_response.append(pydantic_user)
            else:
                logger.warning(f"db_to_pydantic failed for user {user_db.id} in get_all_users, using fallback.")
                users_response.append(UserResponse(
                    id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
                    email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
                    fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
                    bloqueado_hasta=user_db.bloqueado_hasta,
                    roles=[r.id for r in user_db.roles] if user_db.roles else [],
                    modulos_habilitados=[m.modulo for m in user_db.modulos_habilitados] if user_db.modulos_habilitados else []
                ))
        except Exception as e:
            logger.error(f"Error converting user DB object {user_db.id} to response model: {e}")
            users_response.append(UserResponse(
                id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
                email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
                fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
                bloqueado_hasta=user_db.bloqueado_hasta, roles=[], modulos_habilitados=[]
            ))

    return users_response

@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user_by_id_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    # Requires the specific permission to read any user's details
    user: UserDB = Depends(lambda p_code=USER_MANAGEMENT_READ: require_permission(p_code))
):
    """Retrieves a specific user by their ID. Requires USER_MANAGEMENT_READ permission."""
    user_db = get_user(db, user_id)
    if not user_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    try:
        pydantic_user = db_to_pydantic(user_db, UserResponse)
        if pydantic_user:
            return pydantic_user
        else:
            logger.warning(f"db_to_pydantic failed for user {user_id} in get_user_by_id, using fallback.")
            return UserResponse(
                id=user_db.id, username=user_db.username, nombre_completo=user_db.nombre_completo,
                email=user_db.email, activo=user_db.activo, fecha_creacion=user_db.fecha_creacion,
                fecha_ultimo_acceso=user_db.fecha_ultimo_acceso, intentos_fallidos=user_db.intentos_fallidos,
                bloqueado_hasta=user_db.bloqueado_hasta,
                roles=[r.id for r in user_db.roles] if user_db.roles else [],
                modulos_habilitados=[m.modulo for m in user_db.modulos_habilitados] if user_db.modulos_habilitados else []
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
    user_update_req: UserUpdateRequest,
    db: Session = Depends(get_db),
    # Requires the specific permission to update users
    user: UserDB = Depends(lambda p_code=USER_MANAGEMENT_UPDATE: require_permission(p_code))
):
    """Updates an existing user. Requires USER_MANAGEMENT_UPDATE permission."""
    if user_update_req.roles is not None:
        role_ids_to_assign = set(user_update_req.roles)
        all_roles_db = get_all_roles_db(db)
        valid_role_ids = {role.id for role in all_roles_db}

        if not role_ids_to_assign.issubset(valid_role_ids):
            invalid_ids = role_ids_to_assign - valid_role_ids
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se proporcionaron IDs de rol no válidos: {', '.join(map(str, invalid_ids))}"
            )

    updated_user_db = update_user(db, user_id, user_update_req)
    if not updated_user_db:
        if not get_user(db, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el usuario.")

    try:
        user_for_response = get_user(db, user_id)
        if not user_for_response:
            logger.error(f"User {user_id} updated but could not be re-fetched for response.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al recuperar el usuario actualizado.")

        pydantic_user = db_to_pydantic(user_for_response, UserResponse)
        if pydantic_user:
            return pydantic_user
        else:
            logger.warning(f"db_to_pydantic failed for user {user_id} in update_user, using fallback.")
            return UserResponse(
                id=updated_user_db.id, username=updated_user_db.username, nombre_completo=updated_user_db.nombre_completo,
                email=updated_user_db.email, activo=updated_user_db.activo, fecha_creacion=updated_user_db.fecha_creacion,
                fecha_ultimo_acceso=updated_user_db.fecha_ultimo_acceso, intentos_fallidos=updated_user_db.intentos_fallidos,
                bloqueado_hasta=updated_user_db.bloqueado_hasta,
                roles=[r.id for r in updated_user_db.roles] if updated_user_db.roles else [],
                modulos_habilitados=[m.modulo for m in updated_user_db.modulos_habilitados] if updated_user_db.modulos_habilitados else []
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error converting updated user {user_id} to response model: {e}")
        return UserResponse(
            id=updated_user_db.id, username=updated_user_db.username, nombre_completo=updated_user_db.nombre_completo,
            email=updated_user_db.email, activo=updated_user_db.activo, fecha_creacion=updated_user_db.fecha_creacion,
            fecha_ultimo_acceso=updated_user_db.fecha_ultimo_acceso, intentos_fallidos=updated_user_db.intentos_fallidos,
            bloqueado_hasta=updated_user_db.bloqueado_hasta, roles=[], modulos_habilitados=[]
        )

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
async def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    # Requires the specific permission to delete users
    user: UserDB = Depends(lambda p_code=USER_MANAGEMENT_DELETE: require_permission(p_code))
):
    """Deletes a user by deactivating their account (soft delete). Requires USER_MANAGEMENT_DELETE permission."""
    deleted = delete_user(db, user_id)
    if not deleted:
        if not get_user(db, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al desactivar el usuario.")
    return None

# --- Role Management Endpoints ---
# Define permission codes for role management
ROLE_MANAGEMENT_CREATE = "ROLE_MANAGEMENT_CREATE"
ROLE_MANAGEMENT_READ = "ROLE_MANAGEMENT_READ"
ROLE_MANAGEMENT_UPDATE = "ROLE_MANAGEMENT_UPDATE"
ROLE_MANAGEMENT_DELETE = "ROLE_MANAGEMENT_DELETE"

@app.post("/roles/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, tags=["Roles"])
async def create_role_endpoint(
    role_create: RoleCreateRequest,
    db: Session = Depends(get_db),
    # Requires the specific permission to create roles
    user: UserDB = Depends(lambda p_code=ROLE_MANAGEMENT_CREATE: require_permission(p_code))
):
    """Creates a new role. Requires ROLE_MANAGEMENT_CREATE permission."""
    if get_role_by_name(db, role_create.nombre):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre del rol ya está en uso.")

    try:
        new_role_db = create_role(db, role_create)
        return RoleResponse(id=new_role_db.id, nombre=new_role_db.nombre, descripcion=new_role_db.descripcion, es_sistema=new_role_db.es_sistema)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear rol.")

@app.get("/roles/", response_model=List[RoleResponse], tags=["Roles"])
async def get_all_roles_endpoint(
    db: Session = Depends(get_db),
    # Requires the specific permission to read roles
    user: UserDB = Depends(lambda p_code=ROLE_MANAGEMENT_READ: require_permission(p_code))
):
    """Retrieves a list of all roles. Requires ROLE_MANAGEMENT_READ permission."""
    roles_db = get_all_roles_db(db)
    return [RoleResponse(id=r.id, nombre=r.nombre, descripcion=r.descripcion, es_sistema=r.es_sistema) for r in roles_db]

@app.get("/roles/{role_id}", response_model=RoleResponse, tags=["Roles"])
async def get_role_by_id_endpoint(
    role_id: int,
    db: Session = Depends(get_db),
    # Requires the specific permission to read roles
    user: UserDB = Depends(lambda p_code=ROLE_MANAGEMENT_READ: require_permission(p_code))
):
    """Retrieves a specific role by its ID. Requires ROLE_MANAGEMENT_READ permission."""
    role_db = get_role(db, role_id)
    if not role_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return RoleResponse(id=role_db.id, nombre=role_db.nombre, descripcion=role_db.descripcion, es_sistema=role_db.es_sistema)

@app.put("/roles/{role_id}", response_model=RoleResponse, tags=["Roles"])
async def update_role_endpoint(
    role_id: int,
    role_update: RoleCreateRequest,
    db: Session = Depends(get_db),
    # Requires the specific permission to update roles
    user: UserDB = Depends(lambda p_code=ROLE_MANAGEMENT_UPDATE: require_permission(p_code))
):
    """Updates an existing role. Requires ROLE_MANAGEMENT_UPDATE permission."""
    update_data = role_update.model_dump(exclude_unset=True, exclude={'es_sistema'})

    try:
        updated_role_db = update_role(db, role_id, update_data)
        if not updated_role_db:
            if not get_role(db, role_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
            else:
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el rol.")

        return RoleResponse(id=updated_role_db.id, nombre=updated_role_db.nombre, descripcion=updated_role_db.descripcion, es_sistema=updated_role_db.es_sistema)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating role {role_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar rol.")

@app.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Roles"])
async def delete_role_endpoint(
    role_id: int,
    db: Session = Depends(get_db),
    # Requires the specific permission to delete roles
    user: UserDB = Depends(lambda p_code=ROLE_MANAGEMENT_DELETE: require_permission(p_code))
):
    """Deletes a role. Requires ROLE_MANAGEMENT_DELETE permission."""
    try:
        if not delete_role(db, role_id):
            if get_role(db, role_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pueden eliminar roles del sistema o que estén en uso.")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting role {role_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar rol.")
    return None

# --- Permissions Endpoints ---
# This endpoint lists existing permissions. Typically, viewing permissions might be restricted to admins or certain roles.
# For now, let's require a general read permission if available, or keep it less restricted.
# Let's assume a generic "PERMISSION_READ_ALL" or similar is needed for viewing.
PERMISSION_READ_ALL = "PERMISSION_READ_ALL"
@app.get("/permissions/", response_model=List[PermissionResponse], tags=["Permissions"])
async def get_all_permissions_endpoint(
    db: Session = Depends(get_db),
    # Requires the specific permission to read all permissions
    user: UserDB = Depends(lambda p_code=PERMISSION_READ_ALL: require_permission(p_code))
):
    """Retrieves a list of all available permissions. Requires PERMISSION_READ_ALL permission."""
    permissions_db = get_permissions(db)
    return [PermissionResponse(id=p.id, codigo=p.codigo, modulo=p.modulo, descripcion=p.descripcion) for p in permissions_db]

# --- API for Services ---
# Example: EnvioProgramado
# Let's assume creating shipments requires a specific permission.
SHIPMENT_CREATE = "SHIPMENT_CREATE"
SHIPMENT_READ = "SHIPMENT_READ"

@app.post("/envios_programados/", response_model=EnvioProgramadoResponse, status_code=status.HTTP_201_CREATED, tags=["Servicios"])
async def schedule_envio_endpoint(
    envio_create: EnvioProgramadoCreateAPI,
    db: Session = Depends(get_db),
    # Requires authentication and SHIPMENT_CREATE permission
    user: UserDB = Depends(lambda p_code=SHIPMENT_CREATE: require_permission(p_code))
):
    """Schedules a new shipment. Requires SHIPMENT_CREATE permission."""
    try:
        envio_data = envio_create.model_dump()
        new_envio_db = create_envio_programado(db, envio_data)

        if not new_envio_db:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al programar envío: el servicio CRUD devolvió nulo.")

        return EnvioProgramadoResponse(
            id=new_envio_db.id,
            numero_cliente=new_envio_db.numero_cliente,
            fecha_programada=new_envio_db.fecha_programada,
            tipo_envio=new_envio_db.tipo_envio,
            codigo_producto=new_envio_db.codigo_producto,
            fecha_creacion=new_envio_db.fecha_creacion,
            estado=new_envio_db.estado
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error scheduling shipment: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al programar envío.")

@app.get("/envios_programados/", response_model=List[EnvioProgramadoResponse], tags=["Servicios"])
async def get_scheduled_envios(
    db: Session = Depends(get_db),
    estado: Optional[str] = None,
    fecha_limite_str: Optional[str] = Query(None, alias="fecha_limite"),
    # Requires authentication and SHIPMENT_READ permission
    user: UserDB = Depends(lambda p_code=SHIPMENT_READ: require_permission(p_code))
):
    """Retrieves scheduled shipments, optionally filtered by status and date. Requires SHIPMENT_READ permission."""
    query = db.query(EnvioProgramadoDB)
    if estado:
        query = query.filter(EnvioProgramadoDB.estado == estado)

    if fecha_limite_str:
        try:
            fecha_limite = datetime.strptime(fecha_limite_str, "%Y-%m-%d")
            query = query.filter(EnvioProgramadoDB.fecha_programada <= fecha_limite)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de fecha inválido para fecha_limite. Use YYYY-MM-DD.")

    try:
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
    except Exception as e:
        logger.error(f"Error fetching scheduled shipments: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener envíos programados.")

# --- Stock Alerts Endpoints ---
STOCK_ALERTS_READ = "STOCK_ALERTS_READ"
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
    # Requires authentication and STOCK_ALERTS_READ permission
    user: UserDB = Depends(lambda p_code=STOCK_ALERTS_READ: require_permission(p_code))
):
    """Retrieves stock alerts, optionally filtered and sorted. Requires STOCK_ALERTS_READ permission."""
    product_hierarchy = {}
    try:
        pass # Placeholder for hierarchy loading
    except Exception as e:
        logger.error(f"Could not load product hierarchy for filtering: {e}")
        product_hierarchy = {}

    try:
        all_alerts_db = fetch_stock_alerts_optimized(db)
    except Exception as e:
        logger.error(f"Error fetching stock alerts from DB: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener alertas de stock desde la base de datos.")

    if not all_alerts_db:
        return []

    stock_alerts_pydantic = []
    for r in all_alerts_db:
        if r and len(r) >= 4:
            try:
                stock_alerts_pydantic.append(StockAlert(codigo=r[0], descripcion=r[1], stock=int(r[2]), nivel=r[3]))
            except (TypeError, ValueError) as e:
                logger.warning(f"Skipping stock alert due to data conversion error: {r} - {e}")
        else:
            logger.warning(f"Skipping malformed stock alert data: {r}")

    user_favorites = set() # Placeholder for favorite products
    try:
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
    except Exception as e:
        logger.error(f"Error applying filters to stock alerts: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al aplicar filtros a las alertas de stock.")

    paginated_data, total_pages, current_page = paginate(
        filtered_alerts, page, page_size
    )
    return paginated_data

# --- TRA Endpoints ---
TRA_SALES_READ = "TRA_SALES_READ"
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
    # Requires authentication and TRA_SALES_READ permission
    user: UserDB = Depends(lambda p_code=TRA_SALES_READ: require_permission(p_code))
):
    """Retrieves TRA sales data. Requires TRA_SALES_READ permission."""
    logger.warning("Using mock data for TRA sales. Implement actual DB query.")
    raw_tra_data = [
        ('PROD001', 'Producto Uno', 'DEP1', 'GRP1', 'SUB1', 1500.50, 'ALTA', 10.0, 'CRITICO', 'ALTA'),
        ('PROD002', 'Producto Dos', 'DEP1', 'GRP1', 'SUB1', 800.00, 'MEDIA', 8.0, 'BAJO', 'MEDIA'),
        ('PROD003', 'Producto Tres', 'DEP1', 'GRP2', 'SUB2', 300.75, 'BAJA', 5.0, 'MEDIO', 'BAJA'),
        ('PROD004', 'Producto Cuatro', 'DEP2', 'GRP3', 'SUB3', 1200.00, 'ALTA', 15.0, 'NORMAL', 'ALTA'),
        ('PROD005', 'Producto Cinco', 'DEP1', 'GRP1', 'SUB1', 50.25, 'BAJA', 2.5, 'BAJO', 'MEDIA'),
        ('PROD006', 'Producto Seis', 'DEP3', 'GRP4', 'SUB4', 0.00, 'SIN MOVIMIENTO', 0.0, 'NULO', 'NULO'),
        ('PROD007', 'Producto Siete', 'DEP1', 'GRP1', 'SUB1', 950.00, 'ALTA', 9.0, 'MEDIO', 'ALTA'),
    ]

    user_favorites = set()
    stock_alerts_data = {
        'PROD001': ('Producto Uno', 10.0, 'CRITICO'),
        'PROD002': ('Producto Dos', 8.0, 'BAJO'),
        'PROD003': ('Producto Tres', 5.0, 'MEDIO'),
        'PROD004': ('Producto Cuatro', 15.0, 'NORMAL'),
        'PROD005': ('Producto Cinco', 2.5, 'BAJO'),
        'PROD006': ('Producto Seis', 0.0, 'NULO'),
        'PROD007': ('Producto Siete', 9.0, 'MEDIO'),
    }

    try:
        filtered_tra_data = filter_ventas_tra(
            raw_tra_data,
            dept_code=dept_code,
            group_code=group_code,
            sub_code=sub_code,
            search_text=search_text,
            filter_rotacion=filter_rotacion,
            favoritos=user_favorites,
            alertas_stock=stock_alerts_data
        )

        paginated_data, total_pages, current_page = paginate_tra(
            filtered_tra_data, page, page_size
        )

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
            except (IndexError, TypeError, ValueError) as e:
                logger.warning(f"Skipping TRA item due to mapping error: {item} - {e}")
                continue

        return response_data
    except Exception as e:
        logger.error(f"Error fetching or processing TRA sales data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener y procesar datos de ventas TRA.")

# --- MBRP Endpoints ---
MBRP_REPORT_READ = "MBRP_REPORT_READ"
@app.get("/mbrp/report/", response_model=List[ProductoMBRP], tags=["MBRP"])
async def get_mbrp_report(
    db: Session = Depends(get_db),
    dept_code: Optional[str] = Query(None, alias="department"),
    group_code: Optional[str] = Query(None, alias="group"),
    sub_code: Optional[str] = Query(None, alias="subgroup"),
    search_text: Optional[str] = Query(None, alias="search"),
    im_threshold: float = Query(20.0, alias="im_threshold"),
    sede_codigo: Optional[str] = Query(None, alias="sede"),
    fecha_inicio_str: Optional[str] = Query(None, alias="start_date"),
    fecha_fin_str: Optional[str] = Query(None, alias="end_date"),
    page: int = 1,
    page_size: int = 100,
    # Requires authentication and MBRP_REPORT_READ permission
    user: UserDB = Depends(lambda p_code=MBRP_REPORT_READ: require_permission(p_code))
):
    """Generates an MBRP report. Requires MBRP_REPORT_READ permission."""
    fecha_inicio = None
    fecha_fin = None
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de fecha inválido para start_date. Use YYYY-MM-DD.")
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de fecha inválido para end_date. Use YYYY-MM-DD.")

    if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La fecha de fin no puede ser anterior a la fecha de inicio.")

    logger.warning("Using mock data for MBRP analysis. Implement actual DB query.")
    raw_tra_data_for_mbrp = [
        ('PROD001', 'Producto Uno', 'DEP1', 'GRP1', 'SUB1', 1500.50, 'ALTA', 10.0, 1.6, 5.0, 10.0),
        ('PROD002', 'Producto Dos', 'DEP1', 'GRP1', 'SUB1', 800.00, 'MEDIA', 8.0, 1.28, 4.0, 8.0),
        ('PROD003', 'Producto Tres', 'DEP1', 'GRP2', 'SUB2', 300.75, 'BAJA', 5.0, 0.8, 2.5, 5.0),
        ('PROD004', 'Producto Cuatro', 'DEP2', 'GRP3', 'SUB3', 1200.00, 'ALTA', 15.0, 2.4, 7.0, 15.0),
        ('PROD005', 'Producto Cinco', 'DEP1', 'GRP1', 'SUB1', 50.25, 'BAJA', 2.5, 0.4, 1.0, 2.5),
        ('PROD006', 'Producto Seis', 'DEP3', 'GRP4', 'SUB4', 0.00, 'SIN MOVIMIENTO', 0.0, 0.0, 0.0, 0.0),
        ('PROD007', 'Producto Siete', 'DEP1', 'GRP1', 'SUB1', 950.00, 'ALTA', 9.0, 1.44, 4.5, 9.0),
        ('PROD008', 'Producto Ocho', 'DEP1', 'GRP1', 'SUB1', 5.50, 'BAJA', 1.0, 0.16, 0.5, 1.0),
        ('PROD009', 'Producto Nueve', 'DEP1', 'GRP1', 'SUB1', 10.00, 'BAJA', 2.0, 0.32, 0.6, 2.0),
    ]

    try:
        filtered_tra_data = filter_by_hierarchy(
            raw_tra_data_for_mbrp,
            dept_code=dept_code,
            group_code=group_code,
            sub_code=sub_code,
            get_dept=lambda r: r[2] if len(r) > 2 else None,
            get_group=lambda r: r[3] if len(r) > 3 else None,
            get_sub=lambda r: r[4] if len(r) > 4 else None,
            missing_strategy="exclude",
        )

        if search_text:
            text = search_text.strip().lower()
            filtered_tra_data = [
                r for r in filtered_tra_data if len(r) >= 2 and (
                    text in str(r[0]).lower() or text in str(r[1]).lower()
                )
            ]

        if sede_codigo:
            logger.warning("Sede filtering is a placeholder. Implement actual logic for sede filtering.")

        indices_movilidad = calcular_indice_movilidad(filtered_tra_data)

        classified_data = []
        for item in filtered_tra_data:
            if len(item) >= 11:
                codigo, descripcion, departamento, grupo, subgrupo, neto_ventas, _, precio, impuesto1, costo, stock_actual = item[:11]
                neto = neto_ventas if neto_ventas is not None else 0.0
                im = indices_movilidad.get(codigo, 0.0)

                rotacion_mbrp_class = "SIN_MOVIMIENTO"
                if neto > 0:
                    if im <= 10.0: rotacion_mbrp_class = "BAJA"
                    elif im <= 30.0: rotacion_mbrp_class = "MEDIA"
                    else: rotacion_mbrp_class = "ALTA"

                monto_vendido = neto
                monto_comprado = costo * (stock_actual if stock_actual is not None else 0)
                diferencia = monto_vendido - monto_comprado
                margen_pct = (diferencia / monto_vendido * 100) if monto_vendido and monto_vendido > 0 else 0.0

                mbrp_item = ProductoMBRP(
                    codigo=codigo, descripcion=descripcion, departamento=departamento, grupo=grupo, subgrupo=subgrupo,
                    ventas_netas=neto, rotacion=rotacion_mbrp_class, monto_vendido=monto_vendido,
                    monto_comprado=monto_comprado, diferencia=diferencia, margen_pct=margen_pct,
                    im_movilidad=im, stock_actual=stock_actual if stock_actual is not None else 0
                )
                classified_data.append(mbrp_item)
            else:
                logger.warning(f"Skipping MBRP item due to insufficient data: {item}")

        if im_threshold is not None:
            filtered_by_im = [item for item in classified_data if item.im_movilidad is not None and item.im_movilidad <= im_threshold]
        else:
            filtered_by_im = classified_data

        paginated_data, total_pages, current_page = paginate(
            filtered_by_im, page, page_size
        )
        return paginated_data

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error generating MBRP report: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al generar el reporte MBRP.")

# --- Health Check ---
@app.get("/health", tags=["General"])
async def health_check(
    # Health check might not require authentication, or could be a minimal auth check
    # For consistency, let's require a generic read permission if available, or allow unauthenticated access if not.
    # If PERMISSION_READ_ALL is defined and meaningful for health checks, use it. Otherwise, rely on get_current_user_id_for_auth.
    user_id: Optional[int] = Depends(get_current_user_id_for_auth)
):
    """Basic health check endpoint."""
    # A more thorough health check could verify database connectivity
    return {"status": "ok", "api_version": "0.1.0"}

# --- CORS Configuration ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
