import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export default function BlockchainStatus() {
  const { data: status, isLoading } = useQuery({
    queryKey: ["blockchain-status"],
    queryFn: () => api.get("/api/blockchain/status").then((r) => r.data),
    refetchInterval: 5000,
  });

  const isConnected = status?.connected ?? false;
  const network = status?.network === "localhost" ? "Local Hardhat (Persistent)" : status?.network ?? "Unknown";

  return (
    <div className="metrics" style={{ marginBottom: 20 }}>
      <article className="metric">
        <span>BLOCKCHAIN STATUS</span>
        <strong style={{ color: isConnected ? "var(--accent)" : "#ff6b6b" }}>
          {isLoading ? "Checking…" : isConnected ? "Connected" : "Offline"}
        </strong>
        <small>{status?.persistent ? "Storage: Persistent Disk" : "Storage: Memory"}</small>
      </article>

      <article className="metric">
        <span>ACTIVE NETWORK</span>
        <strong>{network}</strong>
        <small>Chain ID: {status?.chain_id ?? "--"}</small>
      </article>

      <article className="metric">
        <span>ESCROW CONTRACT</span>
        <strong style={{ fontSize: 16 }}>
          {status?.contract_address
            ? `${status.contract_address.slice(0, 6)}…${status.contract_address.slice(-4)}`
            : "--"}
        </strong>
        <small>{status?.contract_deployed ? "Verified On-Chain" : "Not Deployed"}</small>
      </article>

      <article className="metric">
        <span>LATEST MINED BLOCK</span>
        <strong>{status?.latest_block != null ? `#${status.latest_block}` : "--"}</strong>
        <small>Total Settled Trades: {status?.total_trades_count ?? 0}</small>
      </article>
    </div>
  );
}
