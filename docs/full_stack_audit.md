# SolarXChange full-stack connection audit

## Training pipeline

`TrainingControls -> POST /api/training/start -> P2PExperimentAPI.start_training -> TrainingService subprocess -> checkpoint -> GET /api/status`.

The API returns `201` on launch, `409` for an active same-kind run, `422` for invalid JSON, and converts unexpected service errors to `500`. The current terminal exposes the status data in the dashboard summary; a dedicated training control can call this endpoint without another backend change.

## Live inference / telemetry pipeline

`campus profile + 21 registered agents -> LiveState -> WS /ws/live (2 seconds) -> useWebSocket -> Zustand -> dashboard components`.

The live projection is intentionally separated from RLlib training. It exposes live market-shaped telemetry from the real campus profile without loading a heavy checkpoint for every connected client. The WebSocket reconnects exponentially from 1 to 30 seconds, while REST polling supplies a fallback state every five seconds.

## Trade settlement pipeline

`TradeForm -> POST /api/trade -> data/manual_trades.json -> SettleButton -> POST /api/blockchain/settle -> BlockchainService -> EnergyTrading -> TransactionLedger`.

Trades are recorded with `201`. A settlement returns `503` until a testnet RPC, deployer key, contract address, compiled ABI, and agent-to-wallet mapping are configured; this avoids presenting simulated hashes as blockchain evidence. Copy `blockchain/agent_wallets.example.json` to `agent_wallets.json` and use funded test wallets. A submitted chain transaction is shown with its Amoy PolygonScan link.

## Evaluation pipeline

`POST /api/evaluation/start -> P2PExperimentAPI.start_evaluation -> EvaluationService -> experiment results -> GET /api/experiments/{id}/metrics`.

The metrics route returns `404` when results have not yet been generated. Query error/loading states are rendered in the terminal, and mutations use a simple user-visible alert for failures or confirmations.
