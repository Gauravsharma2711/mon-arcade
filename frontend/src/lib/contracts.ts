export const MON_ARCADE_VAULT_ADDRESS = '0x5742Ec7A82D85248C76C266CCA9f61791aA133f6' as const;

export const MON_ARCADE_VAULT_ABI = [
  {
    inputs: [],
    stateMutability: 'nonpayable',
    type: 'constructor',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'bytes32', name: 'matchId', type: 'bytes32' },
      { indexed: true, internalType: 'address', name: 'depositor', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'amount', type: 'uint256' },
    ],
    name: 'MatchDeposited',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'bytes32', name: 'matchId', type: 'bytes32' },
      { indexed: true, internalType: 'address', name: 'winner', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'payout', type: 'uint256' },
    ],
    name: 'MatchSettled',
    type: 'event',
  },
  {
    inputs: [{ internalType: 'bytes32', name: 'matchId', type: 'bytes32' }],
    name: 'deposit',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [
      { internalType: 'bytes32', name: 'matchId', type: 'bytes32' },
      { internalType: 'address payable', name: 'winner', type: 'address' },
    ],
    name: 'settle',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'bytes32', name: 'matchId', type: 'bytes32' }],
    name: 'getMatch',
    outputs: [
      { internalType: 'address', name: 'depositor', type: 'address' },
      { internalType: 'uint256', name: 'amount', type: 'uint256' },
      { internalType: 'bool', name: 'settled', type: 'bool' },
      { internalType: 'address', name: 'winner', type: 'address' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'totalEscrowed',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
] as const;
