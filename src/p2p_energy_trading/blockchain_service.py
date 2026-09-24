"""Web3 adapter for persistent on-chain P2P energy settlement and telemetry."""

from __future__ import annotations

# standard library
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BlockchainUnavailable(RuntimeError):
    """Raised when blockchain settlement has not been configured or is unreachable."""


class BlockchainService:
    """Submit EnergyTrading settlements and read its immutable ledger."""

    def __init__(
        self,
        rpc_url: str | None = None,
        contract_address: str | None = None,
        private_key: str | None = None,
        artifact_path: str | Path | None = None,
    ) -> None:
        self.rpc_url = rpc_url or os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545")
        self.private_key = private_key or os.getenv(
            "DEPLOYER_PRIVATE_KEY",
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        )
        self.contract_address = contract_address or self._resolve_contract_address()
        
        # Artifact path resolution
        if artifact_path:
            self.artifact_path = Path(artifact_path)
        else:
            root = Path(__file__).resolve().parents[2]
            hh_artifact = root / "blockchain" / "artifacts" / "contracts" / "EnergyTrading.sol" / "EnergyTrading.json"
            direct_artifact = root / "blockchain" / "artifacts" / "EnergyTrading.json"
            if hh_artifact.exists():
                self.artifact_path = hh_artifact
                # Keep direct artifact synced for backward compatibility
                try:
                    import shutil
                    direct_artifact.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(hh_artifact, direct_artifact)
                except Exception:
                    pass
            else:
                self.artifact_path = direct_artifact

        self._web3: Any | None = None
        self.contract: Any | None = None
        self.account: Any | None = None
        
        # Agent address mappings
        self._agent_to_wallet: dict[str, str] = {}
        self._wallet_to_agent: dict[str, str] = {}
        self._load_agent_wallets()

        # Cache of locally submitted transactions: trade_signature -> tx_hash
        self._settlement_cache: dict[str, str] = {}

    def _resolve_contract_address(self) -> str:
        """Find the contract address from deployment metadata or environment."""
        env_addr = os.getenv("CONTRACT_ADDRESS", "")
        if env_addr and env_addr != "0x0000000000000000000000000000000000000000":
            return env_addr

        # Try deployments/localhost.json or deployments/amoy.json
        root = Path(__file__).resolve().parents[2]
        deployments_dir = root / "blockchain" / "deployments"
        for net in ["localhost", "amoy"]:
            meta_file = deployments_dir / f"{net}.json"
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    addr = data.get("contractAddress")
                    if addr and addr != "0x0000000000000000000000000000000000000000":
                        return addr
                except Exception:
                    pass

        # Try contract_address.json
        contract_file = root / "blockchain" / "contract_address.json"
        if contract_file.exists():
            try:
                data = json.loads(contract_file.read_text(encoding="utf-8"))
                addr = data.get("address")
                if addr and addr != "0x0000000000000000000000000000000000000000":
                    return addr
            except Exception:
                pass

        return ""

    def _load_agent_wallets(self) -> None:
        """Load bidirectional mapping between agent names and wallet addresses."""
        mapping_path = os.getenv("AGENT_WALLETS_FILE", "blockchain/agent_wallets.json")
        path = Path(mapping_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path

        if not path.exists():
            return

        try:
            from web3 import Web3
            wallets = json.loads(path.read_text(encoding="utf-8"))
            for aid, addr in wallets.items():
                if isinstance(addr, str) and addr.startswith("0x"):
                    checksum_addr = Web3.to_checksum_address(addr)
                    self._agent_to_wallet[aid] = checksum_addr
                    self._wallet_to_agent[checksum_addr.lower()] = aid
                    self._wallet_to_agent[checksum_addr] = aid
        except Exception as exc:
            logger.warning("Could not load agent wallets: %s", exc)

    def resolve_party(self, agent_id: str) -> str:
        """Resolve a terminal agent ID to its configured settlement wallet."""
        if agent_id in self._agent_to_wallet:
            return self._agent_to_wallet[agent_id]
        
        # Reload just in case
        self._load_agent_wallets()
        if agent_id in self._agent_to_wallet:
            return self._agent_to_wallet[agent_id]

        raise BlockchainUnavailable(
            f"Agent ID '{agent_id}' is not mapped to an Ethereum wallet in agent_wallets.json."
        )

    def resolve_agent_name(self, address: str) -> str:
        """Resolve a wallet address to a human-readable agent name."""
        if not address:
            return "Unknown"
        clean = address.lower()
        if clean in self._wallet_to_agent:
            return self._wallet_to_agent[clean]
        # Return shortened address if unknown
        return f"{address[:6]}...{address[-4:]}"

    @property
    def configured(self) -> bool:
        if not self.contract_address:
            self.contract_address = self._resolve_contract_address()
        return bool(
            self.rpc_url
            and self.contract_address
            and self.contract_address != "0x0000000000000000000000000000000000000000"
            and self.private_key
            and not self.private_key.startswith("your_")
            and self.artifact_path.exists()
        )

    def _connect(self) -> None:
        """Establish connection to the persistent EVM node and instantiate the contract."""
        if self.contract is not None:
            return
        if not self.configured:
            raise BlockchainUnavailable(
                "Blockchain is not configured. Set RPC URL, contract address, "
                "private key, and compile EnergyTrading.sol first."
            )
        try:
            from web3 import Web3
        except ImportError as exc:
            raise BlockchainUnavailable("Install web3 to enable on-chain settlement.") from exc

        try:
            artifact = json.loads(self.artifact_path.read_text(encoding="utf-8"))
            self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not self._web3.is_connected():
                raise BlockchainUnavailable(
                    f"Unable to connect to the configured blockchain RPC at {self.rpc_url}. "
                    "Ensure the persistent node is running."
                )

            # Ensure contract has bytecode
            checksum_addr = Web3.to_checksum_address(self.contract_address)
            code = self._web3.eth.get_code(checksum_addr)
            if not code or code == b"" or code == b"\x00":
                raise BlockchainUnavailable(
                    f"No contract bytecode found at {checksum_addr} on {self.rpc_url}. "
                    "Run 'npm run blockchain:init' to deploy the contract."
                )

            self.contract = self._web3.eth.contract(address=checksum_addr, abi=artifact["abi"])
            self.account = self._web3.eth.account.from_key(self.private_key)
        except BlockchainUnavailable:
            raise
        except Exception as exc:
            raise BlockchainUnavailable(f"Error connecting to blockchain: {exc}") from exc

    def deposit_for(self, user_address: str, amount_wei: int) -> str:
        """Idempotently deposit funds into the contract for a user's escrow balance."""
        self._connect()
        assert self._web3 is not None and self.contract is not None and self.account is not None
        
        target = self._web3.to_checksum_address(user_address)
        current_balance = self.contract.functions.getBalance(target).call()
        if current_balance >= amount_wei:
            # Already sufficiently funded
            return ""

        diff = amount_wei - current_balance
        transaction = self.contract.functions.depositFor(target).build_transaction(
            {
                "from": self.account.address,
                "nonce": self._web3.eth.get_transaction_count(self.account.address),
                "chainId": self._web3.eth.chain_id,
                "value": diff,
            }
        )
        signed = self.account.sign_transaction(transaction)
        tx_hash = self._web3.eth.send_raw_transaction(signed.raw_transaction)
        self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=15)
        return self._web3.to_hex(tx_hash)

    def settle_trade(
        self, seller: str, buyer: str, energy_wh: int, price_paisa: int
    ) -> str:
        """Submit an idempotent settlement transaction and return its confirmed transaction hash."""
        self._connect()
        assert self._web3 is not None and self.contract is not None and self.account is not None

        seller_checksum = self._web3.to_checksum_address(seller)
        buyer_checksum = self._web3.to_checksum_address(buyer)
        required_amount = int(energy_wh * price_paisa)

        # Idempotent Escrow Funding: Check buyer balance before depositing
        try:
            current_balance = self.contract.functions.getBalance(buyer_checksum).call()
        except Exception:
            current_balance = 0

        if current_balance < required_amount:
            needed = required_amount - current_balance
            deposit_amount = max(needed, 10**15)  # 0.001 ETH buffer
            try:
                deposit_tx = self.contract.functions.depositFor(buyer_checksum).build_transaction(
                    {
                        "from": self.account.address,
                        "nonce": self._web3.eth.get_transaction_count(self.account.address),
                        "chainId": self._web3.eth.chain_id,
                        "value": deposit_amount,
                    }
                )
                signed_deposit = self.account.sign_transaction(deposit_tx)
                deposit_hash = self._web3.eth.send_raw_transaction(signed_deposit.raw_transaction)
                self._web3.eth.wait_for_transaction_receipt(deposit_hash, timeout=15)
            except Exception as e:
                logger.warning("Auto-escrow deposit warning: %s", e)

        # Submit settlement transaction
        transaction = self.contract.functions.settleTrade(
            seller_checksum,
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
        raw_tx = self._web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._web3.eth.wait_for_transaction_receipt(raw_tx, timeout=15)
        
        tx_hash_hex = self._web3.to_hex(receipt.transactionHash)
        return tx_hash_hex

    def get_trades(self) -> list[dict[str, Any]]:
        """Return all contract trades enriched with on-chain event logs and real transaction hashes."""
        self._connect()
        assert self.contract is not None and self._web3 is not None
        
        # 1. Fetch raw trade rows from smart contract state
        rows = self.contract.functions.getTrades().call()
        if not rows:
            return []

        # 2. Query TradeSettled events to extract real transaction hashes and block numbers
        event_map: dict[int, dict[str, Any]] = {}
        try:
            events = self.contract.events.TradeSettled().get_logs(from_block=0)
            for event in events:
                args = event.get("args", {})
                trade_id = args.get("tradeId")
                tx_hash = self._web3.to_hex(event.get("transactionHash"))
                block_num = event.get("blockNumber")
                if trade_id is not None:
                    event_map[int(trade_id)] = {
                        "tx_hash": tx_hash,
                        "block_number": block_num,
                    }
        except Exception as exc:
            logger.warning("Could not query TradeSettled events: %s", exc)

        # 3. Assemble complete trade records
        result: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            seller_addr = self._web3.to_checksum_address(row[0])
            buyer_addr = self._web3.to_checksum_address(row[1])
            energy_wh = int(row[2])
            price_paisa = int(row[3])
            timestamp = int(row[4])
            settled = bool(row[5])

            ev = event_map.get(index, {})
            tx_hash = ev.get("tx_hash")
            block_number = ev.get("block_number")

            volume_kwh = round(energy_wh / 1000.0, 3)
            price_rs = round(price_paisa / 100.0, 2)
            amount_rs = round(volume_kwh * price_rs, 2)

            result.append(
                {
                    "trade_id": index,
                    "seller": seller_addr,
                    "seller_name": self.resolve_agent_name(seller_addr),
                    "buyer": buyer_addr,
                    "buyer_name": self.resolve_agent_name(buyer_addr),
                    "energy_wh": energy_wh,
                    "energy_kwh": volume_kwh,
                    "volume_kwh": volume_kwh,  # backward compatibility
                    "price_paisa": price_paisa,
                    "price_rs_paisa": price_paisa,
                    "price_rs": price_rs,
                    "price_rs_per_kwh": price_rs,  # backward compatibility
                    "amount_rs": amount_rs,
                    "timestamp": timestamp,
                    "settled": settled,
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                    "status": "CONFIRMED" if settled else "PENDING",
                    "is_mock": False,
                }
            )

        return result

    def get_status(self) -> dict[str, Any]:
        """Return connectivity, persistence, and contract configuration details."""
        if not self.contract_address:
            self.contract_address = self._resolve_contract_address()

        network_name = (
            "localhost"
            if ("127.0.0.1" in self.rpc_url or "localhost" in self.rpc_url)
            else "amoy"
        )
        info: dict[str, Any] = {
            "connected": False,
            "configured": self.configured,
            "network": network_name,
            "chain_id": None,
            "rpc_url": self.rpc_url,
            "contract_address": self.contract_address,
            "contract_deployed": False,
            "latest_block": None,
            "deployment_block": None,
            "persistent": True,
            "operator_address": "",
            "operator_balance_eth": 0.0,
            "total_trades_count": 0,
        }

        # Try reading deployment metadata for deployment block
        root = Path(__file__).resolve().parents[2]
        meta_file = root / "blockchain" / "deployments" / f"{network_name}.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                info["deployment_block"] = meta.get("deploymentBlock")
            except Exception:
                pass

        if self.configured:
            try:
                self._connect()
                if self._web3 and self._web3.is_connected():
                    info["connected"] = True
                    info["chain_id"] = self._web3.eth.chain_id
                    info["latest_block"] = self._web3.eth.block_number
                    if self.contract:
                        info["contract_deployed"] = True
                        try:
                            trades = self.contract.functions.getTrades().call()
                            info["total_trades_count"] = len(trades)
                        except Exception:
                            pass
                    if self.account:
                        info["operator_address"] = self.account.address
                        balance_wei = self._web3.eth.get_balance(self.account.address)
                        info["operator_balance_eth"] = round(float(balance_wei) / 10**18, 4)
            except Exception as exc:
                info["connected"] = False
                info["error"] = str(exc)

        return info
