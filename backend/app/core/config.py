from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal Music Intelligence API"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()