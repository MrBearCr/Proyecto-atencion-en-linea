import unittest
from unittest.mock import MagicMock, patch
from pal.services.abastecimiento import AbastecimientoService

class TestRecepciones(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.service = AbastecimientoService(self.mock_db)

    def test_generar_numero_recepcion(self):
        # GIVEN: No hay recepciones previas
        self.mock_db.fetch_data.return_value = [[None]]
        
        # WHEN: Generamos numero
        num = self.service.generar_numero_recepcion()
        
        # THEN: Debe ser REC-000001
        self.assertEqual(num, "REC-000001")
        
        # GIVEN: Existe recepción 5
        self.mock_db.fetch_data.return_value = [[5]]
        
        # WHEN: Generamos numero
        num = self.service.generar_numero_recepcion()
        
        # THEN: Debe ser REC-000006
        self.assertEqual(num, "REC-000006")

    def test_registrar_recepcion_parcial(self):
        # GIVEN: Una transferencia TRS-1 con 2 items
        trs_id = 1
        items_recibidos = [
            {'sugerencia_id': 101, 'cantidad': 10}, # Item 1: Recibimos 10
            {'sugerencia_id': 102, 'cantidad': 0}   # Item 2: Nada
        ]
        user_id = 99
        
        # Mock para generar numero REC
        self.mock_db.fetch_data.side_effect = [
            [[0]], # Max ID recepciones (para generar REC-000001)
            [[500]], # ID de la nueva recepcion insertada (IDENT_CURRENT)
            [[1]] # Count pendientes (para estado global: queda 1 pendiente)
        ]

        # WHEN: Registramos recepción
        result = self.service.registrar_recepcion(trs_id, items_recibidos, user_id)

        # THEN:
        self.assertTrue(result['success'])
        self.assertEqual(result['numero_recepcion'], "REC-000001")
        self.assertEqual(result['estado_transferencia'], "recibida_parcial")
        
        # Verificar llamadas a DB
        # 1. Insert Maestro Recepcion
        self.mock_db.execute_query.assert_any_call(
            """
                INSERT INTO pal_recepciones_maestro 
                (numero_recepcion, transferencia_id, usuario_recibe, observaciones, fecha_recepcion)
                VALUES (?, ?, ?, ?, GETDATE())
            """, 
            ('REC-000001', trs_id, user_id, None)
        )
        
        # 2. Insert Detalle (Solo verificamos uno de los items)
        self.mock_db.execute_query.assert_any_call(
            """
                    INSERT INTO pal_recepciones_detalle (recepcion_id, sugerencia_id, cantidad_recibida)
                    VALUES (?, ?, ?)
                """,
            (500, 101, 10.0)
        )

        # 3. Update estado global
        self.mock_db.execute_query.assert_any_call(
            "UPDATE pal_transferencias_maestro SET estado = ? WHERE id = ?",
            ('recibida_parcial', trs_id)
        )

    def test_registrar_recepcion_total(self):
        # GIVEN: Transferencia que se completa
        trs_id = 1
        items_recibidos = [{'sugerencia_id': 101, 'cantidad': 50}]
        
        # Mock responses
        self.mock_db.fetch_data.side_effect = [
            [[10]], # Max ID rec
            [[510]], # New ID
            [[0]] # Count pendientes = 0 (Todo completo)
        ]

        # WHEN
        result = self.service.registrar_recepcion(trs_id, items_recibidos, 99)

        # THEN
        self.assertEqual(result['estado_transferencia'], "recibida_total")
        self.mock_db.execute_query.assert_any_call(
            "UPDATE pal_transferencias_maestro SET estado = ? WHERE id = ?",
            ('recibida_total', trs_id)
        )

if __name__ == '__main__':
    unittest.main()
