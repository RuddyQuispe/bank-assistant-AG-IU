# Arquitectura

El proyecto sigue una **arquitectura hexagonal** (puertos y adaptadores) con tres capas:

```
infrastructure  ──►  application  ──►  domain
 (adaptadores)      (casos de uso,      (modelos y
                     puertos)            errores)
```

**Regla de dependencias:** cada capa solo importa las capas que están a su derecha. El dominio no
conoce a nadie, la aplicación solo conoce al dominio, y la infraestructura conoce a las dos.
`tests/test_architecture.py` hace cumplir esta regla: si un archivo la rompe, el test falla.

## Estructura

Rutas relativas a `src/digital_wallet_rqm/`.

### `domain/`: el negocio, en Python puro

No importa FastAPI, SQLAlchemy, LangGraph ni Pydantic.

| Archivo | Contenido |
|---|---|
| `models/current_user.py` | `CurrentUser`: usuario autenticado |
| `models/chat_session.py` | `ChatSession` y la regla del título (`build_title`: primeros 150 caracteres) |
| `models/chat.py` | `ChatAnswer` y `ChatMessage` |
| `errors/` | `AppError` y sus subclases (`NotFoundError`, `SessionForbiddenError`...), sin saber de HTTP |

### `application/`: los casos de uso y sus puertos

| Archivo | Contenido |
|---|---|
| `ports/session_repository.py` | `SessionRepository`: dónde se guardan las sesiones |
| `ports/chat_agent.py` | `ChatAgent`: quién responde y guarda el historial |
| `ports/token_service.py` | `TokenService`: emitir y leer tokens, sin saber que son JWT |
| `ports/user_repository.py` | `UserRepository`: dónde se buscan los usuarios |
| `chat_use_cases.py` | `ChatUseCases`: las reglas del chat (dueño de la sesión, 404/403, título, orden del borrado) |
| `auth_use_cases.py` | `AuthUseCases`: las reglas del login (solo un usuario existente recibe token) |

Un puerto es una clase abstracta (`ABC`), equivalente a una `interface` de Java, y cada archivo define un
solo contrato. Los puertos son solo de salida: describen lo que la aplicación necesita de afuera. Los routers
llaman directo al caso de uso, sin una interfaz de entrada, porque cada uno tiene una sola implementación.
Los casos de uso solo reciben puertos, así que se testean con dobles en memoria (`tests/application/`).

### `infrastructure/`: los adaptadores (detalles técnicos)

La carpeta muestra hacia dónde va cada adaptador. **`inbound/` llama a la aplicación** y **`outbound/` es lo que la
aplicación usa** a través de sus puertos. Lo saliente nunca importa lo entrante.

**`inbound/`: lo que entra**

| Carpeta | Qué adapta | Archivos principales |
|---|---|---|
| `rest/` | Endpoints REST con FastAPI | `routers/`, `schemas/` (DTOs Pydantic) |
| `agui/` | Protocolo AG-UI (streaming) | `agui_router.py`, `wallet_agui_adapter.py` |
| (raíz) | Lo que comparten REST y AG-UI | `dependencies.py`, `exception_handlers.py`, `error_schema.py`, `openapi_export.py` |

**`outbound/`: lo que sale**

| Carpeta | Qué adapta | Archivos principales |
|---|---|---|
| `agent/` | LangGraph: el grafo RAG | `rag_agent.py` (grafo), `nodes/`, `prompts/`, `state/`, `tools/`, `langgraph_chat_agent.py` (implementa `ChatAgent`) |
| `persistence/` | Toda la persistencia | `checkpointer.py` (historial, LangGraph), `database.py` + `entities/` + `repositories/` (SQLAlchemy, ver [persistence.md](persistence.md)) |
| `llm/` | Gemini | `llm_model.py` (chat y embeddings) |
| `vectorstore/` | Chroma y documentos | `vector_store.py`, `document_indexer.py`, `document_builder.py`, `document_loaders.py` |
| `security/` | JWT (pyjwt) | `jwt_token_service.py` (implementa `TokenService`; todo el manejo de JWT vive aquí) |

