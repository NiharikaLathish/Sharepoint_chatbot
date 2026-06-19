# SharePoint Data Chatbot

Ask plain-English questions about a data file and get answers backed by real SQL queries over the actual data — **never invented numbers**. Reads column schemas automatically, so it works on any Excel/CSV with no hand-written schema.

```
question
   │
   ▼  (LLM writes SQL — never a number)
SELECT ... FROM "staff"        ← DuckDB runs it on the real data
   │
   ▼  (LLM explains the rows it got back)
grounded answer + the SQL it ran
```

> Built as part of an internship project at KPMG Digital Lighthouse (June 2026).

---

## How the "no made-up numbers" guarantee works

The LLM only ever writes a read-only `SELECT`. DuckDB executes it on the real data and returns the actual rows. The LLM then explains those rows — it **never produces a figure itself**. If the SQL is invalid or references a column that doesn't exist, the query fails and the bot replies *"I do not have sufficient data…"* instead of guessing.

`sql_validate.py` blocks anything that isn't a single `SELECT` — `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE` are all rejected before execution.

---

## Data source

The data source is pluggable via `.env`:

| `SOURCE_TYPE` | Description |
|---|---|
| `local` | Read an Excel/CSV from disk. Use this for the demo. |
| `sharepoint` | Fetch the file live from SharePoint via Microsoft Graph. Same pipeline; wire this once Graph access is confirmed (see [Going live against SharePoint](#going-live-against-sharepoint)). |

The app keeps no copy on disk — data lives in memory for the session and is re-read on restart, so a SharePoint source always reflects the latest file.

---

## Tech stack

| Component | Technology |
|---|---|
| Frontend | React.js, Vite |
| Backend | FastAPI |
| Database | DuckDB |
| Data Processing | Pandas |
| PBIX Extraction | pbi-tools |
| AI Models | Groq Llama 3, Google Gemini |
| Validation | Pydantic |
| Config | python-dotenv |

---

## Project structure

```
backend/
  app/
    agent.py         # question → SQL → validate → run → explain
    datasource.py    # loads file (local or SharePoint) into DuckDB, auto-discovers schema
    sharepoint.py    # Microsoft Graph fetch (the only tenant-gated piece)
    sql_validate.py  # read-only SELECT gate
    llm.py           # Gemini (REST) / OpenAI / Anthropic
    prompts.py       # SQL-generation + explanation prompts
  demo.py            # ask questions from the terminal
  tests/
    test_core.py     # 5 tests, no network needed
```

---

## Run it today (local file, free)

**1. Get a free Gemini key**

Go to [aistudio.google.com](https://aistudio.google.com) → *Get API key* → copy it.

**2. Open the `backend` folder in VS Code**

Terminal → New Terminal.

**3. Put your data file here**

Copy `HR_Staff_Data.xlsx` into the `backend/` folder, or set `DATA_PATH` in `.env` to its full path.

**4. Set up and install**

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
```

**5. Create `.env`**

Copy `.env.example` to `.env` and fill in your key:

```env
GEMINI_API_KEY=your_key_here
SOURCE_TYPE=local
DATA_PATH=HR_Staff_Data.xlsx
```

**6. Run**

```bash
python demo.py
```

Try asking: *"average salary by job title"*, *"headcount by gender"*, *"highest paid role"*.

**Run tests anytime (no API key needed):**

```bash
python -m pytest -q
```

---

## System workflow

```
1. User submits question
2. LLM rewrites question using conversation history (context-aware)
3. LLM generates SQL based on auto-discovered schema
4. SQL Safety Gate validates: only SELECT, no forbidden commands
5. DuckDB executes query on real data
6. LLM explains returned rows in plain English
7. Frontend shows: answer + generated SQL + result table
```

---

## Going live against SharePoint (later)

Only one piece needs tenant access — fetching the file. Everything after the fetch (DuckDB + SQL + grounding + explanation) is identical to the local flow.

**Steps:**

1. Register an app in **Entra ID** with delegated Microsoft Graph permission `Files.Read.All` (and/or `Sites.Read.All`); add a sign-in redirect URI.
2. Sign the user in (MSAL or device-code flow) to get a Graph token for scope `https://graph.microsoft.com/Files.Read.All`.
3. Find the file's Graph URL once via [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer):
   ```
   GET /sites/{host}:/sites/{path}:/drive/root:/Shared Documents/HR_Staff_Data.xlsx
   ```
   Use the item's content URL from the response.
4. In `.env`, set:
   ```env
   SOURCE_TYPE=sharepoint
   GRAPH_TOKEN=...
   SHAREPOINT_FILE_URL=...
   ```

> **Note:** Reaching SharePoint live requires an app registration in the tenant where the data lives. Check with whoever owns that tenant that you're permitted to register an app and use Graph before proceeding. Also ensure the data you point it at is something you're cleared to use (especially if it's real company data).

---

## Features

- **PBIX Dashboard Extraction** — automatic extraction of tables from Power BI files via pbi-tools
- **Dynamic Schema Discovery** — identifies tables and columns with no hardcoded mappings
- **Natural Language Querying** — plain-English questions, no SQL knowledge needed
- **SQL Transparency** — generated SQL shown alongside every answer for auditability
- **Zero-Hallucination Responses** — all figures come from DuckDB, never from the LLM
- **SQL Safety Gate** — blocks all write/modify operations before execution
- **Context-Aware Conversations** — follow-up questions work via conversation history

---

## License

Internal prototype — not for public distribution.
