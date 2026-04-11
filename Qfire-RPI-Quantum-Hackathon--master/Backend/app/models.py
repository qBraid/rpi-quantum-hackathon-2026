from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
    )


class Scenario(Base, TimestampMixin):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(50), default="wildfire")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    grid: Mapped[list[list[str]]] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    constraints_json: Mapped[dict] = mapped_column(JSON, default=dict)
    objectives_json: Mapped[dict] = mapped_column(JSON, default=dict)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)

    risk_runs: Mapped[list["RiskRun"]] = relationship(back_populates="scenario")
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(back_populates="scenario")
    optimization_runs: Mapped[list["OptimizationRun"]] = relationship(back_populates="scenario")
    benchmark_runs: Mapped[list["BenchmarkRun"]] = relationship(back_populates="scenario")
    reports: Mapped[list["Report"]] = relationship(back_populates="scenario")


class RiskRun(Base, TimestampMixin):
    __tablename__ = "risk_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    scenario_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    modes_json: Mapped[list[str]] = mapped_column(JSON)
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scenario: Mapped[Scenario] = relationship(back_populates="risk_runs")


class ForecastRun(Base, TimestampMixin):
    __tablename__ = "forecast_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    scenario_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshots_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnostics_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scenario: Mapped[Scenario] = relationship(back_populates="forecast_runs")


class OptimizationRun(Base, TimestampMixin):
    __tablename__ = "optimization_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    scenario_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scenario: Mapped[Scenario] = relationship(back_populates="optimization_runs")


class BenchmarkRun(Base, TimestampMixin):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    optimization_run_id: Mapped[str | None] = mapped_column(ForeignKey("optimization_runs.id"), nullable=True)
    scenario_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    availability_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scenario: Mapped[Scenario] = relationship(back_populates="benchmark_runs")


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    risk_run_id: Mapped[str | None] = mapped_column(ForeignKey("risk_runs.id"), nullable=True)
    forecast_run_id: Mapped[str | None] = mapped_column(ForeignKey("forecast_runs.id"), nullable=True)
    optimization_run_id: Mapped[str | None] = mapped_column(ForeignKey("optimization_runs.id"), nullable=True)
    benchmark_run_id: Mapped[str | None] = mapped_column(ForeignKey("benchmark_runs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="complete")
    sections_json: Mapped[dict] = mapped_column(JSON, default=dict)
    export_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scenario: Mapped[Scenario] = relationship(back_populates="reports")


class IntegrationStatus(Base, TimestampMixin):
    __tablename__ = "integration_statuses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(64), unique=True)
    available: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(64), default="unavailable")
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
