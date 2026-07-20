require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.20",
  networks: {
    // Mumbai was retired by Polygon; Amoy is Polygon's supported replacement testnet.
    amoy: { url: process.env.BLOCKCHAIN_RPC_URL || "", accounts: process.env.DEPLOYER_PRIVATE_KEY ? [process.env.DEPLOYER_PRIVATE_KEY] : [] },
  },
};
