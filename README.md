# Insight — AI Data Analyst

Insight is a natural-language interface for exploring a PostgreSQL database. Ask a business question in plain English and the agent curates the request, inspects the live schema, generates a read-only SQL query, safety-checks it, executes it, and presents a concise answer with the underlying data.

The project combines a LangGraph workflow for dependable agent orchestration with a modern Streamlit interface for exploration.

## Architecture

```mermaid
flowchart LR
    U[User] --> UI[Streamlit UI\napp.py]
    UI --> G[LangGraph SQL analyst]

    subgraph Agent workflow
        G --> Q[Curate question]
        Q --> S[Load PostgreSQL schema]
        S --> SQL[Generate SQL]
        SQL --> J{Safety judge}
        J -- Unsafe --> X[Explain why execution was blocked]
        J -- Safe --> E[Execute read-only query]
        E --> A[Compose user-friendly answer]
    end

    S <--> DB[(PostgreSQL)]
    E <--> DB
    A --> UI
```

### Request lifecycle

1. The user asks a question in the Streamlit app.
2. `curate_questions` clarifies the question for the SQL workflow.
3. `get_schema_context` reads tables, columns, primary keys, and foreign-key relationships from the `public` PostgreSQL schema.
4. `generate_sql` uses that schema context to create a query limited to known tables and columns.
5. `is_safe_sql` asks a structured judge whether the query is read-only.
6. Unsafe queries are stopped and explained. Safe queries run through `execute_sql_query`.
7. `represent_final_answer` turns the returned rows into a concise, non-technical answer. The UI also makes the generated SQL and raw tabular data available for inspection.

## Project structure

```text
Data_Agent/
├── app.py                    # Streamlit application and presentation layer
├── agents/
│   └── sql_analyst.py        # LangGraph workflow and agent nodes
├── models/
│   └── schema.py             # Pydantic state and safety-judge contracts
├── utils/
│   ├── database.py           # PostgreSQL connection and protected execution
│   ├── schema_context.py     # Database metadata discovery
│   ├── llm_pick.py           # OpenRouter model selection
│   └── seed_database.py      # Database seed utility
├── data/                     # Source CSV datasets
├── pyproject.toml            # Project dependencies
└── uv.lock                   # Locked dependency versions
```

## Safety design

The application uses defense in depth for database access:

- The SQL-generation prompt permits `SELECT` statements only and requires a default 10-row limit.
- A separate structured LLM judge evaluates queries for potentially modifying commands before execution.
- The database execution layer starts a read-only transaction and sets a 10-second statement timeout.
- Query errors are returned as structured responses rather than crashing the interface.

The LLM safety review is helpful, but the database user's privileges should also be restricted to read-only access in production.

## Technology

- **UI:** Streamlit and Pandas
- **Orchestration:** LangGraph and LangChain
- **LLM provider:** OpenRouter through `langchain-openai`
- **Database:** PostgreSQL with `psycopg2`
- **Validation:** Pydantic
- **Environment/dependency management:** `uv`

## Setup

### 1. Install dependencies

```powershell
uv sync
```

### 2. Configure environment variables

Create a `.env` file (or copy `.env.example` if you keep an environment template) and fill in your values:

```powershell
New-Item .env -ItemType File
```

Required variables:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
OPENROUTER_API_KEY=your_openrouter_api_key
```

### 3. Start the application

```powershell
uv run streamlit run app.py
```

Then open the local address Streamlit prints, normally `http://localhost:8501`.

## Using Insight

Try questions such as:

- “What payment methods do we have?”
- “Show the 10 most highly rated drivers.”
- “Which cities have the most rides?”

Every completed response includes the plain-language result. Expand **View generated SQL** to audit the query, and inspect the table beneath the answer for returned rows.

## Production notes

- Use a dedicated PostgreSQL role with `SELECT` privileges only.
- Keep `.env` out of source control; it is already ignored by Git.
- Configure rate limits, monitoring, and authentication before exposing the app beyond a trusted network.
- Schema discovery occurs per request, so caching or a schema-refresh strategy may be appropriate for larger databases.
