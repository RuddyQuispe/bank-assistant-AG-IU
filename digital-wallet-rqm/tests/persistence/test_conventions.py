"""Reglas de persistencia (docs/persistence.md) verificadas sobre el código, al estilo ArchUnit"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[2] / "src" / "digital_wallet_rqm"
PERSISTENCE = PACKAGE / "persistence"


def _python_files(root: Path) -> list[Path]:
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


@pytest.mark.parametrize("path", _python_files(PACKAGE), ids=lambda path: str(path.relative_to(PACKAGE)))
def test_no_raw_sql_with_text(path: Path) -> None:
    # Siempre entidades y expresiones del ORM: nada de text("SELECT ...")
    assert "sqlalchemy.text" not in _imported_modules(path)


@pytest.mark.parametrize(
    "path",
    [path for path in _python_files(PACKAGE) if PERSISTENCE not in path.parents],
    ids=lambda path: str(path.relative_to(PACKAGE)),
)
def test_sqlalchemy_is_only_used_inside_persistence(path: Path) -> None:
    # Servicios, dominio y API dependen de los puertos, no del ORM
    assert not any(module.startswith("sqlalchemy") for module in _imported_modules(path))
