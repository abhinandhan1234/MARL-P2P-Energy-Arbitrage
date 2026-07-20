"""HTTP and WebSocket bridge for the SolarXChange trading terminal."""

from __future__ import annotations

# standard library
import asyncio
import csv
import json
import os
import uuid
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# third party
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# local
from p2p_energy_trading.api import P2PExperimentAPI
from p2p_energy_trading.api.models import EvaluationRequest, TrainingRequest
from p2p_energy_trading.blockchain_service import (
    BlockchainService,
    BlockchainUnavailable,
)
from p2p_energy_trading.constants import (
    ALL_AGENT_IDS,
    COLLEGE_AGENT_ID,
    CONSUMER_AGENT_IDS,
    SOLAR_AGENT_IDS,
)
from p2p_energy_trading.exceptions import ExperimentNotFoundError, ResourceError

# server.py lives at <repo>/src/p2p_energy_trading/server.py.
ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: Path) -> None:
    """Load local development settings without overriding real environment values."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(ROOT / ".env")
CHECKPOINT_DIR = ROOT / os.getenv("CHECKPOINT_DIR", "checkpoints")
DATA_PATH = ROOT / os.getenv("DATA_PATH", "kls_vdit_hourly_market.csv")
TRADE_LEDGER_PATH = ROOT / "data" / "manual_trades.json"


class TrainingPayload(BaseModel):
    config_path: str = "config/training_config.yaml"
    seed: int | None = None
    max_iterations: int | None = Field(default=None, ge=1)
    num_workers: int | None = Field(default=None, ge=0)
    use_gpu: bool = False
    experiment_name: str | None = None


class EvaluationPayload(BaseModel):
    checkpoint_path: str
    config_path: str | None = "config/eval_config.yaml"
    num_episodes: int = Field(default=20, ge=1)
    num_seeds: int = Field(default=5, ge=1)
    deterministic: bool = True
    experiment_name: str | None = None


class TradePayload(BaseModel):
    agent_id: str
    volume_kwh: float = Field(gt=0, le=5000)
    price_rs_per_kwh: float = Field(gt=0, le=100)
    counterparty_id: str | None = None

    @field_validator("agent_id", "counterparty_id")
    @classmethod
    def known_agent(cls, value: str | None) -> str | None:
        if value is not None and value not in ALL_AGENT_IDS:
            raise ValueError("must be one of the 21 registered agent IDs")
        return value


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        for websocket in list(self.connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket)


class LiveState:
    """Deterministic live projection of the actual campus profile dataset."""

    def __init__(self) -> None:
        self.cursor = 0
        self.rows = self._load_profile()
        self.trades = self._read_json(TRADE_LEDGER_PATH)

    @staticmethod
    def _read_json(path: Path) -> list[dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def _load_profile() -> list[dict[str, float | str]]:
        if not DATA_PATH.exists():
            return [{"timestamp": "", "solar": 0.0, "demand": 0.0}]
        with DATA_PATH.open(newline="", encoding="utf-8") as file:
            return [
                {
                    "timestamp": row["Timestamp"],
                    "solar": float(row["College_Solar_kW"]),
                    "demand": float(row["Campus_Demand_kW"]),
                }
                for row in csv.DictReader(file)
            ]

    def snapshot(self, advance: bool = True) -> dict[str, Any]:
        row = self.rows[self.cursor % len(self.rows)]
        if advance:
            self.cursor = (self.cursor + 1) % len(self.rows)
        solar = float(row["solar"])
        demand = float(row["demand"])
        clearing_price = round(4.4 + min(2.6, demand / 25) - min(1.2, solar / 260), 2)
        agents: dict[str, dict[str, float | str]] = {
            COLLEGE_AGENT_ID: {
                "type": "college",
                "soc": round(0.5 + 0.2 * (solar / 200) - 0.08 * (demand / 50), 3),
                "p2p_price": clearing_price,
                "generation_kw": solar,
                "demand_kw": demand,
                "profit_rs": round((solar - demand) * clearing_price, 2),
            }
        }
        solar_each = solar / len(SOLAR_AGENT_IDS)
        for index, agent_id in enumerate(SOLAR_AGENT_IDS, start=1):
            generation = round(solar_each * (0.78 + index * 0.025), 2)
            agents[agent_id] = {
                "type": "solar",
                "soc": round(0.45 + (index % 6) * 0.07, 3),
                "p2p_price": round(clearing_price - 0.15 + index * 0.02, 2),
                "generation_kw": generation,
                "demand_kw": round(1.2 + index * 0.13, 2),
                "profit_rs": round(generation * clearing_price, 2),
            }
        for index, agent_id in enumerate(CONSUMER_AGENT_IDS, start=1):
            load = round(demand / len(CONSUMER_AGENT_IDS) * (0.84 + index * 0.06), 2)
            agents[agent_id] = {
                "type": "consumer",
                "soc": 0.0,
                "p2p_price": round(clearing_price + 0.12 + index * 0.02, 2),
                "generation_kw": 0.0,
                "demand_kw": load,
                "profit_rs": round(-load * clearing_price, 2),
            }
        net_import = round(demand - solar, 2)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "profile_timestamp": row["timestamp"],
            "agents": agents,
            "clearing_price": clearing_price,
            "total_p2p_volume_kwh": round(max(0, min(solar, demand)), 2),
            "grid_import_kw": net_import,
            "solar_forecast": self.forecast(),
            "recent_trades": self.trades[-20:][::-1],
        }

    def forecast(self) -> list[dict[str, float | str]]:
        return [
            {
                "hour": str(
                    self.rows[(self.cursor + offset) % len(self.rows)]["timestamp"]
                ),
                "solar_kw": float(
                    self.rows[(self.cursor + offset) % len(self.rows)]["solar"]
                ),
                "demand_kw": float(
                    self.rows[(self.cursor + offset) % len(self.rows)]["demand"]
                ),
            }
            for offset in range(min(168, len(self.rows)))
        ]

    def submit_trade(self, trade: TradePayload) -> dict[str, Any]:
        trade_record = {
            "trade_id": f"trade_{uuid.uuid4().hex[:12]}",
            "seller": trade.agent_id,
            "buyer": trade.counterparty_id or COLLEGE_AGENT_ID,
            "volume_kwh": round(trade.volume_kwh, 3),
            "price_rs_per_kwh": round(trade.price_rs_per_kwh, 2),
            "amount_rs": round(trade.volume_kwh * trade.price_rs_per_kwh, 2),
            "status": "COMPLETED",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.trades.append(trade_record)
        TRADE_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRADE_LEDGER_PATH.write_text(
            json.dumps(self.trades, indent=2), encoding="utf-8"
        )
        return trade_record


manager = ConnectionManager()
live_state = LiveState()
experiment_api = P2PExperimentAPI(ROOT / "experiments")
blockchain = BlockchainService(
    artifact_path=ROOT / "blockchain" / "artifacts" / "EnergyTrading.json"
)


async def broadcast_live_state() -> None:
    while True:
        await manager.broadcast(live_state.snapshot())
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(broadcast_live_state())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="SolarXChange API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def record_dict(record: Any) -> dict[str, Any]:
    return record.to_dict() if hasattr(record, "to_dict") else asdict(record)


def resolve_status() -> dict[str, Any]:
    experiments = experiment_api.list_experiments()
    if not experiments:
        return {
            "state": "IDLE",
            "is_alive": False,
            "current_iteration": 0,
            "total_iterations": 0,
            "best_reward": None,
            "metrics_summary": {},
        }
    latest = max(experiments, key=lambda record: record.created_at)
    return experiment_api.get_status(latest.experiment_id).to_dict()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/status")
def status() -> dict[str, Any]:
    try:
        return resolve_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/experiments")
def experiments() -> list[dict[str, Any]]:
    return [record_dict(record) for record in experiment_api.list_experiments()]


@app.get("/api/experiments/{experiment_id}")
def experiment(experiment_id: str) -> dict[str, Any]:
    try:
        return record_dict(experiment_api.get_experiment(experiment_id))
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/experiments/{experiment_id}/metrics")
def metrics(experiment_id: str, level: str = "summary") -> dict[str, Any]:
    try:
        return asdict(experiment_api.results.get_metrics(experiment_id, level))
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/training/start", status_code=201)
def start_training(payload: TrainingPayload) -> dict[str, Any]:
    try:
        return record_dict(
            experiment_api.start_training(TrainingRequest(**payload.model_dump()))
        )
    except ResourceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/evaluation/start", status_code=201)
def start_evaluation(payload: EvaluationPayload) -> dict[str, Any]:
    try:
        return record_dict(
            experiment_api.start_evaluation(EvaluationRequest(**payload.model_dump()))
        )
    except ResourceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/checkpoints")
def checkpoints() -> list[dict[str, str]]:
    if not CHECKPOINT_DIR.exists():
        return []
    return [
        {"name": directory.name, "path": str(directory.relative_to(ROOT))}
        for directory in sorted(CHECKPOINT_DIR.iterdir())
        if directory.is_dir()
    ]


@app.get("/api/grid/state")
def grid_state() -> dict[str, Any]:
    return live_state.snapshot(advance=False)


@app.post("/api/trade", status_code=201)
def submit_trade(payload: TradePayload) -> dict[str, Any]:
    return live_state.submit_trade(payload)


@app.post("/api/blockchain/settle", status_code=201)
def settle_trades() -> dict[str, Any]:
    pending = [trade for trade in live_state.trades if not trade.get("tx_hash")]
    if not pending:
        return {"settled": 0, "transactions": []}
    if not blockchain.configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "On-chain settlement is unavailable until blockchain environment "
                "variables and contract artifact are configured."
            ),
        )
    transactions = []
    try:
        for trade in pending:
            tx_hash = blockchain.settle_trade(
                blockchain.resolve_party(trade["seller"]),
                blockchain.resolve_party(trade["buyer"]),
                round(trade["volume_kwh"] * 1000),
                round(trade["price_rs_per_kwh"] * 100),
            )
            trade["tx_hash"] = tx_hash
            trade["status"] = "SETTLEMENT_SUBMITTED"
            transactions.append({"trade_id": trade["trade_id"], "tx_hash": tx_hash})
        TRADE_LEDGER_PATH.write_text(
            json.dumps(live_state.trades, indent=2), encoding="utf-8"
        )
    except BlockchainUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Settlement transaction failed: {exc}"
        ) from exc
    return {"settled": len(transactions), "transactions": transactions}


@app.get("/api/blockchain/transactions")
def blockchain_transactions() -> list[dict[str, Any]]:
    if blockchain.configured:
        try:
            return blockchain.get_trades()[-50:][::-1]
        except BlockchainUnavailable:
            pass
    return [trade for trade in live_state.trades if trade.get("tx_hash")][-50:][::-1]


@app.websocket("/ws/live")
async def live_websocket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json(live_state.snapshot(advance=False))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


FRONTEND_DIST = ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
