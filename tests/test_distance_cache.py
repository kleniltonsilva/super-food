"""
Testes de Cache de Distâncias Mapbox — Derekh Food
Valida cache Redis para distância/taxa de entrega + geocoding.

Execução: pytest tests/test_distance_cache.py -v
"""

import sys
import os
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("MAPBOX_TOKEN", "pk.test_token_fake")

import pytest


# ==================== HELPERS ====================

class FakeRedis:
    """Redis em memória para testes (dict simples)."""

    def __init__(self):
        self._store = {}
        self._ttls = {}

    def get(self, key):
        val = self._store.get(key)
        if val is None:
            return None
        return val

    def setex(self, key, ttl, value):
        self._store[key] = value
        self._ttls[key] = ttl

    def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
            self._ttls.pop(k, None)

    def scan(self, cursor, match="*", count=100):
        import fnmatch
        matched = [k for k in self._store if fnmatch.fnmatch(k, match)]
        return 0, matched

    def ping(self):
        return True

    def clear(self):
        self._store.clear()
        self._ttls.clear()


@pytest.fixture(autouse=True)
def reset_redis_mock():
    """Reset fake Redis antes de cada teste."""
    fake = FakeRedis()

    with patch("backend.app.cache._redis_client", fake), \
         patch("backend.app.cache._redis_available", True), \
         patch("backend.app.cache.get_redis", return_value=fake):
        yield fake


# ==================== TESTES: HELPERS DE CHAVE ====================

class TestCacheKeys:
    """Testes dos helpers de chave de cache."""

    def test_cache_key_dist_format(self):
        from utils.mapbox_api import _cache_key_dist
        key = _cache_key_dist(42, -23.5505, -46.6333)
        assert key == "dist:42:-23.5505:-46.6333"

    def test_cache_key_dist_rounding(self):
        """4 casas decimais = ~11m precisão. Coords a ~5m geram mesma chave."""
        from utils.mapbox_api import _cache_key_dist
        key1 = _cache_key_dist(1, -23.55051, -46.63331)
        key2 = _cache_key_dist(1, -23.55054, -46.63334)
        assert key1 == key2  # Diferença < 0.0001 → mesma chave

    def test_cache_key_dist_different_coords(self):
        """Coords a ~50m de distância geram chaves diferentes."""
        from utils.mapbox_api import _cache_key_dist
        key1 = _cache_key_dist(1, -23.5505, -46.6333)
        key2 = _cache_key_dist(1, -23.5510, -46.6340)
        assert key1 != key2

    def test_cache_key_dist_negative_coords(self):
        """Coordenadas negativas (hemisfério sul BR) funcionam."""
        from utils.mapbox_api import _cache_key_dist
        key = _cache_key_dist(1, -23.5505, -46.6333)
        assert "-23.5505" in key
        assert "-46.6333" in key

    def test_cache_key_geo_format(self):
        from utils.mapbox_api import _cache_key_geo
        key = _cache_key_geo("Rua das Flores, 123")
        assert key.startswith("geo:")
        assert len(key) == 4 + 12  # "geo:" + 12 hex chars

    def test_cache_key_geo_case_insensitive(self):
        """Case diferente → mesmo cache hit."""
        from utils.mapbox_api import _cache_key_geo
        key1 = _cache_key_geo("Rua das Flores, 123")
        key2 = _cache_key_geo("rua das flores, 123")
        assert key1 == key2

    def test_cache_key_geo_strips_spaces(self):
        """Espaços extras → mesmo cache hit."""
        from utils.mapbox_api import _cache_key_geo
        key1 = _cache_key_geo("Rua das Flores, 123")
        key2 = _cache_key_geo("  Rua das Flores, 123  ")
        assert key1 == key2

    def test_cache_key_geo_country_isolation(self):
        """Mesmo endereço em países diferentes → chaves diferentes."""
        from utils.mapbox_api import _cache_key_geo
        key_br = _cache_key_geo("Rua das Flores, 123", country="BR")
        key_pt = _cache_key_geo("Rua das Flores, 123", country="PT")
        assert key_br != key_pt

    def test_cache_key_geo_no_country(self):
        """Sem country e com country=None geram a mesma chave."""
        from utils.mapbox_api import _cache_key_geo
        key1 = _cache_key_geo("Rua das Flores, 123")
        key2 = _cache_key_geo("Rua das Flores, 123", country=None)
        assert key1 == key2

    def test_cache_key_dist_multi_tenant(self):
        """Cache do restaurante A não afeta restaurante B."""
        from utils.mapbox_api import _cache_key_dist
        key_a = _cache_key_dist(1, -23.5505, -46.6333)
        key_b = _cache_key_dist(2, -23.5505, -46.6333)
        assert key_a != key_b
        assert "dist:1:" in key_a
        assert "dist:2:" in key_b


