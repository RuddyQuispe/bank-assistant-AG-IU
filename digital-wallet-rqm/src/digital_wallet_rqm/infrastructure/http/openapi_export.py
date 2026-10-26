from pathlib import Path

import yaml

from digital_wallet_rqm.infrastructure.http.main import app

# Copia del OpenAPI en YAML para compartir o importar (Postman, etc.). Se genera desde el código.
OPENAPI_YAML_PATH = Path(__file__).parents[4] / "docs" / "openapi.yaml"


def build_openapi_yaml() -> str:
    return yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True)
