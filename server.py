import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import answer_question
from app.config import settings
from app.datasource import schema, get_connection

app = FastAPI(title="Power BI Chatbot API")

# Setup CORS to allow the frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allowing all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class ChatRequest(BaseModel):
    question: str

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".pbix"):
        raise HTTPException(status_code=400, detail="Only .pbix files are supported.")
        
    file_path = UPLOAD_DIR / file.filename
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update settings to point to the new file
    settings.source_type = "local"
    settings.data_path = str(file_path.absolute())
    
    # Clear the DuckDB caches so it re-extracts the new file
    get_connection.cache_clear()
    schema.cache_clear()
    
    try:
        # Trigger schema extraction which runs pbi-tools
        schema_text, _ = schema()
        return {"status": "success", "message": "File uploaded and data extracted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        res = await answer_question(request.question, [])
        return {
            "answer": res.answer,
            "sql": res.explainability.sql,
            "confidence": res.explainability.confidence,
            "rows": res.rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
