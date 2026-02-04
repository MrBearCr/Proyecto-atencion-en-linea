from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base # Import Base from our database setup

# --- Database Models (for SQLAlchemy) ---
# These models define the structure of our database tables.
# They will be used by the ORM for mapping Python objects to database tables.

class UserDB(Base):
    __tablename__ = "pal_usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_ultimo_acceso = Column(DateTime, nullable=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship("RoleDB", secondary="pal_usuarios_roles", back_populates="usuarios", foreign_keys="UserRoleDB.usuario_id, UserRoleDB.rol_id")
    sesiones = relationship("SessionDB", back_populates="usuario")
    permisos_directos = relationship("UserPermissionDB", back_populates="usuario", foreign_keys="UserPermissionDB.usuario_id")
    modulos_habilitados = relationship("UserModuleDB", back_populates="usuario", foreign_keys="UserModuleDB.usuario_id")
    auditorias = relationship("AuditDB", back_populates="usuario")
    roles_asignados_rel = relationship("UserRoleDB", back_populates="usuario", foreign_keys="UserRoleDB.usuario_id", overlaps="roles")

class RoleDB(Base):
    __tablename__ = "pal_roles"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    es_sistema = Column(Boolean, default=False)

    # Relationships
    usuarios = relationship("UserDB", secondary="pal_usuarios_roles", back_populates="roles", foreign_keys="UserRoleDB.rol_id, UserRoleDB.usuario_id", overlaps="roles_asignados_rel")
    usuarios_asignados_rel = relationship("UserRoleDB", back_populates="rol", overlaps="roles,usuarios")
    permisos_asignados = relationship("RolePermissionDB", back_populates="rol")
    usuarios_asignados_rel = relationship("UserRoleDB", back_populates="rol", overlaps="roles,usuarios")

class PermissionDB(Base):
    __tablename__ = "pal_permisos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    modulo = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=True)

    # Relationships
    roles_que_lo_usan = relationship("RolePermissionDB", back_populates="permiso")
    usuarios_que_lo_usan = relationship("UserPermissionDB", back_populates="permiso")

class UserRoleDB(Base):
    __tablename__ = "pal_usuarios_roles"
    usuario_id = Column(Integer, ForeignKey("pal_usuarios.id"), primary_key=True)
    rol_id = Column(Integer, ForeignKey("pal_roles.id"), primary_key=True)
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)
    asignado_por = Column(Integer, ForeignKey("pal_usuarios.id"), nullable=True)

    usuario = relationship("UserDB", back_populates="roles_asignados_rel", foreign_keys="UserRoleDB.usuario_id", overlaps="roles,usuarios") # Added relationship for reverse lookup if needed
    rol = relationship("RoleDB", back_populates="usuarios_asignados_rel", overlaps="roles,usuarios") # Added relationship for reverse lookup if needed

class RolePermissionDB(Base):
    __tablename__ = "pal_roles_permisos"
    rol_id = Column(Integer, ForeignKey("pal_roles.id"), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("pal_permisos.id"), primary_key=True)

    rol = relationship("RoleDB", back_populates="permisos_asignados")
    permiso = relationship("PermissionDB", back_populates="roles_que_lo_usan")

class UserPermissionDB(Base):
    __tablename__ = "pal_usuarios_permisos"
    usuario_id = Column(Integer, ForeignKey("pal_usuarios.id"), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("pal_permisos.id"), primary_key=True)
    concedido = Column(Boolean, nullable=False, default=True)
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)
    asignado_por = Column(Integer, ForeignKey("pal_usuarios.id"), nullable=True)

    usuario = relationship("UserDB", back_populates="permisos_directos", foreign_keys="UserPermissionDB.usuario_id")
    permiso = relationship("PermissionDB", back_populates="usuarios_que_lo_usan")

class UserModuleDB(Base):
    __tablename__ = "pal_usuarios_modulos"
    usuario_id = Column(Integer, ForeignKey("pal_usuarios.id"), primary_key=True)
    modulo = Column(String(50), primary_key=True) # e.g., 'TRA', 'MBRP', 'STOCK'
    habilitado = Column(Boolean, nullable=False, default=True)
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)
    asignado_por = Column(Integer, ForeignKey("pal_usuarios.id"), nullable=True)

    usuario = relationship("UserDB", back_populates="modulos_habilitados", foreign_keys="UserModuleDB.usuario_id")

