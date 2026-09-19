require("@nomicfoundation/hardhat-toolbox");
const path = require("path");
const fs = require("fs");

// Load .env from root or local
const rootEnvPath = path.resolve(__dirname, "../.env");
if (fs.existsSync(rootEnvPath)) {
  require("dotenv").config({ path: rootEnvPath });
} else {
  require("dotenv").config();
}

const RPC_URL = process.env.MONAD_RPC_URL || "https://testnet-rpc.monad.xyz";
const CHAIN_ID = parseInt(process.env.MONAD_CHAIN_ID || "10143", 10);
let rawPk = process.env.PRIVATE_KEY || "";
if (rawPk && !rawPk.startsWith("0x")) {
  rawPk = "0x" + rawPk;
}
const accounts = rawPk.length === 66 ? [rawPk] : [];

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {},
    monadTestnet: {
      url: RPC_URL,
      chainId: CHAIN_ID,
      accounts: accounts,
    },
  },
  sourcify: {
    enabled: true,
  },
  etherscan: {
    apiKey: {
      monadTestnet: process.env.MONAD_EXPLORER_API_KEY || "dummy",
    },
    customChains: [
      {
        network: "monadTestnet",
        chainId: CHAIN_ID,
        urls: {
          apiURL: "https://testnet.monadexplorer.com/api",
          browserURL: "https://testnet.monadexplorer.com",
        },
      },
    ],
  },
};
