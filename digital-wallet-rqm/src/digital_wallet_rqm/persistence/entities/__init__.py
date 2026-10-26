# Importar aquí cada entidad nueva: create_all solo crea las tablas de las clases ya importadas
from digital_wallet_rqm.persistence.entities.base import Base
from digital_wallet_rqm.persistence.entities.session_record import SessionRecord

__all__ = ["Base", "SessionRecord"]
