import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Asumimos que el path del proyecto está configurado para que se puedan importar los módulos de `pal`
from pal.core.auth import AuthManager
from pal.infrastructure.database import DatabaseManager

# --- Fixtures ---

@pytest.fixture
def mock_db_manager():
    """Crea un mock del DatabaseManager."""
    return Mock(spec=DatabaseManager)

@pytest.fixture
def auth_manager(mock_db_manager):
    """Crea una instancia de AuthManager con un DatabaseManager mockeado."""
    return AuthManager(mock_db_manager)

# --- Datos de Prueba ---
CORRECT_PASSWORD = "password123"

# --- Casos de Prueba Implementados ---

@patch('pal.core.auth.AuthManager._now')
def test_login_successful(mock_now, auth_manager, mock_db_manager):
    """
    Prueba un inicio de sesión exitoso.
    - GIVEN: Un usuario y contraseña correctos.
    - WHEN: Se llama a login.
    - THEN: El login es exitoso y se crea una sesión.
    """
    # Configurar tiempo y hash
    ahora = datetime(2024, 1, 1, 12, 0, 0)
    mock_now.return_value = ahora
    
    # Generar el hash usando el método interno de la clase, para asegurar consistencia
    hashed_password = auth_manager._hash(CORRECT_PASSWORD)

    user_data_active = [
        (1, hashed_password, True, 0, None)
    ]

    # Configurar mocks
    mock_db_manager.fetch_data.return_value = user_data_active
    
    # Ejecutar
    result = auth_manager.login("testuser", CORRECT_PASSWORD)

    # Verificar
    assert result["success"] is True, f"Login falló inesperadamente con mensaje: {result.get('message')}"
    assert "token" in result
    assert result["user"]["username"] == "testuser"
    
    # Verificar que se resetean los intentos fallidos
    mock_db_manager.execute_query.assert_any_call(
        "UPDATE pal_usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL, fecha_ultimo_acceso = ? WHERE id = ?",
        (ahora, 1)
    )
    # Verificar que se crea la sesión
    expiracion_esperada = ahora + timedelta(minutes=auth_manager.duracion_sesion_min)
    mock_db_manager.execute_query.assert_any_call(
        """
            INSERT INTO pal_sesiones (usuario_id, token, ip_address, fecha_inicio, fecha_expiracion, activa)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
        (1, result["token"], None, ahora, expiracion_esperada)
    )

def test_login_failed_wrong_password(auth_manager, mock_db_manager):
    """
    Prueba un inicio de sesión con contraseña incorrecta.
    - GIVEN: Un usuario válido y una contraseña incorrecta.
    - WHEN: Se llama a login.
    - THEN: El login falla y se incrementan los intentos fallidos.
    """
    # Configurar mocks
    hashed_password = auth_manager._hash(CORRECT_PASSWORD)
    user_data_active = [(1, hashed_password, True, 0, None)]
    mock_db_manager.fetch_data.return_value = user_data_active
    
    # Ejecutar
    result = auth_manager.login("testuser", "wrongpassword")

    # Verificar
    assert result["success"] is False
    assert result["message"] == "Usuario o contraseña inválidos"
    
    # Verificar que se actualizan los intentos fallidos
    mock_db_manager.execute_query.assert_any_call(
        "UPDATE pal_usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
        (1, None, 1) # nuevos_intentos = 1, sin bloqueo
    )

def test_login_failed_user_not_found(auth_manager, mock_db_manager):
    """
    Prueba un inicio de sesión con un usuario que no existe.
    - GIVEN: Un nombre de usuario que no está en la base de datos.
    - WHEN: Se llama a login.
    - THEN: El login falla.
    """
    # Configurar mocks
    mock_db_manager.fetch_data.return_value = [] # No se encuentra el usuario
    
    # Ejecutar
    result = auth_manager.login("nonexistent_user", "anypassword")

    # Verificar
    assert result["success"] is False
    assert result["message"] == "Usuario o contraseña inválidos"
    
    # Verificar que se registra la auditoría de usuario inexistente
    mock_db_manager.execute_query.assert_called_once_with(
        """
                    INSERT INTO pal_auditoria_accesos (usuario_id, accion, modulo, detalle, ip_address, exitoso, fecha)
                    VALUES (NULL, 'LOGIN_FAILED', 'ADMIN', ?, ?, 0, GETDATE())
                    """,
        ("Usuario no existe: nonexistent_user", None)
    )

@patch('pal.core.auth.AuthManager._now')
def test_login_failed_user_is_blocked(mock_now, auth_manager, mock_db_manager):
    """
    Prueba que un usuario bloqueado no puede iniciar sesión.
    - GIVEN: Un usuario cuyo 'bloqueado_hasta' es en el futuro.
    - WHEN: Se llama a login.
    - THEN: El login falla con un mensaje de usuario bloqueado.
    """
    # Configurar tiempo
    ahora = datetime(2024, 1, 1, 12, 0, 0)
    bloqueado_hasta = ahora + timedelta(minutes=15)
    mock_now.return_value = ahora
    
    hashed_password = auth_manager._hash(CORRECT_PASSWORD)
    user_data_blocked = [
        (1, hashed_password, True, 5, bloqueado_hasta)
    ]
    
    # Configurar mocks
    mock_db_manager.fetch_data.return_value = user_data_blocked
    
    # Ejecutar
    result = auth_manager.login("testuser", CORRECT_PASSWORD)

    # Verificar
    assert result["success"] is False
    assert result["message"] == "Usuario bloqueado temporalmente"

def test_login_failed_user_is_inactive(auth_manager, mock_db_manager):
    """
    Prueba que un usuario inactivo no puede iniciar sesión.
    - GIVEN: Un usuario con la bandera 'activo' en False.
    - WHEN: Se llama a login.
    - THEN: El login falla con un mensaje de usuario inactivo.
    """
    hashed_password = auth_manager._hash(CORRECT_PASSWORD)
    user_data_inactive = [
        (1, hashed_password, False, 0, None)
    ]
    mock_db_manager.fetch_data.return_value = user_data_inactive

    result = auth_manager.login("testuser", CORRECT_PASSWORD)

    assert result["success"] is False
    assert result["message"] == "Usuario inactivo"

@patch('pal.core.auth.AuthManager._now')
def test_user_gets_blocked_after_max_attempts(mock_now, auth_manager, mock_db_manager):
    """
    Prueba que un usuario se bloquea después del número máximo de intentos fallidos.
    - GIVEN: Un usuario con (max_intentos - 1) intentos fallidos.
    - WHEN: Se realiza un nuevo intento fallido.
    - THEN: El usuario queda bloqueado.
    """
    # Configurar tiempo
    ahora = datetime(2024, 1, 1, 12, 0, 0)
    mock_now.return_value = ahora
    bloqueo_esperado = ahora + timedelta(minutes=auth_manager.tiempo_bloqueo_min)

    hashed_password = auth_manager._hash(CORRECT_PASSWORD)
    user_data_pre_lock = [
        (1, hashed_password, True, auth_manager.max_intentos - 1, None)
    ]
    mock_db_manager.fetch_data.return_value = user_data_pre_lock
    
    # Ejecutar (el 5to intento fallido)
    auth_manager.login("testuser", "wrongpassword")
    
    # Verificar que se bloquea al usuario
    # El primer `any_call` es para la auditoría, el segundo para el UPDATE
    update_call = mock_db_manager.execute_query.call_args_list[0]
    
    assert update_call.args[0] == "UPDATE pal_usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?"
    assert update_call.args[1][0] == 0  # intentos se resetean a 0
    assert update_call.args[1][1] == bloqueo_esperado # se establece fecha de bloqueo
    assert update_call.args[1][2] == 1 # para el usuario con id 1
