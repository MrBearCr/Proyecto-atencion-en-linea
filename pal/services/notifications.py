"""
Sistema de notificaciones centralizado para la aplicación PAL
Permite a diferentes módulos enviar notificaciones con distintos niveles de urgencia.

Persistencia (Migración 010):
  - Las notificaciones URGENT y WARNING se persisten en la tabla pal_notificaciones.
  - Cada notificación puede incluir un campo `modulo_ruta` que activa el botón
    "Tratar" en la UI, redirigiendo al usuario al módulo que requiere atención.

Política de retención:
  - INFO / SUCCESS  → 7 días
  - WARNING         → 30 días
  - URGENT          → 30 días (o hasta que sea marcada como tratada)
"""
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, List, Dict
import threading


class NotificationPriority(Enum):
    """Niveles de prioridad para las notificaciones"""
    URGENT  = "urgent"   # Rojo parpadeante (ej: quiebres de stock)
    WARNING = "warning"  # Naranja (ej: alertas importantes)
    INFO    = "info"     # Azul (ej: información general)
    SUCCESS = "success"  # Verde (ej: operación exitosa)


# Prioridades que se persisten en base de datos
PERSISTENT_PRIORITIES = {NotificationPriority.URGENT, NotificationPriority.WARNING}

# Política de retención en días por prioridad
RETENTION_DAYS: Dict[str, int] = {
    "urgent":  30,
    "warning": 30,
    "info":     7,
    "success":  7,
}


