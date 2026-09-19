const { ethers, network } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("----------------------------------------------------");
  console.log("Deploying MonArcadeVault to network:", network.name);
  console.log("----------------------------------------------------");

  const [deployer] = await ethers.getSigners();
  if (!deployer) {
    throw new Error("No deployer account configured. Check PRIVATE_KEY in .env");
  }

  const deployerAddress = await deployer.getAddress();
  console.log("Deployer Address:", deployerAddress);

  const balance = await ethers.provider.getBalance(deployerAddress);
  console.log("Deployer Balance:", ethers.formatEther(balance), "MON");

  if (balance === 0n) {
    throw new Error("Deployer has 0 MON balance. Cannot deploy.");
  }

  const net = await ethers.provider.getNetwork();
  console.log("Target Chain ID:", net.chainId.toString());

  console.log("\nDeploying MonArcadeVault...");
  const MonArcadeVault = await ethers.getContractFactory("MonArcadeVault");
  const vault = await MonArcadeVault.deploy();
  
  console.log("Deployment transaction sent. Waiting for confirmation...");
  await vault.waitForDeployment();

  const contractAddress = await vault.getAddress();
  const deployTx = vault.deploymentTransaction();
  const receipt = await deployTx.wait(1);

  console.log("\n================ DEPLOYMENT SUCCESS ================");
  console.log("Contract Name: MonArcadeVault");
  console.log("Contract Address:", contractAddress);
  console.log("Deployment Tx Hash:", deployTx.hash);
  console.log("Block Number:", receipt.blockNumber);
  console.log("Gas Used:", receipt.gasUsed.toString());
  console.log("====================================================\n");

  // Verify bytecode
  const code = await ethers.provider.getCode(contractAddress);
  if (!code || code === "0x") {
    throw new Error("Bytecode verification failed! No code at deployed address.");
  }
  console.log("Bytecode confirmed on-chain (bytes):", (code.length - 2) / 2);

  // Save deployment artifact
  const deploymentDir = path.resolve(__dirname, "../deployments");
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  const artifactPath = path.resolve(
    __dirname,
    "../artifacts/contracts/MonArcadeVault.sol/MonArcadeVault.json"
  );
  let abi = [];
  if (fs.existsSync(artifactPath)) {
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    abi = artifact.abi;
  }

  const deploymentData = {
    network: network.name,
    chainId: Number(net.chainId),
    contractName: "MonArcadeVault",
    address: contractAddress,
    deployTxHash: deployTx.hash,
    blockNumber: receipt.blockNumber,
    deployer: deployerAddress,
    timestamp: new Date().toISOString(),
    abi: abi,
  };

  const outputPath = path.join(deploymentDir, "monad-testnet.json");
  fs.writeFileSync(outputPath, JSON.stringify(deploymentData, null, 2));
  console.log("Saved deployment metadata to:", outputPath);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Deployment failed:", error);
    process.exit(1);
  });
