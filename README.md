# SharePoint-data Chatbot 

Ask plain-English questions about a data file and get answers backed by **real SQL
queries** over the actual data — never invented numbers. Reads the data's columns
automatically, so it works on **any** Excel/CSV with no hand-written schema.

```
question
   │
   ▼  (LLM writes SQL — never a number)
SELECT ... FROM "staff"        ← DuckDB runs it on the real data
   │
   ▼  (LLM explains the rows it got back)
grounded answer + the SQL it ran
```

**Data source is pluggable:**
- **`local`** — read an Excel/CSV on disk. Use this today; great for the demo.
- **`sharepoint`** — fetch the file live from SharePoint via Microsoft Graph. Same
  pipeline; you wire this once Graph access is confirmed (see bottom).

The app keeps **no copy on disk** — data lives in memory for the session and is
re-read on restart, so a SharePoint source always reflects the latest file.

---

## Run it today (local file, free)

1. **Get a free Gemini key:** aistudio.google.com → *Get API key* → copy it.
2. **Open this `backend` folder in VS Code** → Terminal → New Terminal.
3. **Put your data file here.** Copy `HR_Staff_Data.xlsx` (from the HR dashboard repo's
   `data` folder) into this `backend` folder. (Or set `DATA_PATH` in `.env` to its full path.)
4. **Set up + install:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
5. **Create `.env`** (copy `.env.example` to `.env`) and fill in `GEMINI_API_KEY`.
   Leave `SOURCE_TYPE=local` and `DATA_PATH=HR_Staff_Data.xlsx`.
6. **Run it:**
   ```powershell
   python demo.py
   ```
   Ask: *"average salary by job title"*, *"headcount by gender"*, *"highest paid role"*.

Run the tests anytime: `python -m pytest -q` (uses a tiny generated file, no key needed).

---

## How the "no made-up numbers" guarantee works

The LLM only ever writes a **read-only SELECT**. DuckDB executes it on the real data
and returns the actual rows. The LLM then explains *those rows* — it never produces a
figure itself. If the SQL is invalid or references a column that doesn't exist, the
query fails and the bot replies *"I do not have sufficient data…"* instead of guessing.
(`sql_validate.py` blocks anything that isn't a single SELECT.)

---

## Going live against SharePoint (later)

Only one piece needs tenant access — fetching the file. Steps:

1. Register an app (Entra) with **delegated** Microsoft Graph permission
   **`Files.Read.All`** (and/or `Sites.Read.All`); add a sign-in redirect.
2. Sign the user in (MSAL or device-code) to get a **Graph token** for scope
   `https://graph.microsoft.com/Files.Read.All`.
3. Find the file's Graph URL once (Graph Explorer is easiest), e.g.
   `GET /sites/{host}:/sites/{path}:/drive/root:/Shared Documents/HR_Staff_Data.xlsx`
   → use the item's content URL.
4. In `.env`: set `SOURCE_TYPE=sharepoint`, `GRAPH_TOKEN=...`, `SHAREPOINT_FILE_URL=...`.

Everything after the fetch (DuckDB + SQL + grounding + explanation) is identical.

**Two honest notes:**
- Reaching SharePoint live needs that app registration in the tenant where the data
  lives — check with whoever owns that tenant that you're allowed to register an app /
  use Graph.
- Make sure the data you point it at is something you're cleared to use for this
  (especially if it's real company data) before wiring it up.

## Layout
```
backend/
  app/
    agent.py         question -> SQL -> validate -> run -> explain
    datasource.py    loads file (local or SharePoint) into DuckDB, auto-discovers schema
    sharepoint.py    Microsoft Graph fetch (the only tenant-gated piece)
    sql_validate.py  read-only SELECT gate
    llm.py           Gemini (REST) / OpenAI / Anthropic
    prompts.py       SQL-generation + explanation prompts
  demo.py            ask questions from the terminal
  tests/test_core.py 5 tests, no network needed
```
