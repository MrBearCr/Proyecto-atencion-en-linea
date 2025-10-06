"""
Módulo de envíos programados para la aplicación PAL
"""
import threading
import time
from datetime import datetime
from pal.core.log import get_logger

logger = get_logger("ENVIOS")

class EnvioProgramado:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def programar_envio(self, numero_cliente, fecha):
        try:
            self.db_manager.execute_query(
                "INSERT INTO envios_programados (numero_cliente, fecha_programada, estado) VALUES (?, ?, 'PENDIENTE')",
                (numero_cliente, fecha)
            )
            return True
        except Exception as e:
            logger.error(f"Error programando envío: {str(e)}")
            return False

class ProgramadorEnvios:
    def __init__(self, db_manager, app):
        self.db_manager = db_manager
        self.app = app
        self.hilo = threading.Thread(target=self.verificar_envios, daemon=True)
        self.hilo.start()

    def verificar_envios(self):
        while True:
            try:
                if not self.db_manager.conn:
                    time.sleep(10)
                    continue

                ahora = datetime.now()
                pendientes = self.db_manager.fetch_data_threadsafe(
                    "SELECT id, numero_cliente FROM envios_programados "
                    "WHERE fecha_programada <= ? AND estado = 'PENDIENTE'",
                    (ahora,),
                    thread_name="envios"
                )
                self.app.log(f"Envíos pendientes encontrados: {len(pendientes)}", "DEBUG")

                for envio in pendientes:
                    id_envio, numero_cliente = envio
                    self.app.procesar_envio_programado(id_envio, numero_cliente)

                    self.verificar_recordatorios()

            except Exception as e:
                self.app.log(f"Error en programador: {str(e)}", "ERROR")
            time.sleep(60)


    def verificar_recordatorios(self):
        from datetime import timedelta
        
        ahora = datetime.now()
        recordatorios = self.db_manager.fetch_data_threadsafe(
        "SELECT id, numero_cliente, tipo_envio FROM envios_programados "
        "WHERE fecha_programada BETWEEN ? AND ? AND estado = 'PENDIENTE'",
        (ahora, ahora + timedelta(hours=24)),
        thread_name="envios")
    
        for id_envio, numero_cliente, tipo_envio in recordatorios:
            # Log via app to keep UI console consistent
            if hasattr(self, 'app') and hasattr(self.app, 'log'):
                self.app.log(f"Enviando recordatorio ({tipo_envio}) a {numero_cliente}", "INFO")
            else:
                logger.info(f"Enviando recordatorio ({tipo_envio}) a {numero_cliente}")
            self.enviar_mensaje_whatsapp(numero_cliente, tipo_envio=tipo_envio)
