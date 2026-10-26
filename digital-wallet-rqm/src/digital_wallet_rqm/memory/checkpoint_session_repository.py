from langgraph.checkpoint.base import BaseCheckpointSaver

from digital_wallet_rqm.services.session_repository import SessionRepository

# Clave de metadata del checkpoint donde se guarda el dueño de la sesión
OWNER_KEY = "user_id"


class CheckpointSessionRepository(SessionRepository):
    """Adaptador: el dueño viaja en la metadata de cada checkpoint de LangGraph"""

    def __init__(self, checkpointer: BaseCheckpointSaver[str]) -> None:
        self.checkpointer = checkpointer

    async def find_owner(self, session_id: str) -> str | None:
        latest = self.checkpointer.alist({"configurable": {"thread_id": session_id}}, limit=1)
        async for checkpoint in latest:
            # Sesiones antiguas sin dueño devuelven "": no coinciden con nadie
            return str(checkpoint.metadata.get(OWNER_KEY, ""))
        return None

    async def list_for_user(self, user_id: str) -> list[str]:
        # Hay un checkpoint por paso del grafo, por eso se eliminan duplicados
        thread_ids = [
            checkpoint.config["configurable"]["thread_id"]
            async for checkpoint in self.checkpointer.alist(None, filter={OWNER_KEY: user_id})
        ]
        return list(dict.fromkeys(thread_ids))

    async def delete(self, session_id: str) -> None:
        await self.checkpointer.adelete_thread(session_id)


def owner_metadata(user_id: str) -> dict[str, str]:
    """Metadata que se pasa en config["metadata"] para que LangGraph guarde el dueño en cada checkpoint"""
    return {OWNER_KEY: user_id}
