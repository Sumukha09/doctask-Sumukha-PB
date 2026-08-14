# Engineering Rules — FlowDocs V2

These rules govern every change made in this repository. They are non-negotiable.

## 1. Investigate before fixing
- Read the relevant code, logs, and configuration before changing anything.
- Form a hypothesis, then verify it. Do not guess.

## 2. No hardcoded special cases pretending to be intelligence
- No string matches, keyword checks, or "if X then pretend it works" branches.
- If a behaviour cannot be derived from explicit data, do not invent it.

## 3. No duplicated architecture
- One configuration loader. One database access layer. One migration system.
- Do not create parallel implementations of the same concern.

## 4. No business logic in API routes
- Route handlers parse, delegate, and shape responses only.
- Any non-trivial logic belongs in a service or repository.

## 5. No workflow logic in repositories
- Repositories translate between SQLAlchemy and the domain model.
- They do not orchestrate steps, make decisions, or call external services.

## 6. One migration system: Alembic
- All schema changes go through Alembic.
- No raw SQL migration files. No `Base.metadata.create_all()` in production paths.
- `pgvector` is enabled via the initial Alembic migration; that is the only place.

## 7. Explicit typed interfaces
- Function signatures are typed. Pydantic models on every boundary.
- Avoid `Any`, implicit casts, and undocumented return shapes.

## 8. Tests must prove behaviour
- A test that cannot fail is not a test.
- Prefer real interactions (database, HTTP) over mocks when feasible.
- Deterministic inputs and assertions; no flaky fixtures.

## 9. Never claim a feature works without verification
- Run the actual commands. Paste the actual output.
- "It should work" is not evidence.

## 10. Prefer simple, debuggable code over clever abstractions
- Readable first. Optimise only when measurement demands it.
- If a junior engineer cannot follow the call graph, it is too clever.
