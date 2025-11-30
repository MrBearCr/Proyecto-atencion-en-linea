"""Validación de licencia para la aplicación PAL.

La licencia se valida contra un CSV remoto con encabezados:
LicenseKey,ActivationDate,ExpirationDate,Version,Client

La app se considera válida si existe al menos una fila donde:
- Client == client_name (por ejemplo, "PALPY"), y
- ActivationDate <= hoy <= ExpirationDate (formato YYYY-MM-DD).
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import requests


class LicenseError(Exception):
    """Error de validación de licencia."""


@dataclass
class LicenseChecker:
    csv_url: str
    client_name: str = "PALPY"
    timeout_seconds: int = 10
    cache_file: str = "license_cache.json"

    def _parse_date(self, value: str) -> date:
        """Parsea fechas en formato YYYY-MM-DD.

        Lanza ValueError si el valor es inválido.
        """
        value = (value or "").strip()
        if not value:
            raise ValueError("Fecha vacía")
        return datetime.strptime(value, "%Y-%m-%d").date()

    def _has_valid_row(self, rows: list[dict[str, str]]) -> bool:
        """Devuelve True si hay al menos una fila válida para el cliente."""
        today = date.today()
        target_client = (self.client_name or "").strip().upper()

        for row in rows:
            try:
                client = (row.get("Client") or "").strip().upper()
                if client != target_client:
                    continue

                act_str = row.get("ActivationDate", "")
                exp_str = row.get("ExpirationDate", "")
                act = self._parse_date(act_str)
                exp = self._parse_date(exp_str)

                if act <= today <= exp:
                    return True
            except Exception:
                # Ignorar filas mal formadas y continuar con las siguientes
                continue
        return False

    def _load_cache(self) -> Optional[dict]:
        """Carga el cache local de licencia si existe."""
        try:
            p = Path(self.cache_file)
            if not p.exists():
                return None
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _cache_is_valid(self, allow_cached_days: int) -> bool:
        """Devuelve True si el cache indica una licencia válida y reciente.

        - allow_cached_days = 0 deshabilita el uso de cache.
        - Solo se acepta cache si:
          * ok == True,
          * client_name coincide, y
          * checked_at está dentro de los últimos allow_cached_days.
        """
        if allow_cached_days <= 0:
            return False

        cache = self._load_cache()
        if not cache or not cache.get("ok"):
            return False

        cached_client = (cache.get("client_name") or "").strip().upper()
        if cached_client != (self.client_name or "").strip().upper():
            return False

        try:
            last = datetime.strptime(cache.get("checked_at", ""), "%Y-%m-%d").date()
        except Exception:
            return False

        return (date.today() - last).days <= allow_cached_days

    def _save_cache_ok(self) -> None:
        """Guarda un cache simple indicando que la licencia fue válida hoy."""
        try:
            data = {
                "client_name": self.client_name,
                "ok": True,
                "checked_at": date.today().isoformat(),
            }
            Path(self.cache_file).write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            # El fallo al guardar el cache no debe romper la app
            pass

    def ensure_valid(self, allow_cached_days: int = 0) -> None:
        """Verifica que exista una licencia válida para el cliente.

        Flujo:
        - Si hay un cache OK más reciente que allow_cached_days, se acepta sin ir a red.
        - En caso contrario, se consulta el CSV remoto y, si es válido, se actualiza el cache.

        Lanza LicenseError si:
        - No se puede contactar el servidor de licencias (y no hay cache válido), o
        - No hay filas válidas (cliente distinto o fuera de rango de fechas).
        """
        # 1) Intentar usar cache reciente si está permitido
        if self._cache_is_valid(allow_cached_days):
            return None

        # 2) Validar contra el servidor remoto
        try:
            resp = requests.get(self.csv_url, timeout=self.timeout_seconds)
            resp.raise_for_status()
        except Exception as e:  # pragma: no cover - errores de red
            raise LicenseError(f"No se pudo conectar al servidor de licencias: {e}") from e

        lines = resp.text.splitlines()
        if not lines:
            raise LicenseError("El archivo de licencias está vacío.")

        reader = csv.DictReader(lines)
        rows = list(reader)
        if not rows:
            raise LicenseError("No se encontraron registros de licencia en el archivo remoto.")

        if not self._has_valid_row(rows):
            raise LicenseError(
                "No se encontró una licencia válida para este cliente o la licencia está vencida."
            )

        # Si llegamos aquí, la licencia es válida: actualizar cache y salir.
        self._save_cache_ok()
        return None
