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
| `POST /chat` | Pregunta al agente y devuelve la respuesta completa (sin `session_id` crea una sesión nueva) |
| `POST /chat/sessions` | Crea una sesión vacía; el id (UUID) lo asigna el servidor |
| `GET /chat/sessions` | Sesiones del usuario con título y fechas, la más reciente primero |
| `GET/DELETE /chat/sessions/{id}...` | Historial o borrado de una sesión del usuario |
| `POST /agents/wallet` | Mismo agente por protocolo AG-UI, con respuesta en streaming (SSE) |

Todas las rutas, salvo `/auth/token`, exigen `Authorization: Bearer <jwt>`.
Cada sesión pertenece al usuario que la creó: usar la sesión de otro usuario responde `403` y un id
que no existe, `404` (el cliente no inventa ids). Los errores responden `{"error": "...", "detail": "..."}`.

Las sesiones se guardan en la tabla propia `sessions` (id, dueño, título con los primeros 150 caracteres
de la primera pregunta, fechas), en la misma base que las tablas del checkpointer de LangGraph.
Las tablas propias se manejan con SQLAlchemy ORM: ver las reglas en [docs/persistence.md](docs/persistence.md).

## Endpoint AG-UI

`POST /agents/wallet` recibe un `RunAgentInput` de AG-UI. `threadId` es el id de una sesión creada
antes con `POST /chat/sessions` (el mismo id que usa `/chat`). Lo consume un frontend con CopilotKit (`HttpAgent` de `@ag-ui/client`).

```bash
curl -N http://localhost:8000/agents/wallet \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"threadId":"<session_id de POST /chat/sessions>","runId":"r1","state":{},"tools":[],"context":[],"forwardedProps":{},
       "messages":[{"id":"m1","role":"user","content":"¿Cuánto cuesta un SPEI?"}]}'
```

Configuración en `.env`:

- `FRONTEND_ORIGINS`: orígenes permitidos por CORS, separados por coma (por defecto `http://localhost:5173`).
- `ERROR_TRACEBACK_ENABLED`: `true` agrega el traceback en `detail` de los errores 500 (solo desarrollo).
