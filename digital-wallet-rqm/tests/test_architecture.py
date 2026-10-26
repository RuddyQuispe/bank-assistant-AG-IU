"""Reglas de arquitectura verificadas sobre el código fuente, al estilo ArchUnit (ver docs/architecture.md).

Regla de dependencias: infrastructure -> application -> domain, nunca al revés.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "digital_wallet_rqm"
ROOT = "digital_wallet_rqm"

# Librerías de infraestructura: solo se usan en la capa infrastructure
FRAMEWORKS = ("fastapi", "starlette", "pydantic", "sqlalchemy", "langgraph", "langchain", "ag_ui", "copilotkit", "jwt")


def _python_files(layer: str) -> list[Path]:
    root = PACKAGE / layer
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def _violations(path: Path, forbidden: tuple[str, ...]) -> list[str]:
    return sorted(
        module
        for module in _imported_modules(path)
        if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
    )


def _ids(path: Path) -> str:
    return str(path.relative_to(PACKAGE))


@pytest.mark.parametrize("path", _python_files("domain"), ids=_ids)
def test_domain_depends_on_nothing_else(path: Path) -> None:
    # El dominio es Python puro: ni otras capas, ni configuración, ni frameworks
    forbidden = (f"{ROOT}.application", f"{ROOT}.infrastructure", f"{ROOT}.config", *FRAMEWORKS)
    assert _violations(path, forbidden) == []


@pytest.mark.parametrize("path", _python_files("application"), ids=_ids)
def test_application_depends_only_on_domain(path: Path) -> None:
    # Los casos de uso hablan con el exterior solo a través de sus puertos
    forbidden = (f"{ROOT}.infrastructure", f"{ROOT}.config", *FRAMEWORKS)
    assert _violations(path, forbidden) == []


@pytest.mark.parametrize("path", _python_files(""), ids=_ids)
def test_no_raw_sql_with_text(path: Path) -> None:
    # Persistencia con el ORM: nada de text("SELECT ...") (ver docs/persistence.md)
    assert "sqlalchemy.text" not in _imported_modules(path)


@pytest.mark.parametrize(
    "path",
    [path for path in _python_files("") if PACKAGE / "infrastructure" / "persistence" not in path.parents],
    ids=_ids,
)
def test_sqlalchemy_is_only_used_inside_persistence(path: Path) -> None:
    assert _violations(path, ("sqlalchemy",)) == []
