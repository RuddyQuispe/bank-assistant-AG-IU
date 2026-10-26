# Importar aquí cada entidad nueva: create_all solo crea las tablas de las clases ya importadas
from digital_wallet_rqm.infrastructure.persistence.entities.base import Base
from digital_wallet_rqm.infrastructure.persistence.entities.session_record import SessionRecord

__all__ = ["Base", "SessionRecord"]
