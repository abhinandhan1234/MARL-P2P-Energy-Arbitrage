const fs = require("fs");
const path = require("path");
const ganache = require("ganache");

const DB_PATH = path.resolve(__dirname, "..", "blockchain-data");
const PORT = process.env.PORT || 8545;
const HOST = "127.0.0.1";
const MNEMONIC = "test test test test test test test test test test test junk";

if (!fs.existsSync(DB_PATH)) {
  fs.mkdirSync(DB_PATH, { recursive: true });
}

const server = ganache.server({
  database: {
    dbPath: DB_PATH,
  },
  wallet: {
    mnemonic: MNEMONIC,
    totalAccounts: 25,
    defaultBalance: 1000,
  },
  chain: {
    chainId: 31337,
    networkId: 31337,
  },
  logging: {
    quiet: false,
    verbose: false,
  },
});

server.listen(PORT, HOST, (err) => {
  if (err) {
    console.error("Failed to start persistent blockchain node:", err);
    process.exit(1);
  }
  console.log(`=======================================================`);
  console.log(` Persistent Local Blockchain Node Started Successfully `);
  console.log(`=======================================================`);
  console.log(` RPC Endpoint    : http://${HOST}:${PORT}`);
  console.log(` Chain ID        : 31337 (Hardhat / Localhost compatible)`);
  console.log(` Storage Path    : ${DB_PATH}`);
  console.log(` Accounts Loaded : 25 accounts (funded with 1000 ETH each)`);
  console.log(` State Mode      : PERSISTENT (survives restarts & reboots)`);
  console.log(`=======================================================\n`);
});

const handleExit = async () => {
  console.log("\nGracefully shutting down persistent blockchain node...");
  await server.close();
  console.log("Persistent blockchain state safely committed to disk.");
  process.exit(0);
};

process.on("SIGINT", handleExit);
process.on("SIGTERM", handleExit);
