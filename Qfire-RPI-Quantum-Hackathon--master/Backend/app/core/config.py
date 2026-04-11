from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from Backend/ directory
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)


@dataclass(frozen=True)
class Settings:
    app_name: str = "QuantumProj API"
    api_prefix: str = "/api"
    sqlite_path: str = os.getenv(
        "QUANTUMPROJ_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "quantumproj.db"),
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
    )

    # IBM Quantum credentials
    ibm_token: str = os.getenv("QISKIT_IBM_TOKEN", "")
    ibm_channel: str = os.getenv("QISKIT_IBM_CHANNEL", "")
    ibm_instance: str = os.getenv("QISKIT_IBM_INSTANCE", "ibm-q/open/main")

    # qBraid
    qbraid_api_key: str = os.getenv("QBRAID_API_KEY", "")

    # Auth (future use)
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.sqlite_path}"

    @property
    def ibm_configured(self) -> bool:
        return bool(self.ibm_token)

    @property
    def qbraid_configured(self) -> bool:
        return bool(self.qbraid_api_key)

    @property
    def normalized_ibm_channel(self) -> str:
        if not self.ibm_channel:
            return ""
        if self.ibm_channel == "ibm_quantum":
            return "ibm_quantum_platform"
        return self.ibm_channel


settings = Settings()
