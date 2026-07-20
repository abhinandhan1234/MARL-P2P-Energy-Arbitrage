const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const EnergyTrading = await hre.ethers.getContractFactory("EnergyTrading");
  const contract = await EnergyTrading.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  const hardhatArtifact = path.join(__dirname, "..", "artifacts", "contracts", "EnergyTrading.sol", "EnergyTrading.json");
  const apiArtifactDir = path.join(__dirname, "..", "artifacts");
  fs.mkdirSync(apiArtifactDir, { recursive: true });
  fs.copyFileSync(hardhatArtifact, path.join(apiArtifactDir, "EnergyTrading.json"));
  const output = { address, network: hre.network.name, deployedAt: new Date().toISOString() };
  fs.writeFileSync(path.join(__dirname, "..", "contract_address.json"), JSON.stringify(output, null, 2));
  console.log(`EnergyTrading deployed to ${address}`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