class AuditDB(Base):
    __tablename__ = "pal_auditoria_accesos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("pal_usuarios.id"), nullable=True)
    accion = Column(String(100), nullable=False) # e.g., 'LOGIN', 'LOGOUT', 'LOGIN_FAILED'
    modulo = Column(String(50), nullable=True) # e.g., 'ADMIN'
    detalle = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    exitoso = Column(Boolean, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("UserDB", back_populates="auditorias")

class SessionDB(Base):
    __tablename__ = "pal_sesiones"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("pal_usuarios.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, nullable=False)
    activa = Column(Boolean, default=True)

    usuario = relationship("UserDB", back_populates="sesiones")

class ClienteDB(Base):
    __tablename__ = "pal_clientes" # Renamed from 'clientes'
    id = Column(Integer, primary_key=True, index=True)
    numero_cliente = Column(String(50), nullable=False)
    C_CODIGO = Column(String(15), nullable=False) # Assuming this maps to C_CODIGO from original

    # Indexes are typically defined separately or via __table_args__
    # Assuming these are handled by the migration/DDL scripts

class EnvioProgramadoDB(Base):
    __tablename__ = "pal_envios_programados" # Renamed from 'envios_programados'
    id = Column(Integer, primary_key=True, index=True)
    numero_cliente = Column(String(50), nullable=False)
    fecha_programada = Column(DateTime, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(20), default='PENDIENTE') # e.g., 'PENDIENTE', 'ENVIADO', 'ERROR'
    tipo_envio = Column(String(20), nullable=False) # e.g., 'DISPONIBILIDAD', 'ENTREGA'
    codigo_producto = Column(String(15), nullable=True)

    # Constraints can be added via __table_args__ if needed
    # __table_args__ = (UniqueConstraint('numero_cliente', 'fecha_programada', 'tipo_envio', 'codigo_producto', name='uq_envio_programado'),)

class SedeConfiguracionDB(Base):
    __tablename__ = "pal_sedes_configuracion"
    id = Column(Integer, primary_key=True, index=True)
    nombre_sede = Column(String(100), nullable=False)
    ip_servidor = Column(String(100), nullable=False)
    nombre_bd = Column(String(100), nullable=False)
    usuario_bd = Column(String(100), nullable=True)
    password_bd_enc = Column(String(255), nullable=True) # Encrypted password
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow)


# --- Legacy DB Models (Mapped to existing tables) ---

class MaProductosDB(Base):
    __tablename__ = "MA_PRODUCTOS"
    C_CODIGO = Column(String(15), primary_key=True)
    C_DESCRI = Column(String(255))
    cu_descripcion_corta = Column(String(255))
    C_DEPARTAMENTO = Column(String(50))
    C_GRUPO = Column(String(50))
    C_SUBGRUPO = Column(String(50))
    n_precio1 = Column(Float)
    n_impuesto1 = Column(Float)
    n_costoact = Column(Float)
    
class MaDepoProdDB(Base):
    __tablename__ = "MA_DEPOPROD"
    c_codarticulo = Column(String(15), ForeignKey("MA_PRODUCTOS.C_CODIGO"), primary_key=True)
    c_coddeposito = Column(String(10), primary_key=True)
    n_cantidad = Column(Float)

    producto = relationship("MaProductosDB")

class TrInventarioDB(Base):
    __tablename__ = "TR_INVENTARIO"
    # Assuming a composite PK or unique ID exists, otherwise mapping might be tricky for pure ORM
    # However, for reading, we can map minimal fields. rowid/identity usually exists but not specified in legacy code.
    # We'll map what we use. If no PK, SQLAlchemy needs a workaround, usually mapping a candidate key.
    # Legacy schema is often messy. We'll assume composite PK for now or just generic mapping for read-only.
    # Given the usage in legacy app is raw SQL, we might primarily use raw SQL in CRUD too, but models help for type hints and potential ORM usage.
    # For now, let's define it but be aware we might rely on Core for complex queries.
    
    # We'll use a dummy PK for mapping purposes if real one isn't known, or use known columns.
    # Valid guess: c_uniq (often used in mixed schemas) or composite.
    c_Documento = Column(String(20), primary_key=True) # Guessing a PK part
    c_Concepto = Column(String(10), primary_key=True)
    c_Codarticulo = Column(String(15), ForeignKey("MA_PRODUCTOS.C_CODIGO"))
    n_Cantidad = Column(Float)
    f_fecha = Column(DateTime)
    c_Deposito = Column(String(10))

# --- New Stock DB Model ---
class StockDB(Base):
    __tablename__ = "pal_stock_alerts" # Example table name
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, index=True) # Product code
    descripcion = Column(String(255), nullable=False) # Product description
    stock = Column(Integer, nullable=False) # Current stock level
    nivel = Column(String(20), nullable=False) # e.g., 'CRÍTICA', 'MEDIA', 'LEVE'
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow) # Timestamp of last update


