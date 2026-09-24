const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  console.log(`\n=======================================================`);
  console.log(`       Blockchain Health & Diagnostic Check            `);
  console.log(`=======================================================`);

  const networkName = hre.network.name;
  let provider;
  try {
    provider = hre.ethers.provider;
    const network = await provider.getNetwork();
    const blockNumber = await provider.getBlockNumber();
    console.log(`[PASS] RPC reachable on network: ${networkName}`);
    console.log(`[PASS] Chain ID: ${network.chainId}`);
    console.log(`[PASS] Latest Block: ${blockNumber}`);
  } catch (err) {
    console.error(`[FAIL] Cannot connect to RPC (${networkName}): ${err.message}`);
    process.exit(1);
  }

  const deploymentFile = path.join(__dirname, "..", "deployments", `${networkName}.json`);
  const contractAddressFile = path.join(__dirname, "..", "contract_address.json");
  let contractAddress = null;
  let metadata = null;

  if (fs.existsSync(deploymentFile)) {
    try {
      metadata = JSON.parse(fs.readFileSync(deploymentFile, "utf-8"));
      contractAddress = metadata.contractAddress;
      console.log(`[PASS] Deployment metadata found in deployments/${networkName}.json`);
    } catch (_) {}
  } else if (fs.existsSync(contractAddressFile)) {
    try {
      metadata = JSON.parse(fs.readFileSync(contractAddressFile, "utf-8"));
      contractAddress = metadata.address;
      console.log(`[PASS] Deployment metadata found in contract_address.json`);
    } catch (_) {}
  }

  if (!contractAddress) {
    console.error(`[FAIL] No deployment metadata found for network: ${networkName}`);
    process.exit(1);
  }

  console.log(`[INFO] Checking contract at ${contractAddress}...`);
  const code = await provider.getCode(contractAddress);
  if (!code || code === "0x" || code === "0x0") {
    console.error(`[FAIL] No contract bytecode found at ${contractAddress}! Has the node been reset?`);
    process.exit(1);
  }
  console.log(`[PASS] Contract bytecode verified on-chain (${code.length / 2 - 1} bytes).`);

  try {
    const EnergyTrading = await hre.ethers.getContractAt("contracts/EnergyTrading.sol:EnergyTrading", contractAddress);
    const operator = await EnergyTrading.settlementOperator();
    console.log(`[PASS] Callable: settlementOperator() -> ${operator}`);

    const trades = await EnergyTrading.getTrades();
    console.log(`[PASS] Callable: getTrades() -> ${trades.length} trade(s) recorded on-chain`);

    const deployerBalance = await EnergyTrading.getBalance(operator);
    console.log(`[PASS] Escrow state readable: operator escrow balance -> ${deployerBalance.toString()} wei`);

    const [signer] = await hre.ethers.getSigners();
    if (signer) {
      const ethBalance = await provider.getBalance(signer.address);
      console.log(`[PASS] Operator native balance: ${hre.ethers.formatEther(ethBalance)} ETH`);
    }

    console.log(`=======================================================`);
    console.log(` [STATUS: HEALTHY] Blockchain & Contract 100% Ready    `);
    console.log(`=======================================================\n`);
  } catch (err) {
    console.error(`[FAIL] Error interacting with EnergyTrading contract: ${err.message}`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Diagnostic failed:", err);
  process.exitCode = 1;
});
