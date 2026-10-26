# digital-wallet-rqm

Asistente de banca móvil con RAG (LangGraph + Gemini) expuesto con FastAPI.

## Ejecutar

```bash
uv sync
uv run fastapi dev src/digital_wallet_rqm/api/main.py
```

Documentación interactiva en `/scalar` (contrato exportado en `docs/openapi.yaml`).

## Endpoints

| Ruta | Uso |
|------|-----|
| `POST /auth/token` | Obtiene el JWT del usuario demo |
| `POST /chat` | Pregunta al agente y devuelve la respuesta completa |
| `GET/DELETE /chat/sessions...` | Sesiones del usuario del token |
| `POST /agents/wallet` | Mismo agente por protocolo AG-UI, con respuesta en streaming (SSE) |

Todas las rutas, salvo `/auth/token`, exigen `Authorization: Bearer <jwt>`.
Cada sesión pertenece al usuario que la creó: usar la sesión de otro usuario responde `403`.

## Endpoint AG-UI

`POST /agents/wallet` recibe un `RunAgentInput` de AG-UI. `threadId` es el id de la sesión
(el mismo que usa `/chat`). Lo consume un frontend con CopilotKit (`HttpAgent` de `@ag-ui/client`).

```bash
curl -N http://localhost:8000/agents/wallet \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"threadId":"s1","runId":"r1","state":{},"tools":[],"context":[],"forwardedProps":{},
       "messages":[{"id":"m1","role":"user","content":"¿Cuánto cuesta un SPEI?"}]}'
```

Configuración en `.env`:

- `FRONTEND_ORIGINS`: orígenes permitidos por CORS, separados por coma (por defecto `http://localhost:5173`).
