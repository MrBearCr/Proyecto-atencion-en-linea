"""
Módulo de caché para descripciones de productos
"""
import time

class CacheDescripciones:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl

    def obtener(self, codigo):
        item = self.cache.get(codigo)
        if item and (time.time() - item['timestamp']) < self.ttl:
            return item['descripcion']
        return None

    def guardar(self, codigo, descripcion):
        self.cache[codigo] = {
            'descripcion': descripcion,
            'timestamp': time.time()
        }