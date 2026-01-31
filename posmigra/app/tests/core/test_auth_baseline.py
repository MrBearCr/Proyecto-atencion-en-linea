"""
Baseline mínimo para `auth`, apuntando todavía al módulo existente `pal.core.auth`.

La idea es validar el comportamiento actual antes de comenzar a desacoplar
y migrar a la nueva API. Estos tests podrán evolucionar a pruebas de API
en la Fase 2, según se describe en `TEST_PLAN.md`.
"""

import pytest

from pal.core import auth


@pytest.mark.skip(reason="Ejemplo inicial: ajustar con casos reales antes de usar en CI.")
def test_login_successful_baseline():
    """
    Ejemplo de stub de prueba:
    - Rellena con credenciales y expectativas reales según el entorno de pruebas.
    """
    # TODO: implementar con datos de prueba reales o mocks.
    assert hasattr(auth, "login")