`infrastructure/settings.py` tiene la configuración leída del entorno.

### `main.py`: el punto de arranque

Crea la app de FastAPI y conecta los casos de uso con sus adaptadores (`lifespan`).

## Recorrido de una pregunta

**REST, `POST /chat`:**

```
inbound/rest/routers/chat_router.py          recibe el DTO y el usuario del token
  └─► application/chat_use_cases.py  valida la sesión (404/403) o crea una nueva
        ├─► SessionRepository        ◄── outbound/persistence/repositories/sql_session_repository.py
        └─► ChatAgent                ◄── outbound/agent/langgraph_chat_agent.py ──► grafo RAG + checkpointer
```

**AG-UI, `POST /agents/wallet` (streaming):**

```
inbound/agui/agui_router.py          valida la sesión con ChatUseCases.start_run (404/403)
  ├─► inbound/agui/wallet_agui_adapter.py   traduce el grafo RAG a eventos AG-UI (SSE)
  └─► ChatUseCases.finish_run             registra título y actividad si el run terminó bien
```

Las reglas de sesión pasan por `ChatUseCases`, igual que en REST. El grafo no pasa por el puerto `ChatAgent`,
y es una decisión explícita: la librería `ag-ui-langgraph` necesita el grafo compilado para emitir los
eventos del streaming.

**Login, `POST /auth/token`:**

```
inbound/rest/routers/auth_router.py            recibe el nickname
  └─► application/auth_use_cases.py    si el usuario no existe: 401
        ├─► UserRepository             ◄── outbound/persistence/repositories/demo_user_repository.py
        └─► TokenService               ◄── outbound/security/jwt_token_service.py (pyjwt)
```

`get_current_user` (`inbound/dependencies.py`) usa el mismo caso de uso para leer el token de cada request.

## Puerto, caso de uso o adaptador

Un **adaptador conoce una tecnología** (FastAPI, pyjwt, SQLAlchemy, LangGraph) y vive en `infrastructure/`.
Un **caso de uso solo conoce puertos** y vive en `application/`. Por eso `auth_router.py` y
`JwtTokenService` son adaptadores, y `AuthUseCases` es un caso de uso.

## Dónde agregar cada cosa

| Necesito… | Va en |
|---|---|
| una regla de negocio nueva | `domain/` (si es un dato o regla pura) o `application/` (si coordina puertos) |
| un endpoint | `infrastructure/inbound/rest/routers/` + su DTO en `infrastructure/inbound/rest/schemas/` |
| una tabla | entidad en `infrastructure/outbound/persistence/entities/` + repositorio en `repositories/` + puerto en `application/ports/outbound/` (ver [persistence.md](persistence.md)) |
| un error con su status HTTP | subclase en `domain/errors/errors.py` (el status lo resuelve `exception_handlers.py`) |
| un nodo o una tool del agente | `infrastructure/outbound/agent/nodes/` o `infrastructure/outbound/agent/tools/` |

## Equivalencias con Spring Boot

| Spring Boot | Aquí |
|---|---|
| `@RestController` | `infrastructure/inbound/rest/routers/*` |
| DTO | `infrastructure/inbound/rest/schemas/*` (Pydantic) |
| `@RestControllerAdvice` | `infrastructure/inbound/exception_handlers.py` |
| `@Service` | `application/chat_use_cases.py` |
| `interface` del repositorio o cliente externo | `application/ports/` |
| `@Repository` + `@Entity` | `infrastructure/outbound/persistence/repositories/` + `entities/` |
| configuración de beans | `lifespan` en `main.py` |

## Tests

`tests/` repite la misma estructura que `src/`: `tests/domain/`, `tests/application/` y
`tests/infrastructure/inbound/` y `tests/infrastructure/outbound/`. `tests/test_architecture.py` verifica las reglas de este documento.
