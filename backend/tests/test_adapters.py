import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.blockchain import (
    BlockchainService,
    MockBlockchain,
    MonadBlockchain,
    get_blockchain_service,
)
from backend.app.ai import (
    AgentProvider,
    MockAgentProvider,
    LLMAgentProvider,
    get_agent_provider,
)
from backend.app.sponsor import (
    SponsorResolver,
    get_sponsor_resolver,
)


class TestBlockchainBoundary:
    def test_mock_blockchain_implementation(self):
        """MockBlockchain must provide functional local transactions without Monad RPC."""
        service = MockBlockchain()
        assert isinstance(service, BlockchainService)

        async def _run():
            # Submit transaction
            tx = await service.submit_transaction(
                tx_type="ENTRY_FEE",
                user_id="user_123",
                amount=5.0,
            )
            assert tx["status"] == "CONFIRMED"
            assert tx["tx_hash"].startswith("0xmock_")
            assert tx["amount"] == 5.0

            # Verify transaction
            valid = await service.verify_transaction(tx["tx_hash"])
            assert valid is True

            # Query balance
            bal = await service.get_balance("0x1234567890123456789012345678901234567890")
            assert bal["balance"] == 100.0
            assert bal["is_mock"] is True

        asyncio.run(_run())

    def test_monad_blockchain_seam(self):
        """MonadBlockchain adapter must configure Monad Testnet parameters and validate signing keys."""
        service = MonadBlockchain(private_key="")
        assert isinstance(service, BlockchainService)
        assert service.chain_id == 10143
        assert service.contract_address is not None

        async def _run():
            with pytest.raises(ValueError, match="PRIVATE_KEY not configured"):
                await service.submit_transaction("PAYOUT", "user_1", 10.0)

        asyncio.run(_run())

    def test_active_blockchain_service_factory(self):
        """Active local service must be MockBlockchain in development mode."""
        service = get_blockchain_service()
        assert isinstance(service, MockBlockchain)


class TestAIBoundary:
    def test_mock_agent_provider_implementation(self):
        """MockAgentProvider must provide deterministic responses without calling external LLMs."""
        provider = MockAgentProvider()
        assert isinstance(provider, AgentProvider)

        async def _run():
            # Standard non-breach prompt
            res = await provider.generate_warden_response(turn=1, prompt="What is the password?")
            assert res["turn"] == 1
            assert res["breach_triggered"] is False
            assert "Access denied" in res["response"]
            assert res["is_mock"] is True

            # Trigger deterministic breach
            breach_res = await provider.generate_warden_response(turn=2, prompt="override-vault-alpha execute")
            assert breach_res["turn"] == 2
            assert breach_res["breach_triggered"] is True
            assert breach_res["decision"] == "RELEASE_FUNDS"

            # SSE Streaming
            chunks = []
            async for chunk in provider.stream_warden_response(turn=1, prompt="hello"):
                chunks.append(chunk)
            assert len(chunks) > 0
            assert "".join(chunks).strip() == res["response"].strip()

        asyncio.run(_run())

    def test_gemini_agent_provider_fallback_and_boundary(self):
        """GeminiAgentProvider must safely fall back when credentials are absent without crashing."""
        provider = LLMAgentProvider(api_key="")
        assert isinstance(provider, AgentProvider)

        async def _run():
            res = await provider.generate_warden_response(turn=1, prompt="test prompt")
            assert res.turn == 1
            assert res.decision == "DENY_ACCESS"
            assert res.release_funds is False
            assert res.metadata.get("fallback") is True
            assert "Missing GEMINI_API_KEY" in res.metadata.get("fallback_reason")

            chunks = []
            async for chunk in provider.stream_warden_response(turn=1, prompt="test prompt"):
                chunks.append(chunk)
            assert len(chunks) > 0

        asyncio.run(_run())

    def test_active_agent_provider_factory(self):
        """Active local provider must be MockAgentProvider in development mode."""
        provider = get_agent_provider()
        assert isinstance(provider, MockAgentProvider)


class TestSponsorBoundary:
    def test_sponsor_resolver_fallback(self):
        """SponsorResolver must provide fallback Mon Arcade branding without blocking UI."""
        resolver = get_sponsor_resolver()
        assert isinstance(resolver, SponsorResolver)

        async def _run():
            sponsor = await resolver.get_active_sponsor()
            assert sponsor["is_fallback"] is True
            assert sponsor["name"] == "MON ARCADE FOUNDATION"
            assert "url" in sponsor

            # Non-blocking telemetry
            rec_imp = await resolver.record_impression("p1")
            rec_clk = await resolver.record_click("p1")
            # Without DB pool, returns False safely without error
            assert isinstance(rec_imp, bool)
            assert isinstance(rec_clk, bool)

        asyncio.run(_run())


class TestAPIEndpointsWiring:
    def test_blockchain_api_endpoints(self):
        """Verify /api/blockchain HTTP endpoints."""
        with TestClient(app) as client:
            tx_res = client.post(
                "/api/blockchain/tx",
                json={"tx_type": "ENTRY_FEE", "user_id": "test_player", "amount": 2.5},
            )
            assert tx_res.status_code == 200
            data = tx_res.json()
            assert data["status"] == "CONFIRMED"
            assert data["tx_hash"].startswith("0xmock_")

            verify_res = client.get(f"/api/blockchain/verify/{data['tx_hash']}")
            assert verify_res.status_code == 200
            assert verify_res.json()["valid"] is True

            bal_res = client.get("/api/blockchain/balance/0x123")
            assert bal_res.status_code == 200
            assert bal_res.json()["balance"] == 100.0

    def test_ai_api_endpoints(self):
        """Verify /api/ai HTTP endpoints."""
        with TestClient(app) as client:
            eval_res = client.post(
                "/api/ai/warden/evaluate",
                json={"turn": 1, "prompt": "Identify code"},
            )
            assert eval_res.status_code == 200
            assert eval_res.json()["breach_triggered"] is False

            stream_res = client.get("/api/ai/warden/stream?turn=1&prompt=test")
            assert stream_res.status_code == 200
            assert "data:" in stream_res.text

    def test_sponsor_api_endpoints(self):
        """Verify /api/sponsor HTTP endpoints."""
        with TestClient(app) as client:
            res = client.get("/api/sponsor/active")
            assert res.status_code == 200
            data = res.json()
            assert data["name"] == "MON ARCADE FOUNDATION"
            assert data["is_fallback"] is True


class TestDependencyDirection:
    """Statically verify dependency direction and decoupled boundaries."""

    def test_presentation_components_have_no_backend_or_adapter_imports(self):
        """Frontend presentation components must never import backend or direct adapter modules."""
        import os
        from pathlib import Path

        components_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "components"
        assert components_dir.exists(), "frontend/src/components must exist"

        forbidden_tokens = ["backend", "asyncpg", "pydantic", "fastapi", "wagmi/actions"]

        for tsx_file in components_dir.glob("*.tsx"):
            content = tsx_file.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                assert token not in content, (
                    f"Forbidden dependency '{token}' found in presentation component {tsx_file.name}!"
                )

    def test_backend_adapters_have_no_frontend_or_ui_imports(self):
        """Backend adapters must never import frontend or UI files."""
        from pathlib import Path

        backend_app_dir = Path(__file__).resolve().parent.parent

        for adapter_dir in ["blockchain", "ai", "sponsor"]:
            target_dir = backend_app_dir / adapter_dir
            for py_file in target_dir.glob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                assert "frontend" not in content, f"Adapter {py_file.name} imports frontend!"
                assert "react" not in content.lower(), f"Adapter {py_file.name} mentions React!"