# --- Pydantic Models (for API Request/Response) ---
# These models are used for data validation and serialization in API endpoints.
# They define the structure of JSON payloads.

class UserCreate(BaseModel):
    username: str = Field(..., example="john_doe")
    password: str
    nombre_completo: str = Field(..., example="John Doe")
    email: Optional[str] = Field(None, example="john.doe@example.com")
    roles_ids: Optional[List[int]] = Field(None, description="List of role IDs to assign")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, example="john_doe_updated")
    nombre_completo: Optional[str] = Field(None, example="John Doe Updated")
    email: Optional[str] = Field(None, example="john.doe.updated@example.com")
    activo: Optional[bool] = Field(None)

class UserResponse(BaseModel):
    id: int
    username: str
    nombre_completo: str
    email: Optional[str]
    activo: bool
    fecha_creacion: datetime
    fecha_ultimo_acceso: Optional[datetime]
    intentos_fallidos: int
    bloqueado_hasta: Optional[datetime]
    roles: List[int] = [] # List of role IDs
    modulos_habilitados: List[str] = [] # List of enabled module codes

class RoleCreate(BaseModel):
    nombre: str = Field(..., example="Administrador")
    descripcion: Optional[str] = Field(None, example="Acceso total al sistema")
    permisos_codigos: Optional[List[str]] = Field(None, description="List of permission codes (e.g., 'TRA.ver')")

class RoleUpdate(BaseModel):
    nombre: Optional[str] = Field(None, example="Administrador")
    descripcion: Optional[str] = Field(None, example="Acceso total al sistema")

class RoleResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    es_sistema: bool
    # permissions: List[str] # Potentially include permission codes if needed

class PermissionResponse(BaseModel):
    id: int
    codigo: str
    modulo: str
    descripcion: Optional[str]

class LoginRequest(BaseModel):
    username: str
    password: str
    ip_address: Optional[str] = Field(None, description="IP address of the client making the request")

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = Field(None, description="Authentication token if login is successful")
    user: Optional[dict] = Field(None, description="Basic user info (id, username) if successful")
    message: str

class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nuevo: str

class ResetPasswordRequest(BaseModel):
    password_temporal: str

class SessionVerifyResponse(BaseModel):
    id: int
    username: str

class AuditAccessRequest(BaseModel):
    accion: str
    modulo: Optional[str]
    detalle: Optional[str]
    ip_address: Optional[str] = Field(None)
    exitoso: bool

# --- Models for Services ---

class EnvioProgramadoCreate(BaseModel):
    numero_cliente: str
    fecha_programada: datetime
    tipo_envio: str = Field("DISPONIBILIDAD", description="Type of shipment, e.g., 'DISPONIBILIDAD', 'ENTREGA'")
    codigo_producto: Optional[str] = Field(None)

class StockAlert(BaseModel):
    codigo: str
    descripcion: str
    stock: int
    nivel: str # e.g., 'CRÍTICA', 'MEDIA', 'LEVE'
    # Add locations if needed in response, e.g., existence per location.

class JerarquiaProducto(BaseModel):
    departamento: Optional[str] = None
    grupo: Optional[str] = None
    subgrupo: Optional[str] = None

class ProductoVentas(BaseModel):
    codigo: str
    descripcion: str
    departamento: Optional[str] = None
    grupo: Optional[str] = None
    subgrupo: Optional[str] = None
    ventas_netas: float = Field(0.0)
    # Classification and other dynamic fields will be added later
    rotacion: Optional[str] = None # e.g., 'ALTA', 'MEDIA', 'BAJA', 'SIN MOVIMIENTO'
    porcentaje_representacion: Optional[float] = None

# Helper models for Pydantic, not directly mapped to DB tables
# Pydantic models for Pydantic models (BaseModel)
class UserBase(BaseModel):
    username: str
    nombre_completo: str
    email: Optional[str] = None
    activo: bool = True

class UserCreateDB(UserBase):
    password: str

