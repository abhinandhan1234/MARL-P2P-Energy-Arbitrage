import { motion } from "framer-motion";
import BlockchainStatus from "../components/Blockchain/BlockchainStatus";
import SettleButton from "../components/Blockchain/SettleButton";
import TransactionLedger from "../components/Blockchain/TransactionLedger";
import WalletConnect from "../components/Blockchain/WalletConnect";

export default function Blockchain() {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="page">
      <div className="page-title">
        <div>
          <p>IMMUTABLE ESCROW & SETTLEMENT</p>
          <h1>Settlement ledger</h1>
        </div>
        <WalletConnect />
      </div>

      <BlockchainStatus />

      <section className="card settlement">
        <div>
          <h3 style={{ margin: "0 0 6px" }}>Pending P2P order settlement</h3>
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-muted)" }}>
            Execute pending market matches on-chain through the persistent EnergyTrading smart contract.
          </p>
        </div>
        <SettleButton />
      </section>

      <TransactionLedger />
    </motion.div>
  );
}
