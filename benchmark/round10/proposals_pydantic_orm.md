# Pydantic and ORMs, from your answer to item 27

Applied with the user's wording changes and 3 (b) (R10-pydantic, R10-orm-validation).

Your position:
- Pydantic is fine for standardizing user input, but it has many footguns. In FastAPI, a pydantic
  return annotation validates every response at run time.
- An ORM is fine where it makes database work easier, as long as it adds no run-time validation
  that the database already does.

The skill frames the ORM rule around the hot path: "No ORM on a hot path" / "fine off the hot path"
(R6-07). Your position frames it around duplicate validation, and the hot path is only where that
cost is worst. Below are rewrites of the two sections that reflect this, followed by one config
question.

## 1. Pydantic (replaces SKILL.md:318-322)

> - **Pydantic is for standardizing user input, at the boundary gate, and nowhere else.** `TID251`
>   bans the import, so the gate module declares `# ruff: noqa: TID251` and names the gate function
>   in its module docstring. A second suppression in one program means validation is no longer at
>   one gate. (R8-D10)
> - **No framework validates output.** FastAPI makes a route's return annotation its response
>   model, so every response is validated at run time. Pass `response_model=None` in the route
>   decorator, and keep the annotation for mypy.

What it costs: with `response_model=None`, the OpenAPI schema has no response body for that route.

## 2. ORMs (replaces SKILL.md:348-356)

> - **An ORM is fine where it makes database work easier, as long as it adds no run-time
>   validation that the database already does.** The cost is per row and per request, so on a hot
>   path, such as an endpoint that returns database values, use `sqlite3` and SQL unless the ORM
>   validates nothing. A migration, a healing script or a one-off backfill can take an ORM freely.
>   Declare the exception in the module that uses the ORM, with a file-level
>   `# ruff: noqa: TID251`. (Q17, R6-03, R6-07, R7-D04)

Item 27 then becomes: the pydantic suppression names its gate, and the ORM suppression stays bare.
The gate is something the reader cannot see from the import. Whether the ORM validates depends on
the library, and the config question below covers that.

## 3. Config question: which ORMs the ban covers

`pyproject-snippet.toml` bans `sqlalchemy.orm`, `sqlmodel`, `peewee`, `tortoise`, `pony`, `ormar`,
`piccolo` and `sqlobject` with the message `No ORM`. Under your position, the problem is
validation, and these libraries differ. As far as I know (not verified):
- SQLModel and ormar are built on pydantic.
- Pony checks attribute types on assignment.
- SQLAlchemy runs no validation unless you add `@validates`.

- (a) Keep banning every ORM, and lift the ban per module with `noqa`, as now.
- (b) Ban only the pydantic-backed ones (SQLModel, ormar) everywhere, and allow the rest. I would
  check each library's behaviour before writing the list.

## 4. A dead comment in the config

`pyproject-snippet.toml:41` still says `The ban is therefore lifted per directory, below.` The
per-directory list was removed (R7-D04-generalised), and the comment a few lines further down says
so. → `The ban is therefore lifted per module, with # ruff: noqa: TID251.`
