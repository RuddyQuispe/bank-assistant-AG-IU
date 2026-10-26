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
| `ports/inbound/chat_service.py` | `ChatService`: lo que la API le puede pedir al chat (puerto de entrada) |
| `ports/inbound/auth_service.py` | `AuthService`: login y usuario del token (puerto de entrada) |
| `ports/outbound/session_repository.py` | `SessionRepository`: dónde se guardan las sesiones (puerto de salida) |
| `ports/outbound/chat_agent.py` | `ChatAgent`: quién responde y guarda el historial (puerto de salida) |
| `ports/outbound/token_service.py` | `TokenService`: emitir y leer tokens, sin saber que son JWT (puerto de salida) |
| `ports/outbound/user_repository.py` | `UserRepository`: dónde se buscan los usuarios (puerto de salida) |
| `chat_use_cases.py` | `ChatUseCases`: las reglas del chat (dueño de la sesión, 404/403, título, orden del borrado) |
| `auth_use_cases.py` | `AuthUseCases`: las reglas del login (solo un usuario existente recibe token) |

Un puerto es una clase abstracta (`ABC`), equivalente a una `interface` de Java. Los casos de uso solo
reciben puertos, así que se testean con dobles en memoria (`tests/application/`).

### `infrastructure/`: los adaptadores (detalles técnicos)

| Carpeta | Qué adapta | Archivos principales |
|---|---|---|
| `http/` | FastAPI: la entrada REST y AG-UI | `main.py` (app y armado de dependencias), `routers/`, `schemas/` (DTOs Pydantic), `exception_handlers.py`, `agui/` |
| `agent/` | LangGraph: el grafo RAG | `rag_agent.py` (grafo), `nodes/`, `prompts/`, `state/`, `tools/`, `langgraph_chat_agent.py` (implementa `ChatAgent`) |
| `persistence/` | Toda la persistencia | `checkpointer.py` (historial, LangGraph), `database.py` + `entities/` + `repositories/` (tabla `sessions` con SQLAlchemy; `DemoUserRepository` con el usuario demo) |
| `llm/` | Gemini | `llm_model.py` (chat y embeddings) |
| `vectorstore/` | Chroma y documentos | `vector_store.py`, `document_indexer.py`, `document_builder.py`, `document_loaders.py` |
| `security/` | JWT (pyjwt) | `jwt_token_service.py` (implementa `TokenService`; todo el manejo de JWT vive aquí) |

`config/settings.py` tiene la configuración leída del entorno.

## Recorrido de una pregunta

**REST, `POST /chat`:**

```
http/routers/chat_router.py          recibe el DTO y el usuario del token
  └─► application/chat_use_cases.py  valida la sesión (404/403) o crea una nueva
        ├─► SessionRepository        ◄── persistence/repositories/sql_session_repository.py
        └─► ChatAgent                ◄── agent/langgraph_chat_agent.py ──► grafo RAG + checkpointer
```

**AG-UI, `POST /agents/wallet` (streaming):**

```
http/routers/agui_router.py          valida la sesión con SessionRepository (404/403)
  └─► http/agui/wallet_agui_adapter.py   traduce el grafo RAG a eventos AG-UI (SSE)
```

El adaptador AG-UI usa el grafo directamente y no pasa por `ChatUseCases`. Es una decisión explícita:
la librería `ag-ui-langgraph` necesita el grafo compilado para emitir los eventos del streaming.

**Login, `POST /auth/token`:**

```
http/routers/auth_router.py            recibe el nickname
  └─► application/auth_use_cases.py    si el usuario no existe: 401
        ├─► UserRepository             ◄── persistence/repositories/demo_user_repository.py
        └─► TokenService               ◄── security/jwt_token_service.py (pyjwt)
```

`get_current_user` (`http/dependencies.py`) usa el mismo caso de uso para leer el token de cada request.

## Puerto, caso de uso o adaptador

Un **adaptador conoce una tecnología** (FastAPI, pyjwt, SQLAlchemy, LangGraph) y vive en `infrastructure/`.
Un **caso de uso solo conoce puertos** y vive en `application/`. Por eso `auth_router.py` y
`JwtTokenService` son adaptadores, y `AuthUseCases` es un caso de uso.

## Dónde agregar cada cosa

| Necesito… | Va en |
|---|---|
| una regla de negocio nueva | `domain/` (si es un dato o regla pura) o `application/` (si coordina puertos) |
| un endpoint | `infrastructure/http/routers/` + su DTO en `infrastructure/http/schemas/` |
| una tabla | entidad en `infrastructure/persistence/entities/` + repositorio en `repositories/` + puerto en `application/ports/outbound/` (ver [persistence.md](persistence.md)) |
| un error con su status HTTP | subclase en `domain/errors/errors.py` (el status lo resuelve `exception_handlers.py`) |
| un nodo o una tool del agente | `infrastructure/agent/nodes/` o `infrastructure/agent/tools/` |

## Equivalencias con Spring Boot

| Spring Boot | Aquí |
|---|---|
| `@RestController` | `infrastructure/http/routers/*` |
| DTO | `infrastructure/http/schemas/*` (Pydantic) |
| `@RestControllerAdvice` | `infrastructure/http/exception_handlers.py` |
| `@Service` | `application/chat_use_cases.py` |
| `interface` del servicio o del repositorio | `application/ports/` |
| `@Repository` + `@Entity` | `infrastructure/persistence/repositories/` + `entities/` |
| configuración de beans | `lifespan` en `infrastructure/http/main.py` |

## Tests

`tests/` repite la misma estructura que `src/`: `tests/domain/`, `tests/application/` y
`tests/infrastructure/<adaptador>/`. `tests/test_architecture.py` verifica las reglas de este documento.
