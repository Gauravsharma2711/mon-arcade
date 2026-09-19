import { http, createConfig } from 'wagmi';
import { defineChain } from 'viem';

// Monad Devnet / Local Mock Chain definition
export const monadDevnet = defineChain({
  id: 10143,
  name: 'Monad Testnet (Mock)',
  nativeCurrency: {
    decimals: 18,
    name: 'MON',
    symbol: 'MON',
  },
  rpcUrls: {
    default: { http: ['https://rpc.monad.xyz'] },
  },
  blockExplorers: {
    default: { name: 'MonadExplorer', url: 'https://explorer.monad.xyz' },
  },
  testnet: true,
});

export const wagmiConfig = createConfig({
  chains: [monadDevnet],
  transports: {
    [monadDevnet.id]: http(),
  },
});
