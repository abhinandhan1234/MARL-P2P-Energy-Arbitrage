import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";

export default function TransactionLedger() {
  const [copiedTx, setCopiedTx] = useState(null);

  const { data: status } = useQuery({
    queryKey: ["blockchain-status"],
    queryFn: () => api.get("/api/blockchain/status").then((r) => r.data),
    refetchInterval: 5000,
  });

  const { data = [], isLoading, error } = useQuery({
    queryKey: ["transactions"],
    queryFn: () => api.get("/api/blockchain/transactions").then((r) => r.data),
    refetchInterval: 5000,
  });

  const isAmoy = status?.network === "amoy";

  const copyToClipboard = (text) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedTx(text);
    setTimeout(() => setCopiedTx(null), 2000);
  };

  if (error) {
    return <section className="card error">Unable to load the transaction ledger.</section>;
  }

  return (
    <section className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>
          On-chain transaction ledger <span>{data.length} records</span>
        </h3>
        {copiedTx && (
          <span style={{ fontSize: 10, color: "var(--accent)", fontStyle: "italic" }}>
            Hash copied to clipboard!
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="spinner" />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Seller Agent</th>
                <th>Buyer Agent</th>
                <th>Energy</th>
                <th>Price</th>
                <th>Total (Rs)</th>
                <th>Block</th>
                <th>Transaction Hash</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((t, i) => {
                const tradeId = t.trade_id !== undefined ? `#${t.trade_id}` : `#${i}`;
                const sellerName = t.seller_name || t.seller || "Unknown";
                const buyerName = t.buyer_name || t.buyer || "Unknown";
                const sellerAddr = t.seller && t.seller.startsWith("0x") ? `${t.seller.slice(0, 6)}…${t.seller.slice(-4)}` : "";
                const buyerAddr = t.buyer && t.buyer.startsWith("0x") ? `${t.buyer.slice(0, 6)}…${t.buyer.slice(-4)}` : "";

                const energy = (t.energy_kwh ?? t.volume_kwh ?? (t.energy_wh ? t.energy_wh / 1000 : 0))?.toFixed(2);
                const price = (t.price_rs ?? t.price_rs_per_kwh ?? (t.price_paisa ? t.price_paisa / 100 : 0))?.toFixed(2);
                const amount = t.amount_rs !== undefined ? t.amount_rs.toFixed(2) : (energy * price).toFixed(2);
                const blockNum = t.block_number != null ? `#${t.block_number}` : "--";

                const txHash = t.tx_hash;
                const isMock = t.is_mock || t.status === "HISTORICAL_MOCK";

                return (
                  <tr key={t.tx_hash || t.trade_id || i}>
                    <td><b>{tradeId}</b></td>
                    <td>
                      <div><b>{sellerName}</b></div>
                      {sellerAddr && <small style={{ color: "var(--text-muted)", fontSize: 9 }}>{sellerAddr}</small>}
                    </td>
                    <td>
                      <div><b>{buyerName}</b></div>
                      {buyerAddr && <small style={{ color: "var(--text-muted)", fontSize: 9 }}>{buyerAddr}</small>}
                    </td>
                    <td>{energy} kWh</td>
                    <td>Rs {price}</td>
                    <td>Rs {amount}</td>
                    <td>{blockNum}</td>
                    <td>
                      {txHash ? (
                        isAmoy ? (
                          <a
                            target="_blank"
                            rel="noreferrer"
                            href={`https://amoy.polygonscan.com/tx/${txHash}`}
                            title="View on PolygonScan Amoy"
                          >
                            {txHash.slice(0, 8)}…{txHash.slice(-6)} ↗
                          </a>
                        ) : (
                          <span
                            onClick={() => copyToClipboard(txHash)}
                            style={{ cursor: "pointer", textDecoration: "underline dotted" }}
                            title="Local Hardhat node transaction. Click to copy full hash."
                          >
                            {txHash.slice(0, 8)}…{txHash.slice(-6)}
                          </span>
                        )
                      ) : (
                        "--"
                      )}
                    </td>
                    <td>
                      {isMock ? (
                        <span className="tag" style={{ background: "rgba(247,197,58,0.15)", color: "#f7c53a" }}>
                          HISTORICAL MOCK
                        </span>
                      ) : (
                        <span className="tag" style={{ background: "rgba(200,247,58,0.12)", color: "var(--accent)" }}>
                          CONFIRMED
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!data.length && (
                <tr>
                  <td colSpan="9" className="empty" style={{ textAlign: "center", padding: "28px 0" }}>
                    No on-chain settlements yet. Submit orders in Marketplace or run MARL evaluation to settle trades.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