class Notification:
    """Representa una notificación individual"""

    def __init__(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        module: str,
        timestamp: Optional[datetime] = None,
        action_callback: Optional[Callable] = None,
        action_label: str = "Ver detalles",
        data: Optional[Dict] = None,
        # ── Nuevos campos para persistencia y botón "Tratar" ──────────────
        modulo_ruta: Optional[str] = None,
        accion_etiqueta: str = "Tratar",
        usuario: Optional[str] = None,
        notification_id: Optional[str] = None,
    ):
        self.id = notification_id or f"{module}_{datetime.now().timestamp()}"
        self.title = title
        self.message = message
        self.priority = priority
        self.module = module
        self.timestamp = timestamp or datetime.now()
        self.action_callback = action_callback
        self.action_label = action_label
        self.data = data or {}
        self.read = False
        self.dismissed = False
        self.treated = False

        # Ruta de navegación para el botón "Tratar"
        # Ejemplos: 'stock', 'tra', 'mbrp', 'clientes', 'sedes_config', None
        self.modulo_ruta: Optional[str] = modulo_ruta

        # Etiqueta del botón de acción principal (visible en el panel de notificaciones)
        self.accion_etiqueta: str = accion_etiqueta

        # Usuario que generó la notificación
        self.usuario: Optional[str] = usuario

        # Timestamps de auditoría
        self.f_leida: Optional[datetime] = None
        self.f_tratada: Optional[datetime] = None
        self.f_expiracion: Optional[datetime] = self._calcular_expiracion()

    # ------------------------------------------------------------------
    # Propiedades de conveniencia
    # ------------------------------------------------------------------

    @property
    def tiene_accion_tratar(self) -> bool:
        """True si la notificación tiene una ruta de módulo para el botón Tratar."""
        return self.modulo_ruta is not None

    @property
    def es_persistente(self) -> bool:
        """True si esta notificación debe guardarse en base de datos."""
        return self.priority in PERSISTENT_PRIORITIES

    # ------------------------------------------------------------------
    # Métodos de estado
    # ------------------------------------------------------------------

    def mark_as_read(self):
        """Marca la notificación como leída."""
        self.read = True
        self.f_leida = datetime.now()

    def dismiss(self):
        """Descarta la notificación."""
        self.dismissed = True

    def mark_as_treated(self, usuario: Optional[str] = None):
        """
        Marca la notificación como tratada.
        Se llama cuando el usuario hace clic en el botón "Tratar" y navega
        al módulo correspondiente.
        """
        self.treated = True
        self.f_tratada = datetime.now()
        if usuario:
            self.usuario_trato = usuario
        if not self.read:
            self.mark_as_read()

    def execute_action(self):
        """Ejecuta la acción asociada a la notificación (callback legacy)."""
        if self.action_callback:
            try:
                self.action_callback(self.data)
            except Exception as e:
                print(f"Error ejecutando acción de notificación: {e}")

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def to_db_dict(self) -> Dict:
        """
        Devuelve un diccionario listo para insertar/actualizar en la tabla
        pal_notificaciones (ver migración 010).
        """
        return {
            "id":              self.id,
            "titulo":          self.title,
            "mensaje":         self.message,
            "prioridad":       self.priority.value,
            "modulo":          self.module,
            "modulo_ruta":     self.modulo_ruta,
            "accion_etiqueta": self.accion_etiqueta,
            "datos_json":      json.dumps(self.data, ensure_ascii=False) if self.data else None,
            "leida":           1 if self.read else 0,
            "descartada":      1 if self.dismissed else 0,
            "tratada":         1 if self.treated else 0,
            "c_usuario":       self.usuario,
            "c_usuario_trato": getattr(self, "usuario_trato", None),
            "f_creacion":      self.timestamp,
            "f_leida":         self.f_leida,
            "f_tratada":       self.f_tratada,
            "f_expiracion":    self.f_expiracion,
        }

    @classmethod
    def from_db_row(cls, row: Dict) -> "Notification":
        """
        Reconstruye una Notification a partir de una fila de la BD
        (resultado de pyodbc fetchone/fetchall como dict).
        """
        priority_map = {p.value: p for p in NotificationPriority}
        priority = priority_map.get(row.get("prioridad", "info"), NotificationPriority.INFO)

        data = {}
        if row.get("datos_json"):
            try:
                data = json.loads(row["datos_json"])
            except (json.JSONDecodeError, TypeError):
                data = {}

        n = cls(
            title=row["titulo"],
            message=row["mensaje"],
            priority=priority,
            module=row["modulo"],
            timestamp=row.get("f_creacion"),
            action_label=row.get("accion_etiqueta", "Tratar"),
            data=data,
            modulo_ruta=row.get("modulo_ruta"),
            accion_etiqueta=row.get("accion_etiqueta", "Tratar"),
            usuario=row.get("c_usuario"),
            notification_id=row["id"],
        )
        n.read      = bool(row.get("leida", 0))
        n.dismissed = bool(row.get("descartada", 0))
        n.treated   = bool(row.get("tratada", 0))
        n.f_leida   = row.get("f_leida")
        n.f_tratada = row.get("f_tratada")
        n.f_expiracion = row.get("f_expiracion")
        if row.get("c_usuario_trato"):
            n.usuario_trato = row["c_usuario_trato"]
        return n

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _calcular_expiracion(self) -> Optional[datetime]:
        dias = RETENTION_DAYS.get(self.priority.value)
        if dias is None:
            return None
        return self.timestamp + timedelta(days=dias) if self.timestamp else \
               datetime.now() + timedelta(days=dias)