class UserUpdateDB(BaseModel):
    username: Optional[str] = None
    nombre_completo: Optional[str] = None
    email: Optional[str] = None
    activo: Optional[bool] = None
    # Password changes are handled separately due to hashing

class RoleBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    es_sistema: bool = False

class RoleCreateDB(RoleBase):
    pass

class RoleUpdateDB(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    es_sistema: Optional[bool] = None

class PermissionBase(BaseModel):
    codigo: str
    modulo: str
    descripcion: Optional[str] = None

class AuditAccessBase(BaseModel):
    accion: str
    modulo: Optional[str] = None
    detalle: Optional[str] = None
    ip_address: Optional[str] = None
    exitoso: bool

class SessionBase(BaseModel):
    usuario_id: int
    token: str
    ip_address: Optional[str] = None
    fecha_inicio: datetime
    fecha_expiracion: datetime
    activa: bool

class ClienteBase(BaseModel):
    numero_cliente: str
    C_CODIGO: str

class EnvioProgramadoBase(BaseModel):
    numero_cliente: str
    fecha_programada: datetime
    estado: str = 'PENDIENTE'
    tipo_envio: str
    codigo_producto: Optional[str] = None

class SedeConfiguracionBase(BaseModel):
    nombre_sede: str
    ip_servidor: str
    nombre_bd: str
    usuario_bd: Optional[str] = None
    password_bd_enc: Optional[str] = None # Encrypted password
    activa: bool = True

class SedeConfiguracionCreate(SedeConfiguracionBase):
    # Password will be encrypted before storing
    pass

class SedeConfiguracionUpdate(SedeConfiguracionBase):
    # Password will be encrypted before storing
    pass

# --- Pydantic models for API request/response ---

# User related
class UserAuth(BaseModel):
    username: str
    password: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreateRequest(UserBase): # For API creation, password required
    password: str

class UserUpdateRequest(UserUpdate): # Use UserUpdate here, and add roles
    roles: Optional[List[int]] = None

class RoleCreateRequest(RoleBase):
    permisos_codigos: Optional[List[str]] = None

class PermissionRequest(BaseModel): # For assigning permissions directly to user
    permiso_codigo: str
    concedido: bool = True

class UserPermissionsRequest(BaseModel):
    permisos: List[PermissionRequest]

class RolePermissionsRequest(BaseModel):
    permisos_codigos: List[str]

class UserModuleRequest(BaseModel):
    modulo: str
    habilitado: bool = True

class UserModulesRequest(BaseModel):
    modulos: List[UserModuleRequest]

class LoginRequestAPI(LoginRequest): # Specific API request model for login
    pass

class LoginResponseAPI(LoginResponse): # Specific API response model for login
    pass

class ChangePasswordRequestAPI(ChangePasswordRequest):
    pass

class ResetPasswordRequestAPI(ResetPasswordRequest):
    pass

# Session related
class SessionCreate(SessionBase):
    pass

class SessionResponse(SessionBase):
    id: int
    usuario: dict # Simplified user info: {'id': int, 'username': str}

# Audit related
class AuditAccessCreate(AuditAccessBase):
    usuario_id: Optional[int] = None

# Envio Programado related
class EnvioProgramadoCreateAPI(EnvioProgramadoCreate):
    pass

class EnvioProgramadoResponse(EnvioProgramadoCreate): # Extend Base for response
    id: int
    fecha_creacion: datetime
    estado: str

# Stock related
class StockAlertResponse(StockAlert):
    # Inherits code, description, stock, nivel
    pass

class StockAlertDetail(StockAlertResponse): # For detailed view, add more fields if needed
    pass

# TRA related
class ProductoVentasResponse(ProductoVentas):
    # Inherits code, description, hierarchy, net sales, rotation, rep. %, etc.
    pass

# MBRP related
class ProductoMBRP(ProductoVentas): # Inherit from ProductoVentas as MBRP builds on TRA data
    # Add MBRP specific fields if needed, e.g., monto_comprado, diferencia, margen
    monto_vendido: float = Field(0.0)
    monto_comprado: float = Field(0.0)
    diferencia: float = Field(0.0)
    margen_pct: float = Field(0.0)
    dias_sin_venta: int = Field(0)
    im_movilidad: float = Field(0.0)

class MBRPReportSummary(BaseModel):
    total_productos: int
    sin_movimiento: int
    baja_rotacion: int
    media_rotacion: int
    alta_rotacion: int
    productos_criticos: int
    porcentaje_baja_rotacion: float
    # detalle_criticos will be a list of ProductMBRP-like objects

# SedeConfiguracion related
class SedeConfiguracionResponse(SedeConfiguracionBase):
    id: int
    fecha_creacion: datetime
    fecha_modificacion: datetime

# --- Helper function for Pydantic models ---
# This function would be used to convert SQLAlchemy DB objects to Pydantic models.
# It's crucial for returning data from API endpoints in a structured, validated way.
def db_to_pydantic(db_obj, pydantic_model):
    """Converts a SQLAlchemy DB object to a Pydantic model."""
    if not db_obj:
        return None
    
    try:
        # Get attributes from DB object that match Pydantic model fields
        # This assumes Pydantic field names match SQLAlchemy column names or are aliased.
        # For more complex mappings, a dedicated library like `ormodel` or manual mapping is needed.
        
        # Simple manual mapping for demonstration:
        if isinstance(db_obj, UserDB):
            return UserResponse(
                id=db_obj.id,
                username=db_obj.username,
                nombre_completo=db_obj.nombre_completo,
                email=db_obj.email,
                activo=db_obj.activo,
                fecha_creacion=db_obj.fecha_creacion,
                fecha_ultimo_acceso=db_obj.fecha_ultimo_acceso,
                intentos_fallidos=db_obj.intentos_fallidos,
                bloqueado_hasta=db_obj.bloqueado_hasta,
                roles=[role.id for role in db_obj.roles], # List of role IDs
                modulos_habilitados=[mod.modulo for mod in db_obj.modulos_habilitados]
            )
        elif isinstance(db_obj, RoleDB):
            return RoleResponse(
                id=db_obj.id,
                nombre=db_obj.nombre,
                descripcion=db_obj.descripcion,
                es_sistema=db_obj.es_sistema
            )
        elif isinstance(db_obj, PermissionDB):
            return PermissionResponse(
                id=db_obj.id,
                codigo=db_obj.codigo,
                modulo=db_obj.modulo,
                descripcion=db_obj.descripcion
            )
        elif isinstance(db_obj, SessionDB):
            return SessionResponse(
                id=db_obj.id,
                usuario_id=db_obj.usuario_id,
                token=db_obj.token,
                ip_address=db_obj.ip_address,
                fecha_inicio=db_obj.fecha_inicio,
                fecha_expiracion=db_obj.fecha_expiracion,
                activa=db_obj.activa,
                usuario={'id': db_obj.usuario.id, 'username': db_obj.usuario.username} if db_obj.usuario else None
            )
        elif isinstance(db_obj, EnvioProgramadoDB):
            return EnvioProgramadoResponse(
                id=db_obj.id,
                numero_cliente=db_obj.numero_cliente,
                fecha_programada=db_obj.fecha_programada,
                estado=db_obj.estado,
                tipo_envio=db_obj.tipo_envio,
                codigo_producto=db_obj.codigo_producto,
                fecha_creacion=db_obj.fecha_creacion
            )
        elif isinstance(db_obj, SedeConfiguracionDB):
            return SedeConfiguracionResponse(
                id=db_obj.id,
                nombre_sede=db_obj.nombre_sede,
                ip_servidor=db_obj.ip_servidor,
                nombre_bd=db_obj.nombre_bd,
                usuario_bd=db_obj.usuario_bd,
                password_bd_enc=db_obj.password_bd_enc,
                activa=db_obj.activa,
                fecha_creacion=db_obj.fecha_creacion,
                fecha_modificacion=db_obj.fecha_modificacion
            )
        # Add more mappings for other DB models as needed
        
        # Fallback for generic BaseModel mapping if field names match exactly
        # This is less robust and prone to errors if names don't align perfectly.
        # model_fields = pydantic_model.model_fields
        # data = {field: getattr(db_obj, field, None) for field in model_fields}
        # return pydantic_model(**data)
        
        # If no specific mapping found, attempt generic mapping (use with caution)
        # Note: This might require db_obj to be a dict or have attributes matching pydantic fields.
        # For SQLAlchemy ORM objects, direct attribute access is more common.
        # Example for a simple model:
        # if isinstance(db_obj, SomeGenericDBModel):
        #     return pydantic_model(field1=db_obj.field1, field2=db_obj.field2)

    except Exception as e:
        logger.error(f"Error converting DB object to Pydantic model {pydantic_model.__name__}: {e}")
        return None
    
    return None # Return None if conversion is not supported or fails
