"""Run the SharePoint-data chatbot locally.

Today (local file):
    1. Put your free Gemini key in backend/.env  (GEMINI_API_KEY=...)
    2. Set DATA_PATH in .env to your Excel/CSV (default: HR_Staff_Data.xlsx)
    3. From the backend folder:  python demo.py
    4. Ask questions; "quit" to exit.

Later (live SharePoint): set SOURCE_TYPE=sharepoint plus GRAPH_TOKEN and
SHAREPOINT_FILE_URL — everything else stays the same.
"""
import asyncio

from app.agent import answer_question
from app.config import settings
from app.datasource import schema


async def main() -> None:
    try:
        schema_text, _ = schema()  # also confirms the data loaded
    except FileNotFoundError:
        print(f"\n  Couldn't find the data file: {settings.data_path}")
        print("  Fix: copy your Excel/CSV into this backend folder, or set DATA_PATH")
        print("  in .env to its full path (e.g. DATA_PATH=C:\\\\Users\\\\you\\\\HR_Staff_Data.xlsx)\n")
        return
    print(f"\n  Chatbot over: {settings.data_path}  (source: {settings.source_type})")
    print("  " + schema_text.replace("\n", "\n  "))
    print("\n  Ask a question (e.g. 'average salary by job title'). 'quit' to exit.\n")
    while True:
        try:
            q = input("Ask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"quit", "exit", ""}:
            break
        res = await answer_question(q, [])
        print(f"\n  Answer: {res.answer}")
        print(f"  SQL:    {res.explainability.sql}")
        print(f"  (confidence: {res.explainability.confidence})\n")


if __name__ == "__main__":
    asyncio.run(main())
