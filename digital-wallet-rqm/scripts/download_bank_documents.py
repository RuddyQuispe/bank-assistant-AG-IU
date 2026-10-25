"""Descarga documentos públicos de bancos de Bolivia para probar el RAG.

Uso: uv run python scripts/download_bank_documents.py
Los archivos quedan en settings.DOCUMENTS_DIR (data/ está en .gitignore, no se suben al repo).
"""

import time
import urllib.request
from pathlib import Path

from digital_wallet_rqm.config.settings import settings

# (nombre del archivo, url). El nombre aparece en los ids de los chunks y en las fuentes citadas.
DOCUMENTS = [
    (
        "baneco_tarifario.pdf",
        "https://baneco.com.bo/assets/content/docs/footers/tarifario/909ef6fd8b3d44b38a0d521ab2c69b52.pdf",
    ),
    (
        "baneco_tarifario_creditos.pdf",
        "https://baneco.com.bo/assets/content/docs/footers/tarifario/dd39c34d1a2699386ec3d6edb2ab7a60.pdf",
    ),
    (
        "baneco_educacion_financiera.pdf",
        "https://baneco.com.bo/assets/content/docs/institucional/662185164f899.pdf",
    ),
    (
        "asfi_derechos_del_consumidor_financiero.pdf",
        "https://asfi.gob.bo/sites/default/files/2025-09/3.%20DERECHOS%20DEL%20CONSUMIDOR%20FINANCIERO.pdf",
    ),
    (
        "asfi_reglamento_proteccion_del_consumidor.pdf",
        "https://www.baneco.com.bo/doc/asfi/ASFI-Reglamento_derechos_del_consumidor.pdf",
    ),
    (
        "ipdrs_guia_educacion_financiera.pdf",
        "https://ipdrs.org/wp-content/uploads/2025/09/Raices-de-empoderamiento.pdf",
    ),
]

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
PAUSE_SECONDS = 1.5


def download_pdf(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()

    # Algunos sitios devuelven una página HTML de error en vez del PDF
    if not content.startswith(b"%PDF"):
        raise ValueError("la respuesta no es un PDF")
    destination.write_bytes(content)


def main() -> None:
    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    for file_name, url in DOCUMENTS:
        destination = settings.DOCUMENTS_DIR / file_name
        if destination.exists():
            print(f"SKIP {file_name} (ya existe)")
            continue

        try:
            download_pdf(url, destination)
            print(f"OK   {file_name}")
        except Exception as error:
            # Si una descarga falla, se sigue con las demás
            print(f"FAIL {file_name}: {error}")

        time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
