"""Settings for the SharePoint-data chatbot (Option B)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM ---
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # --- Data source ---
    # "local"      -> read a file on disk (use this today; great for the demo)
    # "sharepoint" -> fetch the file live from SharePoint via Microsoft Graph
    source_type: str = "local"

    # For source_type=local: path to the .xlsx or .csv
    data_path: str = "HR_Staff_Data.xlsx"

    # The SQL table name the chatbot will query (and tell the LLM about).
    table_name: str = "staff"

    # For source_type=sharepoint (wire these once Graph access is confirmed):
    graph_token: str = ""          # delegated Graph token (scope Files.Read.All)
    sharepoint_file_url: str = ""  # Graph download URL or drive-item path

    # For source_type=gdrive:
    gdrive_file_id: str = ""       # Google Drive file ID from the share link

    # --- Server ---
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
