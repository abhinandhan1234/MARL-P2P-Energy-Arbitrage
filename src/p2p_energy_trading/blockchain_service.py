"""Small, optional Web3 adapter used by the FastAPI settlement endpoint.

The application remains usable without chain credentials.  In that case this
service reports a clear configuration error rather than fabricating a hash.
"""

from __future__ import annotations

# standard library
import json
import os
from pathlib import Path
from typing import Any


class BlockchainUnavailable(RuntimeError):
    """Raised when blockchain settlement has not been configured."""


class BlockchainService:
    """Submit EnergyTrading settlements and read its immutable ledger."""

    def __init__(
        self,
        rpc_url: str | None = None,
        contract_address: str | None = None,
        private_key: str | None = None,
        artifact_path: str | Path = "blockchain/artifacts/EnergyTrading.json",
    ) -> None:
        self.rpc_url = rpc_url or os.getenv("BLOCKCHAIN_RPC_URL", "")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS", "")
        self.private_key = private_key or os.getenv("DEPLOYER_PRIVATE_KEY", "")
        self.artifact_path = Path(artifact_path)
        self._web3: Any | None = None
        self.contract: Any | None = None
        self.account: Any | None = None

    def resolve_party(self, agent_id: str) -> str:
        """Resolve a terminal agent ID to its configured settlement wallet."""
        mapping_path = os.getenv("AGENT_WALLETS_FILE", "blockchain/agent_wallets.json")
        path = Path(mapping_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            wallets = json.loads(path.read_text(encoding="utf-8"))
            wallet = wallets[agent_id]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
            raise BlockchainUnavailable(
                "Create blockchain/agent_wallets.json with an Ethereum address "
                "for every settled agent, or set AGENT_WALLETS_FILE."
            ) from exc
        return wallet

    @property
    def configured(self) -> bool:
        return bool(
            self.rpc_url
            and self.contract_address
            and self.contract_address != "0x0000000000000000000000000000000000000000"
            and self.private_key
            and not self.private_key.startswith("your_")
            and self.artifact_path.exists()
        )

    def _connect(self) -> None:
        if self.contract is not None:
            return
        if not self.configured:
            raise BlockchainUnavailable(
                "Blockchain is not configured. Set RPC URL, contract address, "
                "private key, and compile EnergyTrading.sol first."
            )
        try:
            # third party
            from web3 import Web3
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise BlockchainUnavailable(
                "Install web3 to enable on-chain settlement."
            ) from exc

        artifact = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self._web3.is_connected():
            raise BlockchainUnavailable(
                "Unable to connect to the configured blockchain RPC."
            )
        self.contract = self._web3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address), abi=artifact["abi"]
        )
        self.account = self._web3.eth.account.from_key(self.private_key)

    def deposit_for(self, user_address: str, amount_wei: int) -> str:
        """Deposit funds into the contract for a specific user's escrow balance."""
        self._connect()
        assert (
            self._web3 is not None
            and self.contract is not None
            and self.account is not None
        )
        transaction = self.contract.functions.depositFor(
            self._web3.to_checksum_address(user_address)
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": self._web3.eth.get_transaction_count(self.account.address),
                "chainId": self._web3.eth.chain_id,
                "value": amount_wei,
            }
        )
        signed = self.account.sign_transaction(transaction)
        tx_hash = self._web3.eth.send_raw_transaction(signed.raw_transaction)
        return self._web3.to_hex(tx_hash)

    def settle_trade(
        self, seller: str, buyer: str, energy_wh: int, price_paisa: int
    ) -> str:
        """Submit a settlement transaction and return its transaction hash."""
        self._connect()
        assert (
            self._web3 is not None
            and self.contract is not None
            and self.account is not None
        )
        
        buyer_checksum = self._web3.to_checksum_address(buyer)
        required_amount = energy_wh * price_paisa
        
        try:
            current_balance = self.contract.functions.getBalance(buyer_checksum).call()
        except Exception:
            current_balance = 0
            
        if current_balance < required_amount:
            needed = required_amount - current_balance
            deposit_amount = max(needed, 10**15)  # minimum 0.001 ETH buffer
            try:
                deposit_tx = self.contract.functions.depositFor(
                    buyer_checksum
                ).build_transaction(
                    {
                        "from": self.account.address,
                        "nonce": self._web3.eth.get_transaction_count(self.account.address),
                        "chainId": self._web3.eth.chain_id,
                        "value": deposit_amount,
                    }
                )
                signed_deposit = self.account.sign_transaction(deposit_tx)
                deposit_hash = self._web3.eth.send_raw_transaction(signed_deposit.raw_transaction)
                self._web3.eth.wait_for_transaction_receipt(deposit_hash)
            except Exception as e:
                # If auto-funding fails, log it and proceed (settleTrade might still succeed if buyer had enough)
                pass

        transaction = self.contract.functions.settleTrade(
            self._web3.to_checksum_address(seller),
            buyer_checksum,
            energy_wh,
            price_paisa,
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": self._web3.eth.get_transaction_count(self.account.address),
                "chainId": self._web3.eth.chain_id,
            }
        )
        signed = self.account.sign_transaction(transaction)
        return self._web3.to_hex(
            self._web3.eth.send_raw_transaction(signed.raw_transaction)
        )

    def get_trades(self) -> list[dict[str, Any]]:
        """Return all contract trades in a JSON-friendly representation."""
        self._connect()
        assert self.contract is not None
        rows = self.contract.functions.getTrades().call()
        return [
            {
                "trade_id": index,
                "seller": row[0],
                "buyer": row[1],
                "energy_wh": int(row[2]),
                "price_paisa": int(row[3]),
                "timestamp": int(row[4]),
                "settled": bool(row[5]),
            }
            for index, row in enumerate(rows)
        ]

    def get_status(self) -> dict[str, Any]:
        """Return connectivity and configuration status information."""
        configured = self.configured
        info = {
            "configured": configured,
            "contract_address": self.contract_address,
            "rpc_url": self.rpc_url,
            "operator_address": "",
            "operator_balance_eth": 0.0,
        }
        if configured:
            try:
                self._connect()
                if self.account and self._web3:
                    info["operator_address"] = self.account.address
                    balance_wei = self._web3.eth.get_balance(self.account.address)
                    info["operator_balance_eth"] = float(balance_wei) / 10**18
            except Exception:
                pass
        return info


