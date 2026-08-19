import os
import sys
import numpy as np
from pathlib import Path

# Add project root and src to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

# Load .env variables
load_env_file(ROOT / ".env")

from p2p_energy_trading.environment.env import P2PEnergyTradingEnv
from p2p_energy_trading.constants import ALL_AGENT_IDS
from p2p_energy_trading.blockchain_service import BlockchainService

def run_test():
    print("Initializing P2PEnergyTradingEnv with blockchain settlement...")
    config = {
        "episode_length": 24,
        "pandapower_bypass": True,
        "grid_buy_rate": 8.15,
        "grid_sell_rate": 3.56,
        "data_dir": "data/processed",
        "eval_mode": True,
        "seed": 42,
        "blockchain_settlement": True,
    }
    
    env = P2PEnergyTradingEnv(config)
    
    assert env.blockchain_settlement is True
    assert env.blockchain is not None
    assert env.blockchain.configured is True
    
    print("Blockchain configured successfully!")
    
    # Reset env
    obs, info = env.reset(seed=42)
    
    print("Stepping environment to trigger P2P trading and on-chain settlements...")
    for step in range(1, 6):
        # We want to force trading: we'll have sellers sell fully (action[1] = 1.0)
        # and buyers buy fully (action[0] = 1.0)
        actions = {}
        for aid in ALL_AGENT_IDS:
            actions[aid] = np.array([1.0, 1.0, 0.5], dtype=np.float32)
            
        obs, rewards, terminated, truncated, info = env.step(actions)
        print(f"Step {step} complete.")
        
    print("Reading settled trades from the smart contract...")
    service = BlockchainService()
    trades = service.get_trades()
    print(f"Retrieved {len(trades)} trades from blockchain ledger:")
    for t in trades[:10]:
        print(f"Trade ID: {t['trade_id']}, Seller: {t['seller']}, Buyer: {t['buyer']}, Energy: {t['energy_wh']} Wh, Price: {t['price_paisa']} Paisa")
        
    assert len(trades) > 0, "No trades were settled on-chain!"
    print("[OK] Blockchain Settlement Integration Test Passed successfully!")
    env.close()

if __name__ == "__main__":
    run_test()