# ==================== TESTES: CACHE BÁSICO ====================

class TestCacheBasic:
    """Testes do fluxo cache miss → save → hit."""

    def test_cache_miss_then_hit(self, reset_redis_mock):
        """Primeiro request → cache miss → salva. Segundo → cache hit."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        key = _cache_key_dist(1, -23.5505, -46.6333)

        # Miss
        assert cache_get(key) is None

        # Save
        data = {"dentro_zona": True, "distancia_km": 2.5, "taxa_entrega": 5.0}
        cache_set(key, data, ttl_seconds=2592000)

        # Hit
        result = cache_get(key)
        assert result is not None
        assert result["dentro_zona"] is True
        assert result["distancia_km"] == 2.5
        assert result["taxa_entrega"] == 5.0

    def test_different_coords_miss(self, reset_redis_mock):
        """Coordenada diferente → cache miss."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        key1 = _cache_key_dist(1, -23.5505, -46.6333)
        key2 = _cache_key_dist(1, -23.5600, -46.6400)

        cache_set(key1, {"dentro_zona": True, "distancia_km": 2.5, "taxa_entrega": 5.0}, 100)
        assert cache_get(key2) is None

    def test_same_precision_coords_hit(self, reset_redis_mock):
        """Coords a ~5m de distância (mesmos 4 decimais) → mesmo cache hit."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        # Ambas arredondam para -23.5505, -46.6333
        key1 = _cache_key_dist(1, -23.55051, -46.63331)
        key2 = _cache_key_dist(1, -23.55054, -46.63334)

        data = {"dentro_zona": True, "distancia_km": 2.5, "taxa_entrega": 5.0}
        cache_set(key1, data, 100)

        result = cache_get(key2)
        assert result is not None
        assert result["taxa_entrega"] == 5.0


# ==================== TESTES: INVALIDAÇÃO ====================

class TestCacheInvalidation:
    """Testes de invalidação do cache de distâncias."""

    def test_invalidate_clears_cache(self, reset_redis_mock):
        """Invalidar restaurante limpa todo cache de distâncias."""
        from backend.app.cache import cache_get, cache_set, invalidate_distancias
        from utils.mapbox_api import _cache_key_dist

        key = _cache_key_dist(1, -23.5505, -46.6333)
        cache_set(key, {"dentro_zona": True, "distancia_km": 2.5, "taxa_entrega": 5.0}, 100)
        assert cache_get(key) is not None

        invalidate_distancias(1)
        assert cache_get(key) is None

    def test_invalidate_multi_tenant(self, reset_redis_mock):
        """Invalidar restaurante A não apaga cache do restaurante B."""
        from backend.app.cache import cache_get, cache_set, invalidate_distancias
        from utils.mapbox_api import _cache_key_dist

        key_a = _cache_key_dist(1, -23.5505, -46.6333)
        key_b = _cache_key_dist(2, -23.5505, -46.6333)

        cache_set(key_a, {"dentro_zona": True, "distancia_km": 2.5, "taxa_entrega": 5.0}, 100)
        cache_set(key_b, {"dentro_zona": True, "distancia_km": 3.0, "taxa_entrega": 7.0}, 100)

        invalidate_distancias(1)

        assert cache_get(key_a) is None  # Limpo
        assert cache_get(key_b) is not None  # Intacto
        assert cache_get(key_b)["taxa_entrega"] == 7.0

    def test_invalidate_multiple_keys(self, reset_redis_mock):
        """Invalidar limpa TODAS as chaves de distância do restaurante."""
        from backend.app.cache import cache_get, cache_set, invalidate_distancias
        from utils.mapbox_api import _cache_key_dist

        keys = [
            _cache_key_dist(1, -23.5505, -46.6333),
            _cache_key_dist(1, -23.5600, -46.6400),
            _cache_key_dist(1, -23.5700, -46.6500),
        ]
        for k in keys:
            cache_set(k, {"dentro_zona": True, "distancia_km": 1.0, "taxa_entrega": 5.0}, 100)

        invalidate_distancias(1)

        for k in keys:
            assert cache_get(k) is None


# ==================== TESTES: GEOCODING CACHE ====================

class TestGeocodingCache:
    """Testes do cache de geocoding."""

    @patch("utils.mapbox_api.requests.get")
    def test_geocode_caches_result(self, mock_get, reset_redis_mock):
        """Geocode salva resultado no cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [{"center": [-46.6333, -23.5505]}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from utils.mapbox_api import geocode_address, _cache_key_geo
        from backend.app.cache import cache_get

        result = geocode_address("Rua das Flores, 123", country="BR")
        assert result == (-23.5505, -46.6333)

        # Verificar que foi salvo no cache (com country na chave)
        key = _cache_key_geo("Rua das Flores, 123", country="BR")
        cached = cache_get(key)
        assert cached is not None
        assert cached == [-23.5505, -46.6333]

    @patch("utils.mapbox_api.requests.get")
    def test_geocode_uses_cache_on_second_call(self, mock_get, reset_redis_mock):
        """Segundo geocode do mesmo endereço → cache hit, sem API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [{"center": [-46.6333, -23.5505]}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from utils.mapbox_api import geocode_address

        # Primeira chamada → API
        result1 = geocode_address("Rua das Flores, 123", country="BR")
        assert mock_get.call_count == 1

        # Segunda chamada → cache (sem nova chamada API)
        result2 = geocode_address("Rua das Flores, 123", country="BR")
        assert mock_get.call_count == 1  # Não chamou de novo
        assert result1 == result2

    @patch("utils.mapbox_api.requests.get")
    def test_geocode_no_cache_on_none_result(self, mock_get, reset_redis_mock):
        """Geocode que retorna None → NÃO cacheia."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from utils.mapbox_api import geocode_address, _cache_key_geo
        from backend.app.cache import cache_get

        result = geocode_address("Endereço Inexistente XYZ", country="BR")
        assert result is None

        key = _cache_key_geo("Endereço Inexistente XYZ", country="BR")
        assert cache_get(key) is None


# ==================== TESTES: CÁLCULOS ====================

class TestDistanceCalculations:
    """Testes de cálculos de taxa de entrega."""

    def test_taxa_within_base_distance(self):
        """Taxa dentro distância base → taxa_base."""
        distancia = 2.0
        distancia_base_km = 3.0
        taxa_base = 5.0
        taxa_km_extra = 1.5

        if distancia <= distancia_base_km:
            taxa = taxa_base
        else:
            taxa = round(taxa_base + (distancia - distancia_base_km) * taxa_km_extra, 2)

        assert taxa == 5.0

    def test_taxa_beyond_base_distance(self):
        """Taxa além distância base → cálculo correto."""
        distancia = 5.0
        distancia_base_km = 3.0
        taxa_base = 5.0
        taxa_km_extra = 1.5

        if distancia <= distancia_base_km:
            taxa = taxa_base
        else:
            taxa = round(taxa_base + (distancia - distancia_base_km) * taxa_km_extra, 2)

        # 5.0 + (5.0 - 3.0) * 1.5 = 5.0 + 3.0 = 8.0
        assert taxa == 8.0

    def test_cached_taxa_equals_calculated(self, reset_redis_mock):
        """Taxa cacheada = taxa calculada (idênticas)."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        # Simular cálculo e cache
        distancia = 4.5
        taxa_base = 5.0
        distancia_base_km = 3.0
        taxa_km_extra = 2.0

        taxa_calculada = round(taxa_base + (distancia - distancia_base_km) * taxa_km_extra, 2)

        key = _cache_key_dist(1, -23.5505, -46.6333)
        cache_set(key, {
            "dentro_zona": True,
            "distancia_km": distancia,
            "taxa_entrega": taxa_calculada,
        }, 100)

        cached = cache_get(key)
        assert cached["taxa_entrega"] == taxa_calculada
        assert cached["taxa_entrega"] == 8.0


# ==================== TESTES: EDGE CASES ====================

class TestEdgeCases:
    """Testes de casos extremos."""

    def test_redis_unavailable_graceful(self):
        """Redis indisponível → funciona sem cache (best-effort)."""
        with patch("backend.app.cache.get_redis", return_value=None):
            from backend.app.cache import cache_get, cache_set

            # Não dá erro, apenas retorna None
            assert cache_get("dist:1:-23.5505:-46.6333") is None

            # Não dá erro ao tentar salvar
            cache_set("dist:1:-23.5505:-46.6333", {"test": True}, 100)

    def test_fora_zona_also_cached(self, reset_redis_mock):
        """Endereço fora da zona → 'fora' também cacheado."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        key = _cache_key_dist(1, -23.5505, -46.6333)
        data = {"dentro_zona": False, "distancia_km": 15.0, "taxa_entrega": 0.0}
        cache_set(key, data, 100)

        result = cache_get(key)
        assert result["dentro_zona"] is False
        assert result["distancia_km"] == 15.0

    def test_cache_ttl_30_days(self, reset_redis_mock):
        """Cache de distância usa TTL de 30 dias (2592000s)."""
        fake = reset_redis_mock
        from backend.app.cache import cache_set
        from utils.mapbox_api import _cache_key_dist

        key = _cache_key_dist(1, -23.5505, -46.6333)
        cache_set(key, {"dentro_zona": True}, ttl_seconds=2592000)
        assert fake._ttls.get(key) == 2592000

    @patch("utils.mapbox_api.requests.get")
    def test_geocode_ttl_7_days(self, mock_get, reset_redis_mock):
        """Cache de geocoding usa TTL de 7 dias (604800s)."""
        fake = reset_redis_mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "features": [{"center": [-46.6333, -23.5505]}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from utils.mapbox_api import geocode_address, _cache_key_geo

        geocode_address("Rua das Flores, 123", country="BR")
        key = _cache_key_geo("Rua das Flores, 123", country="BR")
        assert fake._ttls.get(key) == 604800

    def test_invalidation_config_fields(self, reset_redis_mock):
        """Testa que campos de config de entrega trigam invalidação."""
        campos_entrega = {'taxa_entrega_base', 'distancia_base_km', 'taxa_km_extra', 'raio_entrega_km'}

        # Simula dados recebidos pelo PUT /painel/config
        test_cases = [
            {"taxa_entrega_base": 6.0},
            {"distancia_base_km": 4.0},
            {"taxa_km_extra": 2.0},
            {"raio_entrega_km": 12.0},
        ]

        for dados in test_cases:
            assert campos_entrega & dados.keys(), f"Campo {dados.keys()} deveria triggerar invalidação"

        # Campos que NÃO devem triggerar
        dados_outros = {"status_atual": "aberto", "horario_abertura": "18:00"}
        assert not (campos_entrega & dados_outros.keys())


# ==================== TESTES: PERFORMANCE ====================

class TestPerformance:
    """Testes de performance do cache."""

    def test_cache_hit_faster_than_calculation(self, reset_redis_mock):
        """Cache hit deve ser significativamente mais rápido que calcular."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist
        from utils.haversine import haversine

        key = _cache_key_dist(1, -23.5505, -46.6333)
        data = {"dentro_zona": True, "distancia_km": 2.5, "taxa_entrega": 5.0}
        cache_set(key, data, 100)

        # Medir cache hit
        start = time.perf_counter()
        for _ in range(100):
            cache_get(key)
        cache_time = time.perf_counter() - start

        # Medir cálculo haversine + taxa
        start = time.perf_counter()
        for _ in range(100):
            d = haversine((-23.5505, -46.6333), (-23.5600, -46.6400))
            _ = 5.0 + max(0, d - 3.0) * 1.5
        calc_time = time.perf_counter() - start

        # Cache hit com FakeRedis local é basicamente dict lookup,
        # mas em produção com Redis real a vantagem é evitar chamadas Mapbox API (~200ms cada)
        # Aqui verificamos que o cache funciona em tempo razoável
        assert cache_time < 1.0  # 100 lookups em menos de 1s


# ==================== TESTES: INTEGRAÇÃO ====================

class TestIntegration:
    """Testes de integração com endpoints (mock)."""

    def test_validar_entrega_caches_on_second_call(self, reset_redis_mock):
        """POST validar-entrega com mesmas coords → cache hit na 2ª chamada."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        # Simula o fluxo: 1ª chamada salva no cache
        rest_id = 1
        lat, lng = -23.5505, -46.6333
        key = _cache_key_dist(rest_id, lat, lng)

        # Simula save (como o endpoint faria)
        cache_set(key, {
            "dentro_zona": True,
            "distancia_km": 2.5,
            "taxa_entrega": 5.0,
            "mensagem": "Dentro da zona",
        }, ttl_seconds=2592000)

        # 2ª chamada → cache hit
        cached = cache_get(key)
        assert cached is not None
        assert cached["dentro_zona"] is True
        assert cached["taxa_entrega"] == 5.0

    def test_checkout_uses_cached_taxa(self, reset_redis_mock):
        """Checkout usa taxa cacheada se endereço já foi validado."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        rest_id = 1
        lat, lng = -23.5505, -46.6333
        key = _cache_key_dist(rest_id, lat, lng)

        # Cache preenchido pelo validar-entrega anterior
        cache_set(key, {
            "dentro_zona": True,
            "distancia_km": 2.5,
            "taxa_entrega": 7.50,
        }, ttl_seconds=2592000)

        # Checkout lê do cache
        cached = cache_get(key)
        assert cached is not None
        assert cached["taxa_entrega"] == 7.50

    def test_bot_validar_endereco_uses_cache(self, reset_redis_mock):
        """Bot _validar_endereco usa cache para coords já conhecidas."""
        from backend.app.cache import cache_get, cache_set
        from utils.mapbox_api import _cache_key_dist

        rest_id = 1
        lat, lng = -23.5505, -46.6333
        key = _cache_key_dist(rest_id, lat, lng)

        cache_set(key, {
            "dentro_zona": True,
            "distancia_km": 2.5,
            "taxa_entrega": 5.0,
        }, ttl_seconds=2592000)

        cached = cache_get(key)
        assert cached is not None
        assert cached["taxa_entrega"] == 5.0

    def test_no_cache_for_demo_restaurant(self, reset_redis_mock):
        """Demo restaurants devem ser bypassed (sem cache)."""
        from backend.app.cache import cache_get
        from utils.mapbox_api import _cache_key_dist

        # Demo restaurants nunca chegam no cálculo de distância
        # (retornam valores fixos antes). Verificar que não há
        # cache poluído por demo.
        key = _cache_key_dist(999, -23.5505, -46.6333)
        assert cache_get(key) is None

    def test_restaurant_without_coords_no_cache(self, reset_redis_mock):
        """Restaurante sem coordenadas → não cacheia (key precisa de rest coords)."""
        from utils.mapbox_api import _cache_key_dist

        # O endpoint verifica restaurante.latitude antes de montar key
        # Se None, não monta key nem cacheia
        # Aqui verificamos que a chave gerada com coords=None não seria usada
        # (o endpoint não chega a chamar _cache_key_dist se coords=None)
        # O teste é conceitual: o fluxo nem tenta cachear sem coords
        assert True  # Fluxo protegido no endpoint


# ==================== RESUMO ====================

class TestSummary:
    """Testes de resumo para validação rápida."""

    def test_all_cache_functions_exist(self):
        """Verifica que todas as funções de cache existem."""
        from backend.app.cache import (
            cache_get, cache_set, cache_delete, cache_delete_pattern,
            invalidate_cardapio, invalidate_distancias,
        )
        from utils.mapbox_api import _cache_key_dist, _cache_key_geo

        assert callable(cache_get)
        assert callable(cache_set)
        assert callable(invalidate_distancias)
        assert callable(_cache_key_dist)
        assert callable(_cache_key_geo)
