from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Mon Arcade Backend"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: Optional[str] = "postgresql://postgres:postgres@localhost:5432/mon_arcade"

    # Adapter flags
    USE_MOCK_BLOCKCHAIN: bool = True
    USE_MOCK_AI: bool = True

    # Blockchain & Smart Contracts
    MONAD_RPC_URL: str = "https://testnet-rpc.monad.xyz"
    MONAD_CHAIN_ID: int = 10143
    PRIVATE_KEY: Optional[str] = None
    VAULT_CONTRACT_ADDRESS: Optional[str] = None
    BLUFF_CONTRACT_ADDRESS: Optional[str] = None

    # AI & Gemini
    GEMINI_API_KEY: Optional[str] = None
    AI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        return self.GEMINI_API_KEY or self.AI_API_KEY

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
