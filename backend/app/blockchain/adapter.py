from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import uuid


class BlockchainService(ABC):
    """Abstract boundary for blockchain operations.
    
    UI and presentation components must never import or invoke RPC directly.
    """

    @abstractmethod
    async def submit_transaction(self, tx_type: str, user_id: str, amount: float) -> Dict[str, Any]:
        """Submit a game stake, entry fee, or payout transaction."""
        pass

    @abstractmethod
    async def verify_transaction(self, tx_hash: str) -> bool:
        """Verify receipt of an on-chain transaction."""
        pass

    @abstractmethod
    async def get_balance(self, wallet_address: str) -> Dict[str, Any]:
        """Query token balance for a wallet address."""
        pass


class MockBlockchain(BlockchainService):
    """Deterministic local mock blockchain adapter for offline simulation and testing."""

    async def submit_transaction(self, tx_type: str, user_id: str, amount: float) -> Dict[str, Any]:
        tx_hash = f"0xmock_{uuid.uuid4().hex[:16]}"
        return {
            "status": "CONFIRMED",
            "tx_hash": tx_hash,
            "tx_type": tx_type,
            "user_id": user_id,
            "amount": amount,
            "chain": "monad-mock-local",
        }

    async def verify_transaction(self, tx_hash: str) -> bool:
        return tx_hash.startswith("0x")

    async def get_balance(self, wallet_address: str) -> Dict[str, Any]:
        return {
            "wallet_address": wallet_address,
            "balance": 100.0,
            "currency": "MON",
            "is_mock": True,
        }


class MonadBlockchain(BlockchainService):
    """Monad Testnet RPC implementation for onchain settlement and balance queries."""

    VAULT_ABI = [
        {
            "inputs": [{"internalType": "bytes32", "name": "matchId", "type": "bytes32"}],
            "name": "deposit",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "matchId", "type": "bytes32"},
                {"internalType": "address payable", "name": "winner", "type": "address"},
            ],
            "name": "settle",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "bytes32", "name": "matchId", "type": "bytes32"}],
            "name": "getMatch",
            "outputs": [
                {"internalType": "address", "name": "depositor", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "bool", "name": "settled", "type": "bool"},
                {"internalType": "address", "name": "winner", "type": "address"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        chain_id: Optional[int] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
    ):
        from backend.app.config import settings
        self.rpc_url = rpc_url or settings.MONAD_RPC_URL or "https://testnet-rpc.monad.xyz"
        self.chain_id = chain_id or settings.MONAD_CHAIN_ID or 10143
        self.contract_address = (
            contract_address
            or settings.VAULT_CONTRACT_ADDRESS
            or "0x5742Ec7A82D85248C76C266CCA9f61791aA133f6"
        )
        self.private_key = private_key if private_key is not None else settings.PRIVATE_KEY

    def _get_w3(self):
        from web3 import Web3
        return Web3(Web3.HTTPProvider(self.rpc_url))

    async def get_balance(self, wallet_address: str) -> Dict[str, Any]:
        """Query token balance for a wallet address from Monad Testnet."""
        from web3 import Web3
        w3 = self._get_w3()
        try:
            checksum_addr = Web3.to_checksum_address(wallet_address)
            balance_wei = w3.eth.get_balance(checksum_addr)
            balance_mon = float(w3.from_wei(balance_wei, "ether"))
            return {
                "wallet_address": checksum_addr,
                "balance": balance_mon,
                "currency": "MON",
                "is_mock": False,
                "chain_id": self.chain_id,
            }
        except Exception as e:
            return {
                "wallet_address": wallet_address,
                "balance": 0.0,
                "currency": "MON",
                "error": str(e),
                "is_mock": False,
            }

    async def verify_transaction(self, tx_hash: str) -> bool:
        """Verify receipt and confirmation of an on-chain transaction."""
        w3 = self._get_w3()
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            return receipt is not None and receipt.get("status") == 1
        except Exception:
            return False

    async def submit_transaction(self, tx_type: str, user_id: str, amount: float) -> Dict[str, Any]:
        """Submit a game settlement or native MON transfer transaction to Monad Testnet."""
        from web3 import Web3
        from eth_account import Account

        if not self.private_key:
            raise ValueError("PRIVATE_KEY not configured for MonadBlockchain")

        w3 = self._get_w3()
        pk = self.private_key if self.private_key.startswith("0x") else f"0x{self.private_key}"
        account = Account.from_key(pk)

        recipient = user_id if Web3.is_address(user_id) else account.address
        recipient_checksum = Web3.to_checksum_address(recipient)
        nonce = w3.eth.get_transaction_count(account.address, "pending")
        amount_wei = w3.to_wei(amount, "ether") if amount > 0 else 0

        # Construct settlement transaction (native transfer or contract call)
        tx = {
            "chainId": self.chain_id,
            "from": account.address,
            "to": recipient_checksum,
            "value": amount_wei,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": w3.eth.gas_price,
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
        tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = tx_hash_bytes.hex()
        if not tx_hash.startswith("0x"):
            tx_hash = f"0x{tx_hash}"

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        status = "CONFIRMED" if receipt.get("status") == 1 else "FAILED"

        return {
            "status": status,
            "tx_hash": tx_hash,
            "tx_type": tx_type,
            "user_id": user_id,
            "amount": amount,
            "chain": "monad-testnet",
            "contract": self.contract_address,
            "block_number": receipt.get("blockNumber"),
            "explorer_url": f"https://testnet.monadexplorer.com/tx/{tx_hash}",
        }

    async def settle_match_on_chain(self, match_id: str, winner_address: str) -> Dict[str, Any]:
        """Call settle(bytes32, address) on the deployed MonArcadeVault contract."""
        from web3 import Web3
        from eth_account import Account

        if not self.private_key:
            raise ValueError("PRIVATE_KEY not configured for MonadBlockchain")

        w3 = self._get_w3()
        pk = self.private_key if self.private_key.startswith("0x") else f"0x{self.private_key}"
        account = Account.from_key(pk)

        vault_addr = Web3.to_checksum_address(self.contract_address)
        contract = w3.eth.contract(address=vault_addr, abi=self.VAULT_ABI)

        # Match ID as bytes32
        if match_id.startswith("0x") and len(match_id) == 66:
            match_id_bytes = bytes.fromhex(match_id[2:])
        else:
            match_id_bytes = Web3.keccak(text=match_id)

        winner_checksum = Web3.to_checksum_address(winner_address)
        nonce = w3.eth.get_transaction_count(account.address, "pending")

        tx = contract.functions.settle(match_id_bytes, winner_checksum).build_transaction({
            "chainId": self.chain_id,
            "from": account.address,
            "nonce": nonce,
            "gas": 250000,
            "gasPrice": w3.eth.gas_price,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
        tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = tx_hash_bytes.hex()
        if not tx_hash.startswith("0x"):
            tx_hash = f"0x{tx_hash}"

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        status = "CONFIRMED" if receipt.get("status") == 1 else "FAILED"

        return {
            "status": status,
            "tx_hash": tx_hash,
            "match_id": match_id,
            "winner": winner_checksum,
            "block_number": receipt.get("blockNumber"),
            "explorer_url": f"https://testnet.monadexplorer.com/tx/{tx_hash}",
        }


def get_blockchain_service() -> BlockchainService:
    """Factory returning the active BlockchainService based on configuration."""
    from backend.app.config import settings
    if settings.USE_MOCK_BLOCKCHAIN:
        return MockBlockchain()
    return MonadBlockchain()

