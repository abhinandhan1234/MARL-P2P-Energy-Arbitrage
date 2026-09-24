const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const networkName = hre.network.name;
  const deploymentsDir = path.join(__dirname, "..", "deployments");
  const deploymentFile = path.join(deploymentsDir, `${networkName}.json`);
  const contractAddressFile = path.join(__dirname, "..", "contract_address.json");
  const hardhatArtifact = path.join(__dirname, "..", "artifacts", "contracts", "EnergyTrading.sol", "EnergyTrading.json");
  const apiArtifactDir = path.join(__dirname, "..", "artifacts");
  const apiArtifactFile = path.join(apiArtifactDir, "EnergyTrading.json");

  fs.mkdirSync(deploymentsDir, { recursive: true });
  fs.mkdirSync(apiArtifactDir, { recursive: true });

  // Always keep backend ABI artifact up to date if compiled
  if (fs.existsSync(hardhatArtifact)) {
    fs.copyFileSync(hardhatArtifact, apiArtifactFile);
  }

  // Check if contract is already deployed and verified on-chain
  let existingAddress = null;
  if (fs.existsSync(deploymentFile)) {
    try {
      const meta = JSON.parse(fs.readFileSync(deploymentFile, "utf-8"));
      existingAddress = meta.contractAddress;
    } catch (_) {}
  } else if (fs.existsSync(contractAddressFile)) {
    try {
      const meta = JSON.parse(fs.readFileSync(contractAddressFile, "utf-8"));
      existingAddress = meta.address;
    } catch (_) {}
  }

  const [deployer] = await hre.ethers.getSigners();
  const network = await hre.ethers.provider.getNetwork();

  if (existingAddress) {
    try {
      const code = await hre.ethers.provider.getCode(existingAddress);
      if (code && code !== "0x" && code !== "0x0") {
        console.log(`\n=======================================================`);
        console.log(` [IDEMPOTENT] Contract Already Deployed & Verified`);
        console.log(`=======================================================`);
        console.log(` Network          : ${networkName} (Chain ID: ${network.chainId})`);
        console.log(` Contract Address : ${existingAddress}`);
        console.log(` Deployer Account : ${deployer ? deployer.address : "N/A"}`);
        console.log(` Status           : Bytecode verified on-chain. Skipping redeployment.`);
        console.log(`=======================================================\n`);
        return;
      } else {
        console.warn(`[WARN] Saved address ${existingAddress} has no bytecode on network "${networkName}". Proceeding with new deployment.`);
      }
    } catch (err) {
      console.warn(`[WARN] Could not check code at ${existingAddress}: ${err.message}. Proceeding with deployment.`);
    }
  }

  console.log(`Deploying EnergyTrading to ${networkName} via ${deployer.address}...`);
  const EnergyTrading = await hre.ethers.getContractFactory("contracts/EnergyTrading.sol:EnergyTrading");
  const contract = await EnergyTrading.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const deployTx = contract.deploymentTransaction();
  const receipt = await deployTx.wait();

  // Re-copy artifact just in case
  if (fs.existsSync(hardhatArtifact)) {
    fs.copyFileSync(hardhatArtifact, apiArtifactFile);
  }

  const metadata = {
    network: networkName,
    chainId: network.chainId.toString(),
    contractAddress: address,
    deployer: deployTx.from,
    deploymentBlock: receipt.blockNumber,
    deploymentTx: deployTx.hash,
    timestamp: new Date().toISOString(),
  };

  fs.writeFileSync(deploymentFile, JSON.stringify(metadata, null, 2), "utf-8");
  fs.writeFileSync(contractAddressFile, JSON.stringify({
    address: address,
    network: networkName,
    deployedAt: metadata.timestamp,
  }, null, 2), "utf-8");

  // Sync to root .env if it exists
  const envPath = path.resolve(__dirname, "..", "..", ".env");
  if (fs.existsSync(envPath)) {
    let envContent = fs.readFileSync(envPath, "utf-8");
    if (envContent.includes("CONTRACT_ADDRESS=")) {
      envContent = envContent.replace(/CONTRACT_ADDRESS=0x[a-fA-F0-9]+/g, `CONTRACT_ADDRESS=${address}`);
    } else {
      envContent += `\nCONTRACT_ADDRESS=${address}`;
    }
    if (envContent.includes("VITE_CONTRACT_ADDRESS=")) {
      envContent = envContent.replace(/VITE_CONTRACT_ADDRESS=0x[a-fA-F0-9]+/g, `VITE_CONTRACT_ADDRESS=${address}`);
    }
    fs.writeFileSync(envPath, envContent, "utf-8");
  }

  console.log(`\n=======================================================`);
  console.log(` EnergyTrading Successfully Deployed & Persisted `);
  console.log(`=======================================================`);
  console.log(` Network          : ${networkName} (Chain ID: ${network.chainId})`);
  console.log(` Contract Address : ${address}`);
  console.log(` Deployer         : ${deployTx.from}`);
  console.log(` Deployment Block : ${receipt.blockNumber}`);
  console.log(` Deployment Tx    : ${deployTx.hash}`);
  console.log(` Metadata Saved   : ${deploymentFile}`);
  console.log(`=======================================================\n`);
}

main().catch((error) => {
  console.error("Deployment failed:", error);
  process.exitCode = 1;
});
