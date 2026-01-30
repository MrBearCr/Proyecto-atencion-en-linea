from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import (
    UserDB, UserCreateRequest, UserUpdateRequest, RoleDB, RoleCreateRequest, PermissionDB,
    UserRoleDB, RolePermissionDB, UserModuleDB, AuditDB, SessionDB, ClienteDB,
    EnvioProgramadoDB, SedeConfiguracionDB
)
from app.database import get_db # Assuming get_db is correctly imported and configured
from app.models import hash_password, check_password # Import password utilities
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# --- User CRUD Operations ---

def get_user(db: Session, user_id: int) -> Optional[UserDB]:
    """Fetches a user by ID."""
    try:
        return db.query(UserDB).filter(UserDB.id == user_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching user {user_id}: {e}")
        return None

def get_user_by_username(db: Session, username: str) -> Optional[UserDB]:
    """Fetches a user by username."""
    try:
        return db.query(UserDB).filter(UserDB.username == username).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching user by username '{username}': {e}")
        return None

def get_users(db: Session, active_only: bool = True) -> List[UserDB]:
    """Fetches a list of users."""
    try:
        query = db.query(UserDB)
        if active_only:
            query = query.filter(UserDB.activo == True)
        return query.all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching users: {e}")
        return []

def create_user(db: Session, user_create: UserCreateRequest) -> UserDB:
    """Creates a new user."""
    hashed_password = hash_password(user_create.password)
    new_user = UserDB(
        username=user_create.username,
        password_hash=hashed_password,
        nombre_completo=user_create.nombre_completo,
        email=user_create.email,
        activo=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Assign roles if provided
    if user_create.roles_ids:
        for role_id in user_create.roles_ids:
            role_db = db.query(RoleDB).filter(RoleDB.id == role_id).first()
            if role_db:
                user_role = UserRoleDB(usuario_id=new_user.id, rol_id=role_id)
                db.add(user_role)
            else:
                logger.warning(f"Rol ID {role_id} no encontrado al crear usuario {new_user.id}")
        db.commit()
    
    # Fetch the created user again to ensure relationships are loaded if needed for response
    # This is a common pattern if the initial 'new_user' object doesn't eagerly load relationships.
    # For simplicity here, we assume refresh is sufficient or relationships are lazy loaded.
    return new_user

def update_user(db: Session, user_id: int, user_update: UserUpdateRequest) -> Optional[UserDB]:
    """Updates an existing user."""
    user_db = get_user(db, user_id)
    if not user_db:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    
    # Handle password change separately if it's part of the update payload
    # if 'password' in update_data:
    #     user_db.password_hash = hash_password(update_data.pop('password'))

    for field, value in update_data.items():
        if field != 'password': # Avoid trying to set password directly here
            setattr(user_db, field, value)

    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return user_db

def delete_user(db: Session, user_id: int) -> bool:
    """Soft deletes a user by deactivating them."""
    user_db = get_user(db, user_id)
    if not user_db:
        return False
    
    user_db.activo = False
    db.add(user_db)
    db.commit()
    return True

# --- Role CRUD Operations ---

def get_role(db: Session, role_id: int) -> Optional[RoleDB]:
    """Fetches a role by ID."""
    try:
        return db.query(RoleDB).filter(RoleDB.id == role_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching role {role_id}: {e}")
        return None

def get_role_by_name(db: Session, nombre: str) -> Optional[RoleDB]:
    """Fetches a role by name."""
    try:
        return db.query(RoleDB).filter(RoleDB.nombre == nombre).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching role by name '{nombre}': {e}")
        return None

def get_roles(db: Session) -> List[RoleDB]:
    """Fetches a list of all roles."""
    try:
        return db.query(RoleDB).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching roles: {e}")
        return []

def create_role(db: Session, role_create: RoleCreateRequest) -> RoleDB:
    """Creates a new role."""
    new_role = RoleDB(
        nombre=role_create.nombre,
        descripcion=role_create.descripcion,
        es_sistema=False # New roles are not system roles by default
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    # Assign permissions if provided
    if role_create.permisos_codigos:
        for perm_code in role_create.permisos_codigos:
            perm_db = db.query(PermissionDB).filter(PermissionDB.codigo == perm_code).first()
            if perm_db:
                role_perm = RolePermissionDB(rol_id=new_role.id, permiso_id=perm_db.id)
                db.add(role_perm)
            else:
                logger.warning(f"Permiso código '{perm_code}' no encontrado al crear rol '{new_role.nombre}'")
        db.commit()
    
    return new_role

def update_role(db: Session, role_id: int, role_update_data: Dict[str, Any]) -> Optional[RoleDB]:
    """Updates an existing role."""
    role_db = get_role(db, role_id)
    if not role_db:
        return None

    # Handle specific fields that require logic (e.g., name conflicts, permissions)
    if 'nombre' in role_update_data and role_update_data['nombre'] != role_db.nombre:
        if get_role_by_name(db, role_update_data['nombre']):
            raise ValueError("El nombre del rol ya está en uso")
        setattr(role_db, 'nombre', role_update_data['nombre'])
        
    if 'descripcion' in role_update_data:
        setattr(role_db, 'descripcion', role_update_data['descripcion'])

    # Permission update logic is more complex (handling additions/removals)
    # This part would need explicit implementation if required for updates.

    db.add(role_db)
    db.commit()
    db.refresh(role_db)
    return role_db

def delete_role(db: Session, role_id: int) -> bool:
    """Deletes a role."""
    role_db = get_role(db, role_id)
    if not role_db:
        return False
    
    # Prevent deletion of system roles
    if role_db.es_sistema:
        raise ValueError("No se pueden eliminar roles del sistema")

    db.delete(role_db)
    db.commit()
    return True

# --- Permission CRUD Operations ---

def get_permission_by_code(db: Session, code: str) -> Optional[PermissionDB]:
    """Fetches a permission by its code."""
    try:
        return db.query(PermissionDB).filter(PermissionDB.codigo == code).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching permission by code '{code}': {e}")
        return None

def get_permissions(db: Session) -> List[PermissionDB]:
    """Fetches a list of all permissions."""
    try:
        return db.query(PermissionDB).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching permissions: {e}")
        return []

# --- Session Operations ---
def get_active_session_by_token(db: Session, token: str) -> Optional[SessionDB]:
    """Fetches an active session by its token."""
    try:
        now = datetime.utcnow()
        return db.query(SessionDB).filter(
            SessionDB.token == token,
            SessionDB.activa == True,
            SessionDB.fecha_expiracion > now
        ).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching active session for token '{token[:8]}...': {e}")
        return None

def invalidate_session_token(db: Session, token: str) -> bool:
    """Invalidates a session token."""
    session_db = db.query(SessionDB).filter(SessionDB.token == token).first()
    if session_db:
        session_db.activa = False
        db.add(session_db)
        try:
            db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error invalidating session {token[:8]}...: {e}")
            db.rollback()
            return False
    return False

# --- Audit Operations ---
def log_audit_access(
    db: Session,
    accion: str,
    modulo: Optional[str],
    detalle: Optional[str],
    ip_address: Optional[str],
    exitoso: bool,
    usuario_id: Optional[int] = None
):
    """Logs an access audit event."""
    try:
        audit_entry = AuditDB(
            usuario_id=usuario_id,
            accion=accion,
            modulo=modulo,
            detalle=detalle,
            ip_address=ip_address,
            exitoso=exitoso,
            fecha=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error logging audit access: {e}")
        db.rollback()

# --- Placeholder for other services ---
# These would mirror the original pal.services logic but use SQLAlchemy ORM

def create_envio_programado(db: Session, envio_data: Dict[str, Any]) -> Optional[EnvioProgramadoDB]:
    """Creates a new scheduled shipment record."""
    try:
        # Basic validation of tipo_envio
        tipo_envio = envio_data.get('tipo_envio', 'DISPONIBILIDAD').upper()
        if tipo_envio not in ('DISPONIBILIDAD', 'ENTREGA'):
            tipo_envio = 'DISPONIBILIDAD'

        new_envio = EnvioProgramadoDB(
            numero_cliente=envio_data['numero_cliente'],
            fecha_programada=envio_data['fecha_programada'],
            tipo_envio=tipo_envio,
            codigo_producto=envio_data.get('codigo_producto'),
            estado='PENDIENTE'
        )
        db.add(new_envio)
        db.commit()
        db.refresh(new_envio)
        return new_envio
    except KeyError as e:
        logger.error(f"Missing key in envio_data: {e}")
        return None
    except SQLAlchemyError as e:
        logger.error(f"Database error creating envio_programado: {e}")
        db.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating envio_programado: {e}")
        return None

def get_pending_envios(db: Session, limit_date: datetime):
    """Fetches pending shipments scheduled before a certain date."""
    try:
        return db.query(EnvioProgramadoDB).filter(
            EnvioProgramadoDB.fecha_programada <= limit_date,
            EnvioProgramadoDB.estado == 'PENDIENTE'
        ).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching pending envios: {e}")
        return []

def update_envio_estado(db: Session, envio_id: int, estado: str):
    """Updates the status of a scheduled shipment."""
    envio_db = db.query(EnvioProgramadoDB).filter(EnvioProgramadoDB.id == envio_id).first()
    if envio_db:
        envio_db.estado = estado
        db.add(envio_db)
        try:
            db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error updating envio {envio_id} status to {estado}: {e}")
            db.rollback()
            return False
    return False

# Placeholder for other services (Stock, TRA, MBRP, SedeConfiguracion)
# These would involve implementing CRUD operations and specific logic for each service.
# For example, for SedeConfiguracion:

def get_active_sedes(db: Session):
    """Fetches all active sede configurations."""
    try:
        return db.query(SedeConfiguracionDB).filter(SedeConfiguracionDB.activa == True).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching active sedes: {e}")
        return []

# --- Helper Functions (if needed for complex queries/logic) ---
# These can be placed here or within specific service CRUD functions.

# Example: Function to get user roles and modules for response population
def get_user_extra_info(db: Session, user_id: int):
    """Fetches user's roles and modules for response."""
    user_db = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user_db:
        return {"roles": [], "modulos_habilitados": []}
    
    # Ensure relationships are loaded if not already
    # Example using options for eager loading if relationships are lazy loaded by default
    # user_db = db.query(UserDB).filter(UserDB.id == user_id).options(
    #     joinedload(UserDB.roles), joinedload(UserDB.modulos_habilitados)
    # ).first()
    
    roles = [role.id for role in user_db.roles] if hasattr(user_db, 'roles') else []
    modulos_habilitados = [mod.modulo for mod in user_db.modulos_habilitados] if hasattr(user_db, 'modulos_habilitados') else []
    
    return {"roles": roles, "modulos_habilitados": modulos_habilitados}

