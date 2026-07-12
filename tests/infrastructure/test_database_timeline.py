import unittest
from unittest.mock import MagicMock
from pal.infrastructure.database import DatabaseManager

class TestDatabaseTimeline(unittest.TestCase):
    def setUp(self):
        # Creamos una instancia de DatabaseManager mockeando el credentials manager
        self.mock_cred_manager = MagicMock()
        self.db_manager = DatabaseManager(self.mock_cred_manager)
        # Mockear el método fetch_data para no interactuar realmente con SQL Server
        self.db_manager.fetch_data = MagicMock(return_value=[])

    def test_get_ventas_timeline_global_unidades(self):
        # GIVEN: Rango de fechas y modo ICH (global) sin monto (solo unidades)
        fecha_inicio = "01-07-2026"
        fecha_fin = "10-07-2026"
        sede_codigo = "ICH"

        # WHEN: Llamamos a la función
        self.db_manager.get_ventas_timeline(fecha_inicio, fecha_fin, sede_codigo, include_monto=False)

        # THEN: Se debe llamar a fetch_data con la query y los parámetros correctos
        self.db_manager.fetch_data.assert_called_once()
        args, kwargs = self.db_manager.fetch_data.call_args
        query = args[0]
        params = args[1]

        # Verificar que los parámetros de fecha se pasan correctamente
        self.assertEqual(params, [fecha_inicio, fecha_fin])
        # Al ser global (ICH), la consulta no debe incluir filtros por sede en el WHERE
        self.assertNotIn("AND i.c_Deposito LIKE ?", query)
        # Debe contener la lógica de agrupación y filtrado básico de TR_INVENTARIO
        self.assertIn("TR_INVENTARIO", query)
        self.assertIn("GROUP BY CONVERT(DATE, i.f_fecha)", query)

    def test_get_ventas_timeline_sede_monto(self):
        # GIVEN: Sede específica (01) e include_monto=True (dólares con JOIN a MA_PRODUCTOS)
        fecha_inicio = "01-07-2026"
        fecha_fin = "10-07-2026"
        sede_codigo = "01"

        # WHEN: Llamamos a la función
        self.db_manager.get_ventas_timeline(fecha_inicio, fecha_fin, sede_codigo, include_monto=True)

        # THEN: Se debe llamar a fetch_data con los parámetros que incluyan la sede
        self.db_manager.fetch_data.assert_called_once()
        args, kwargs = self.db_manager.fetch_data.call_args
        query = args[0]
        params = args[1]

        # Los parámetros deben incluir fecha_inicio, fecha_fin y la sede con comodín de búsqueda LIKE
        self.assertEqual(params, [fecha_inicio, fecha_fin, "01%"])
        self.assertIn("AND i.c_Deposito LIKE ?", query)
        # Al incluir monto, debe hacer JOIN con MA_PRODUCTOS y calcular los precios multiplicados
        self.assertIn("LEFT JOIN MA_PRODUCTOS p", query)
        self.assertIn("p.n_precio1", query)

if __name__ == '__main__':
    unittest.main()
