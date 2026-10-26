"""Exporta el OpenAPI que FastAPI genera desde el código a docs/openapi.yaml.

Uso: uv run python scripts/export_openapi.py
Correrlo después de cambiar un endpoint o un DTO; tests/infrastructure/http/test_openapi_docs.py avisa si quedó desactualizado.
"""

from digital_wallet_rqm.infrastructure.http.openapi_export import OPENAPI_YAML_PATH, build_openapi_yaml


def main() -> None:
    OPENAPI_YAML_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_YAML_PATH.write_text(build_openapi_yaml(), encoding="utf-8")
    print(f"OpenAPI exportado en {OPENAPI_YAML_PATH}")


if __name__ == "__main__":
    main()
