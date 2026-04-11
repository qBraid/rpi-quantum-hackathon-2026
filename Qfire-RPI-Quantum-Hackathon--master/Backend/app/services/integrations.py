"""Integration status detection for qBraid, Qiskit, IBM Quantum, and simulators.

Reads credentials from the environment (loaded via python-dotenv in config.py)
and performs real availability checks against installed packages.
"""
from __future__ import annotations

import importlib.util
import importlib.metadata
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import IntegrationStatus

logger = logging.getLogger(__name__)


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _get_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None


def _check_ibm_connectivity() -> dict:
    """Test actual IBM Quantum connectivity if credentials are configured."""
    if not settings.ibm_configured:
        return {"connected": False, "reason": "QISKIT_IBM_TOKEN not configured"}

    if not _module_available("qiskit_ibm_runtime"):
        return {"connected": False, "reason": "qiskit-ibm-runtime not installed"}

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService

        service_kwargs = {"token": settings.ibm_token}
        if settings.ibm_instance:
            service_kwargs["instance"] = settings.ibm_instance
        if settings.normalized_ibm_channel:
            service_kwargs["channel"] = settings.normalized_ibm_channel

        # Try to initialize the service (validates token)
        service = QiskitRuntimeService(**service_kwargs)
        # Try listing backends to verify access
        backends = service.backends()
        backend_names = [b.name for b in backends[:5]]
        logger.info("IBM Quantum connected. Available backends: %s", backend_names)
        return {
            "connected": True,
            "channel": settings.ibm_channel or "auto",
            "normalized_channel": settings.normalized_ibm_channel or "auto",
            "instance": settings.ibm_instance,
            "available_backends": backend_names,
            "total_backends": len(backends) if backends else 0,
        }
    except Exception as exc:
        logger.warning("IBM Quantum connection check failed: %s", exc)
        return {"connected": False, "reason": str(exc)}


def _check_qbraid_status() -> dict:
    """Check qBraid SDK availability and API key status."""
    if not _module_available("qbraid"):
        return {"installed": False, "api_key_configured": False}

    version = _get_version("qbraid")

    # Check if qbraid transpiler is available
    transpiler_available = False
    try:
        from qbraid.transpiler import transpile  # noqa: F401
        transpiler_available = True
    except Exception:
        pass

    result = {
        "installed": True,
        "version": version,
        "api_key_configured": settings.qbraid_configured,
        "transpiler_available": transpiler_available,
    }

    # If API key is configured, try to validate it
    if settings.qbraid_configured:
        try:
            import os
            os.environ["QBRAID_API_KEY"] = settings.qbraid_api_key
            result["api_key_set_in_environment"] = True
        except Exception as exc:
            result["api_key_error"] = str(exc)

    return result


def collect_provider_statuses() -> list[dict]:
    """Collect real-time status for all integration providers."""
    qiskit_installed = _module_available("qiskit")
    aer_installed = _module_available("qiskit_aer")
    qasm3_import_installed = _module_available("qiskit_qasm3_import")
    qbraid_status = _check_qbraid_status()

    # Only do the IBM connectivity check if credentials exist
    ibm_status = _check_ibm_connectivity() if settings.ibm_configured else {
        "connected": False,
        "reason": "QISKIT_IBM_TOKEN not set in .env",
    }

    return [
        {
            "provider": "qbraid",
            "available": qbraid_status.get("installed", False),
            "mode": (
                "ready" if qbraid_status.get("installed") and qbraid_status.get("api_key_configured")
                else "sdk_only" if qbraid_status.get("installed")
                else "missing"
            ),
            "details": {
                **qbraid_status,
                "role": "Compiler-aware benchmarking and cross-framework transpilation backbone.",
            },
        },
        {
            "provider": "qiskit",
            "available": qiskit_installed,
            "mode": "benchmark_ready" if qiskit_installed and aer_installed and qasm3_import_installed else "ready" if qiskit_installed else "missing",
            "details": {
                "sdk_installed": qiskit_installed,
                "version": _get_version("qiskit"),
                "aer_installed": aer_installed,
                "aer_version": _get_version("qiskit-aer"),
                "qasm3_import_installed": qasm3_import_installed,
                "qasm3_import_version": _get_version("qiskit-qasm3-import"),
                "role": "Primary quantum circuit framework for QAOA workloads and simulator execution.",
            },
        },
        {
            "provider": "ibm_quantum",
            "available": ibm_status.get("connected", False),
            "mode": (
                "hardware_ready" if ibm_status.get("connected")
                else "token_configured" if settings.ibm_configured
                else "simulator_only"
            ),
            "details": {
                "token_configured": settings.ibm_configured,
                "channel": (settings.ibm_channel or "auto") if settings.ibm_configured else "not_configured",
                "normalized_channel": (settings.normalized_ibm_channel or "auto") if settings.ibm_configured else "not_configured",
                "instance": settings.ibm_instance if settings.ibm_configured else "not_configured",
                "runtime_version": _get_version("qiskit-ibm-runtime"),
                **ibm_status,
            },
        },
        {
            "provider": "local_simulators",
            "available": aer_installed,
            "mode": "ready" if aer_installed else "basic",
            "details": {
                "aer_installed": aer_installed,
                "aer_version": _get_version("qiskit-aer"),
                "ideal_simulator": aer_installed,
                "noisy_simulator": aer_installed,
                "noise_model": "depolarizing (configurable)" if aer_installed else "analytical_estimate",
                "methods": ["statevector", "density_matrix", "qasm_simulator"] if aer_installed else ["analytical"],
            },
        },
    ]


def sync_integration_statuses(db: Session) -> list[IntegrationStatus]:
    records: list[IntegrationStatus] = []
    for item in collect_provider_statuses():
        existing = db.scalar(select(IntegrationStatus).where(IntegrationStatus.provider == item["provider"]))
        if existing is None:
            existing = IntegrationStatus(
                provider=item["provider"],
                available=item["available"],
                mode=item["mode"],
                details_json=item["details"],
            )
            db.add(existing)
        else:
            existing.available = item["available"]
            existing.mode = item["mode"]
            existing.details_json = item["details"]
        records.append(existing)
    db.commit()
    for record in records:
        db.refresh(record)
    return records
