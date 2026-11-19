import { HttpAgent } from '@ag-ui/client'
import { API_URL } from './config'

// Cliente AG-UI de una sesión: el JWT viaja en cada pedido y la sesión es el threadId.
export function createWalletAgent(token: string, sessionId: string): HttpAgent {
  return new HttpAgent({
    url: `${API_URL}/agents/wallet`,
    headers: { Authorization: `Bearer ${token}` },
    threadId: sessionId,
  })
}
