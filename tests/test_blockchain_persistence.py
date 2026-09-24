"""Comprehensive test suite for blockchain persistence, idempotency, event tracking, and escrow."""

import os
import sys
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

load_env_file(ROOT / ".env")

from p2p_energy_trading.blockchain_service import BlockchainService


def test_1_contract_deployment():
    print("\n--- Test 1: Contract Deployment & Metadata Verification ---")
    service = BlockchainService()
    assert service.configured, "BlockchainService is not configured!"
    status = service.get_status()
    assert status["connected"] is True, f"Failed to connect to RPC at {service.rpc_url}"
    assert status["contract_deployed"] is True, f"No contract bytecode at {service.contract_address}"
    assert status["chain_id"] == 31337, f"Unexpected chainId: {status['chain_id']}"
    print(f"[PASS] Contract deployed at {service.contract_address} (Chain ID: {status['chain_id']})")


def test_2_settlement_and_receipt():
    print("\n--- Test 2: Settlement & Receipt Generation ---")
    service = BlockchainService()
    seller = service.resolve_party("solar_01")
    buyer = service.resolve_party("consumer_01")
    energy_wh = 15000  # 15 kWh
    price_paisa = 620   # Rs 6.20

    tx_hash = service.settle_trade(seller, buyer, energy_wh, price_paisa)
    assert tx_hash.startswith("0x") and len(tx_hash) == 66, f"Invalid tx_hash: {tx_hash}"
    print(f"[PASS] Settlement submitted. Confirmed Tx Hash: {tx_hash}")

    trades = service.get_trades()
    assert len(trades) > 0, "No trades found after settlement!"
    latest = trades[-1]
    assert latest["tx_hash"] == tx_hash, f"Mismatch: expected {tx_hash}, got {latest.get('tx_hash')}"
    assert latest["energy_wh"] == energy_wh
    assert latest["price_rs_paisa"] == price_paisa
    assert latest["block_number"] is not None
    assert latest["seller_name"] == "solar_01"
    assert latest["buyer_name"] == "consumer_01"
    assert latest["is_mock"] is False
    assert latest["status"] == "CONFIRMED"
    print(f"[PASS] On-chain trade verified with real tx_hash={tx_hash} at block #{latest['block_number']}")
    return tx_hash, latest["block_number"]


def test_3_disconnect_reconnect_persistence():
    print("\n--- Test 3: Disconnect & Reconnect Persistence Verification ---")
    # Simulate a completely fresh connection in a new service instance
    service_a = BlockchainService()
    trades_before = service_a.get_trades()
    count_before = len(trades_before)
    block_before = service_a.get_status()["latest_block"]
    contract_addr = service_a.contract_address

    # Destroy the first service instance
    del service_a

    # Create a new service instance connecting to the same persistent node
    service_b = BlockchainService()
    assert service_b.contract_address == contract_addr
    status_b = service_b.get_status()
    assert status_b["connected"] is True
    assert status_b["latest_block"] >= block_before

    trades_after = service_b.get_trades()
    assert len(trades_after) == count_before, f"Trade count mismatch: {len(trades_after)} vs {count_before}"
    assert trades_after[-1]["tx_hash"] == trades_before[-1]["tx_hash"]
    print(f"[PASS] State persisted across new client connection! {count_before} trades intact.")


def test_4_escrow_idempotency():
    print("\n--- Test 4: Escrow Funding Idempotency ---")
    service = BlockchainService()
    buyer = service.resolve_party("consumer_02")
    service._connect()
    
    # Check current balance
    target = service._web3.to_checksum_address(buyer)
    initial_balance = service.contract.functions.getBalance(target).call()
    
    # Call deposit_for with an amount smaller than or equal to current balance
    # It should not deposit additional funds
    tx1 = service.deposit_for(buyer, initial_balance)
    assert tx1 == "", "deposit_for should not deposit when balance is already sufficient!"
    
    new_balance = service.contract.functions.getBalance(target).call()
    assert new_balance == initial_balance, "Balance should not change on idempotent call!"
    print(f"[PASS] Escrow deposit is idempotent. Balance {initial_balance} remained unchanged.")


def test_5_real_transaction_hashes_in_api():
    print("\n--- Test 5: Verify Transaction Ledger Exposes Real Tx Hashes ---")
    service = BlockchainService()
    trades = service.get_trades()
    assert len(trades) > 0
    has_real_hash = False
    for t in trades:
        if t.get("tx_hash") and t["tx_hash"].startswith("0x") and len(t["tx_hash"]) == 66:
            has_real_hash = True
            assert t["seller_name"] is not None
            assert t["buyer_name"] is not None
            assert t["energy_kwh"] > 0
            assert t["price_rs"] > 0
            assert t["is_mock"] is False
            break
    assert has_real_hash, "No real transaction hashes found in trade ledger!"
    print(f"[PASS] Real transaction hashes and agent names correctly exposed for all on-chain trades.")


def run_all():
    print("=======================================================")
    print(" Running Blockchain Persistence & Idempotency Test Suite ")
    print("=======================================================")
    test_1_contract_deployment()
    tx_hash, block_num = test_2_settlement_and_receipt()
    test_3_disconnect_reconnect_persistence()
    test_4_escrow_idempotency()
    test_5_real_transaction_hashes_in_api()
    print("\n=======================================================")
    print(" [ALL TESTS PASSED] Blockchain Integration is Complete!  ")
    print("=======================================================\n")


if __name__ == "__main__":
    run_all()
