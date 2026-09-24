# P2P MARL Energy Trading System

A Peer-to-Peer Multi-Agent Reinforcement Learning energy trading system for a college campus microgrid. 21 autonomous agents trade energy while respecting physical grid constraints through PandaPower simulation, trained using MAPPO with centralized training and decentralized execution (CTDE).

## Features

- **21 Agents**: 1 College Building, 15 Solar Buildings, 5 Consumer Buildings
- **MAPPO with CTDE**: Centralized critic (243-dim), decentralized actors (23-dim)
- **3 Shared Policies**: College, Solar, Consumer with parameter sharing
- **IEEE 33-Bus Network**: PandaPower-validated power flow
- **Uniform Clearing Market**: Quantity-only P2P trading with pro-rata allocation
- **College Battery**: 500 kWh / 250 kW with SoC management
- **3-Stage Curriculum**: Debug → Training → Constraint-aware
- **Full Evaluation Suite**: 4 research questions, 3 baselines, 5 ablation studies
- **Persistent Escrow Settlement Layer**: Decentralized settlement smart contract (`EnergyTrading.sol`) with persistent local disk storage and auto-funding escrow loop.

---

## Blockchain Development Setup

The decentralized transaction settlement layer provides an immutable, escrow-backed ledger for P2P trading events across the microgrid.

### 1. How the Persistent Blockchain Works
* Local EVM development uses a **persistent LevelDB disk-backed engine** (Ganache) configured to match Hardhat's default developer accounts (25 accounts loaded with 1,000 ETH each).
* **Storage Location**: `blockchain/blockchain-data/` (git-ignored).
* **State Persistence**: Closing your IDE, terminating the terminal, or restarting your computer preserves all mined blocks, balances, contract bytecode, and trade history. **Stopping the node is NOT the same as resetting the chain.**

### 2. First-Time Blockchain Setup

```bash
# 1. Start the persistent local blockchain node
npm run blockchain:start

# 2. In a second terminal, compile and deploy the contract idempotently
npm run blockchain:init
```

This compiles `EnergyTrading.sol`, deploys it to the local chain, records the deployment metadata in `blockchain/deployments/localhost.json`, and updates `.env`.

### 3. Normal Startup (Subsequent Sessions)

Whenever you return to the project:

```bash
# Start the persistent node (automatically reconnects to existing blockchain-data)
npm run blockchain:start
```

*Because deployment is idempotent, you do NOT need to redeploy the contract.*

To verify that the existing contract and block history are fully intact:

```bash
npm run blockchain:status
```

### 4. Deployment Metadata
Contract addresses and block heights are tracked permanently in:
* `blockchain/deployments/localhost.json`: Full deployment metadata (deployer, tx hash, block number, chain ID, timestamp).
* `blockchain/contract_address.json`: Synchronized address reference for backward compatibility.

### 5. Running the Application Stack

```bash
# Terminal 1: Persistent Blockchain Node
npm run blockchain:start

# Terminal 2: Production Frontend Build & FastAPI Server
npm run frontend:build
python -m uvicorn p2p_energy_trading.server:app --port 8000
```

Open **`http://localhost:8000`** in your browser to interact with the full production React terminal.

*(For frontend development with hot-reload, run `npm run frontend:dev` and open `http://localhost:5173`)*.

### 6. Running Verification Tests

```bash
# Run the integration test (MARL trading + on-chain settlement)
python tests/test_blockchain_settlement.py

# Run the persistence & idempotency test suite
python tests/test_blockchain_persistence.py
```

### 7. Switching to Polygon Amoy Testnet
To deploy and settle on Polygon's Amoy testnet:
1. In `.env`, set:
   ```env
   BLOCKCHAIN_RPC_URL=https://rpc-amoy.polygon.technology
   DEPLOYER_PRIVATE_KEY=<your_funded_amoy_private_key>
   ```
2. Deploy to Amoy:
   ```bash
   cd blockchain
   npm run deploy:amoy
   ```
The frontend automatically detects whether you are running on Localhost or Polygon Amoy and renders explorer links accordingly.

### 8. Resetting or Backing Up Blockchain Data
* **Backup**: Copy the `blockchain/blockchain-data/` directory to preserve your local chain state.
* **Intentional Reset**: Delete `blockchain/blockchain-data/` and `blockchain/deployments/localhost.json`, then re-run `npm run blockchain:start` followed by `npm run blockchain:init`.

---

## Python Setup & Training

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### Data Preparation
```bash
python -m p2p_energy_trading.modules.profile_generator.run
```

### Training
```bash
python -m p2p_energy_trading.training.train --config config/training_config.yaml
```

### Evaluation
```bash
python -m p2p_energy_trading.evaluation.evaluate --checkpoint checkpoints/best_model/
```
