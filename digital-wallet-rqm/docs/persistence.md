# Persistencia

Toda la persistencia vive en `src/digital_wallet_rqm/infrastructure/persistence/` (ver
[architecture.md](architecture.md)):

```
infrastructure/persistence/
  checkpointer.py    historial de cada sesión: checkpointer de LangGraph (sus tablas las maneja LangGraph)
  database.py        tablas propias: engine, URL, fábrica de sesiones, creación de tablas, ajustes de SQLite
  entities/          entidades ORM (una clase por tabla)
  repositories/      adaptadores que implementan los puertos de application/ports/outbound/
```

Las tablas propias se manejan con **SQLAlchemy 2.0 ORM** (el equivalente de JPA/Hibernate).

## Reglas

1. **Sin SQL nativo.** Nada de `text("SELECT ...")` ni SQL en strings: siempre entidades y expresiones
   del ORM (`select`, `update`, `delete`).
2. **Por entidad por defecto.** Usar `db.add`, `db.get` y `select(Entidad)` para las operaciones simples.
   Usar una sentencia (`update(...)`, `delete(...)`) solo cuando hace falta atomicidad o una operación
   masiva, con un comentario que explique por qué.
3. **Las entidades no salen del repositorio.** El repositorio las convierte al modelo de dominio
   (`to_domain()`) antes de devolverlas.
4. **Transacciones en el repositorio**, con `async with self._sessions.begin():`.
5. **El ORM solo vive en `infrastructure/persistence/`.** Dominio, aplicación y API dependen de los
   puertos (`application/ports/outbound/`), nunca de SQLAlchemy.
6. **Entidad nueva:** crearla en `entities/` e importarla en `entities/__init__.py`. Si no se importa,
   `create_all` no crea su tabla.

Las reglas 1 y 5 las verifica `tests/test_architecture.py`.

## Esquema y migraciones

`get_engine()` corre `Base.metadata.create_all` al arrancar. Solo crea las tablas que faltan y **nunca
modifica columnas existentes**. Cuando haya que cambiar una tabla existente, pasar a Alembic
(el equivalente de Flyway o Liquibase).

## Fuera de estas reglas

- Tablas del checkpointer de LangGraph (`checkpoints`, `writes`; en Postgres también `checkpoint_blobs`
  y `checkpoint_migrations`). Las crea y migra LangGraph: no se mapean ni se consultan con el ORM.
- Base de Chroma (`data/langchain_chroma/`), el vector store.

Las tablas propias van en la misma base que las de LangGraph. La relación entre ambas se hace por id
(`sessions.session_id = checkpoints.thread_id`), sin foreign keys hacia las tablas de LangGraph.