class NotificationManager:
    """
    Gestor centralizado de notificaciones.

    Responsabilidades:
      - Mantener la lista en memoria (thread-safe).
      - Persistir notificaciones URGENT/WARNING en BD a través de un
        `db_backend` opcional (ver interfaz NotificationDBBackend).
      - Notificar a observadores UI cuando cambia el estado.
    """

    def __init__(self, max_notifications: int = 100, db_backend=None):
        """
        Args:
            max_notifications: Límite de notificaciones en memoria.
            db_backend: Instancia de NotificationDBBackend (opcional).
                        Si se provee, las notificaciones persistentes se
                        guardan/cargan desde la BD.
        """
        self.notifications: List[Notification] = []
        self.max_notifications = max_notifications
        self._lock = threading.Lock()
        self._observers: List[Callable] = []
        self._db: Optional["NotificationDBBackend"] = db_backend

    # ------------------------------------------------------------------
    # API pública principal
    # ------------------------------------------------------------------

    def add_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        module: str,
        action_callback: Optional[Callable] = None,
        action_label: str = "Ver detalles",
        data: Optional[Dict] = None,
        # ── Nuevos parámetros ──────────────────────────────────────────
        modulo_ruta: Optional[str] = None,
        accion_etiqueta: str = "Tratar",
        usuario: Optional[str] = None,
    ) -> "Notification":
        """
        Añade una nueva notificación al sistema.

        Args:
            title:           Título de la notificación.
            message:         Mensaje descriptivo.
            priority:        Nivel de prioridad (URGENT, WARNING, INFO, SUCCESS).
            module:          Módulo que genera la notificación (STOCK, TRA, MBRP…).
            action_callback: Función a ejecutar cuando se hace clic en la notificación.
            action_label:    Texto del botón de acción legacy.
            data:            Datos adicionales asociados a la notificación.
            modulo_ruta:     Identificador de pestaña/módulo para el botón "Tratar".
                             Ejemplos: 'stock', 'tra', 'mbrp', 'clientes', 'sedes_config'.
                             Si es None, el botón "Tratar" no se muestra.
            accion_etiqueta: Texto del botón "Tratar" (por defecto "Tratar").
            usuario:         Usuario que genera la notificación.

        Returns:
            La notificación creada.
        """
        with self._lock:
            notification = Notification(
                title=title,
                message=message,
                priority=priority,
                module=module,
                action_callback=action_callback,
                action_label=action_label,
                data=data,
                modulo_ruta=modulo_ruta,
                accion_etiqueta=accion_etiqueta,
                usuario=usuario,
            )

            # Insertar al inicio (más recientes primero)
            self.notifications.insert(0, notification)

            # Limitar el número de notificaciones en memoria
            if len(self.notifications) > self.max_notifications:
                self.notifications = self.notifications[:self.max_notifications]

            # Persistir en BD si corresponde
            if notification.es_persistente and self._db is not None:
                try:
                    self._db.save(notification)
                except Exception as e:
                    print(f"[NotificationManager] Error persistiendo notificación: {e}")

            self._notify_observers()
            return notification

    def get_notifications(
        self,
        unread_only: bool = False,
        priority: Optional[NotificationPriority] = None,
        module: Optional[str] = None,
    ) -> List[Notification]:
        """
        Obtiene las notificaciones según los filtros especificados.

        Args:
            unread_only: Si True, solo devuelve notificaciones no leídas.
            priority:    Filtrar por prioridad específica.
            module:      Filtrar por módulo específico.

        Returns:
            Lista de notificaciones filtradas (excluye descartadas).
        """
        with self._lock:
            filtered = [n for n in self.notifications if not n.dismissed]

            if unread_only:
                filtered = [n for n in filtered if not n.read]

            if priority:
                filtered = [n for n in filtered if n.priority == priority]

            if module:
                filtered = [n for n in filtered if n.module == module]

            return filtered

    def get_unread_count(self) -> int:
        """Obtiene el número de notificaciones no leídas."""
        with self._lock:
            return sum(1 for n in self.notifications if not n.read and not n.dismissed)

    def get_urgent_count(self) -> int:
        """Obtiene el número de notificaciones urgentes no leídas."""
        with self._lock:
            return sum(
                1 for n in self.notifications
                if n.priority == NotificationPriority.URGENT and not n.read and not n.dismissed
            )

    def get_untreated_count(self) -> int:
        """
        Obtiene el número de notificaciones persistentes (URGENT/WARNING)
        que aún no han sido tratadas.
        """
        with self._lock:
            return sum(
                1 for n in self.notifications
                if n.es_persistente and not n.treated and not n.dismissed
            )

    def mark_all_as_read(self):
        """Marca todas las notificaciones como leídas."""
        with self._lock:
            for notification in self.notifications:
                if not notification.read:
                    notification.mark_as_read()
                    if notification.es_persistente and self._db is not None:
                        try:
                            self._db.update_status(notification)
                        except Exception as e:
                            print(f"[NotificationManager] Error actualizando estado en BD: {e}")
            self._notify_observers()

    def mark_as_treated(self, notification_id: str, usuario: Optional[str] = None):
        """
        Marca una notificación como tratada.
        Se llama cuando el usuario hace clic en el botón "Tratar".

        Args:
            notification_id: ID de la notificación.
            usuario:         Usuario que realizó la acción.
        """
        with self._lock:
            for notification in self.notifications:
                if notification.id == notification_id:
                    notification.mark_as_treated(usuario=usuario)
                    if notification.es_persistente and self._db is not None:
                        try:
                            self._db.update_status(notification)
                        except Exception as e:
                            print(f"[NotificationManager] Error actualizando tratada en BD: {e}")
                    break
            self._notify_observers()

    def clear_all(self):
        """Elimina todas las notificaciones de memoria (no afecta la BD)."""
        with self._lock:
            self.notifications.clear()
            self._notify_observers()

    def dismiss_notification(self, notification_id: str):
        """Descarta una notificación específica."""
        with self._lock:
            for notification in self.notifications:
                if notification.id == notification_id:
                    notification.dismiss()
                    if notification.es_persistente and self._db is not None:
                        try:
                            self._db.update_status(notification)
                        except Exception as e:
                            print(f"[NotificationManager] Error actualizando descartada en BD: {e}")
                    break
            self._notify_observers()

    # ------------------------------------------------------------------
    # Métodos de conveniencia (compatibilidad con app.py)
    # ------------------------------------------------------------------

    def show_error(
        self,
        title: str,
        message: str,
        module: str = "SISTEMA",
        modulo_ruta: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> "Notification":
        """Atajo para notificación URGENT."""
        return self.add_notification(
            title=title,
            message=message,
            priority=NotificationPriority.URGENT,
            module=module,
            modulo_ruta=modulo_ruta,
            accion_etiqueta="Tratar",
            usuario=usuario,
        )

    def show_warning(
        self,
        title: str,
        message: str,
        module: str = "SISTEMA",
        modulo_ruta: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> "Notification":
        """Atajo para notificación WARNING."""
        return self.add_notification(
            title=title,
            message=message,
            priority=NotificationPriority.WARNING,
            module=module,
            modulo_ruta=modulo_ruta,
            accion_etiqueta="Tratar",
            usuario=usuario,
        )

    def show_success(
        self,
        title: str,
        message: str,
        module: str = "SISTEMA",
        usuario: Optional[str] = None,
    ) -> "Notification":
        """Atajo para notificación SUCCESS."""
        return self.add_notification(
            title=title,
            message=message,
            priority=NotificationPriority.SUCCESS,
            module=module,
            usuario=usuario,
        )

    def show_info(
        self,
        title: str,
        message: str,
        module: str = "SISTEMA",
        modulo_ruta: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> "Notification":
        """Atajo para notificación INFO."""
        return self.add_notification(
            title=title,
            message=message,
            priority=NotificationPriority.INFO,
            module=module,
            modulo_ruta=modulo_ruta,
            usuario=usuario,
        )

    def show_banner(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.WARNING,
        module: str = "SISTEMA",
        modulo_ruta: Optional[str] = None,
        usuario: Optional[str] = None,
        # Parámetros extra ignorados para compatibilidad con llamadas legacy
        bg: Optional[str] = None,
        fg: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> "Notification":
        """
        Compatibilidad con el método show_banner() usado en tra.py y mbrp.py.
        Internamente crea una notificación con la prioridad indicada.
        """
        return self.add_notification(
            title=title,
            message=message,
            priority=priority,
            module=module,
            modulo_ruta=modulo_ruta,
            accion_etiqueta="Tratar",
            usuario=usuario,
        )

    def add(
        self,
        title: str,
        message: str,
        priority: str = "info",
        module: str = "SISTEMA",
        modulo_ruta: Optional[str] = None,
        accion_etiqueta: str = "Tratar",
        usuario: Optional[str] = None,
        datos: Optional[Dict] = None,
    ) -> "Notification":
        """
        Alias simplificado de add_notification() que acepta priority como string.
        Usado por mostrar_notificacion_quiebre() y otros módulos.

        Args:
            priority: String 'urgent' | 'warning' | 'info' | 'success'
        """
        priority_map = {p.value: p for p in NotificationPriority}
        prio_enum = priority_map.get(str(priority).lower(), NotificationPriority.INFO)
        return self.add_notification(
            title=title,
            message=message,
            priority=prio_enum,
            module=module,
            modulo_ruta=modulo_ruta,
            accion_etiqueta=accion_etiqueta,
            usuario=usuario,
            data=datos,
        )

    # ------------------------------------------------------------------
    # Persistencia — carga desde BD al iniciar
    # ------------------------------------------------------------------

    def load_from_db(self, usuario: Optional[str] = None):
        """
        Carga las notificaciones persistentes desde la BD al iniciar la sesión.
        Solo carga notificaciones no descartadas y no expiradas.

        Args:
            usuario: Si se provee, filtra por usuario.
        """
        if self._db is None:
            return
        try:
            rows = self._db.load_active(usuario=usuario)
            with self._lock:
                loaded = [Notification.from_db_row(r) for r in rows]
                # Mezclar con las que ya están en memoria (evitar duplicados por id)
                existing_ids = {n.id for n in self.notifications}
                for n in loaded:
                    if n.id not in existing_ids:
                        self.notifications.append(n)
                # Ordenar: más recientes primero
                self.notifications.sort(key=lambda n: n.timestamp, reverse=True)
            self._notify_observers()
        except Exception as e:
            print(f"[NotificationManager] Error cargando notificaciones desde BD: {e}")

    # ------------------------------------------------------------------
    # Observadores
    # ------------------------------------------------------------------

    def add_observer(self, callback: Callable):
        """
        Añade un observador que será notificado cuando cambien las notificaciones.

        Args:
            callback: Función a llamar cuando haya cambios.
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable):
        """Elimina un observador."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self):
        """Notifica a todos los observadores sobre cambios."""
        def notify_one(observer):
            try:
                observer()
            except Exception as e:
                print(f"[NotificationManager] Error notificando observador: {e}")
        
        # Ejecutar en el hilo de Tkinter de forma diferida para no bloquear la UI
        try:
            import tkinter as tk
            root = None
            # Intentar obtener la raíz de Tkinter de forma segura
            try:
                root = tk._default_root
            except AttributeError:
                pass
            
            if root is not None:
                for observer in self._observers:
                    root.after_idle(notify_one, observer)
                return
        except ImportError:
            pass
        
        # Fallback: ejecutar directamente si no hay Tkinter
        for observer in self._observers:
            notify_one(observer)


# ==============================================================================
# Interfaz de backend de persistencia
# ==============================================================================

class NotificationDBBackend:
    """
    Interfaz (protocolo) que debe implementar cualquier backend de persistencia
    para el NotificationManager.

    La implementación concreta debe conectarse a la tabla pal_notificaciones
    (creada por la migración 010) usando pyodbc o el conector disponible.

    Ejemplo de uso:
        backend = MiBackendPyodbc(conn)
        manager = NotificationManager(db_backend=backend)
        manager.load_from_db(usuario="admin")
    """

    def save(self, notification: Notification) -> None:
        """
        Inserta una nueva notificación en la BD.
        Si ya existe (mismo id), actualiza.
        """
        raise NotImplementedError

    def update_status(self, notification: Notification) -> None:
        """
        Actualiza los campos de estado (leida, descartada, tratada,
        c_usuario_trato, f_leida, f_tratada) de una notificación existente.
        """
        raise NotImplementedError

    def load_active(self, usuario: Optional[str] = None) -> List[Dict]:
        """
        Carga las notificaciones activas (no descartadas, no expiradas).
        Devuelve una lista de dicts con las columnas de pal_notificaciones.

        Args:
            usuario: Si se provee, filtra por c_usuario.
        """
        raise NotImplementedError

    def purge_expired(self) -> int:
        """
        Elimina las notificaciones expiradas según la política de retención.
        Devuelve el número de filas eliminadas.
        """
        raise NotImplementedError
