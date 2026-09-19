"""
API integration tests for Mon Arcade Sponsor endpoints.
Verifies sponsor entity registration, campaign creation/funding/activation,
retrieval, active resolution fallback, and telemetry endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.sponsor import get_sponsor_repository


class TestSponsorAPIEndpoints:
    """Test /api/sponsor REST endpoints."""

    def setup_method(self):
        # Reset in-memory repository state
        repo = get_sponsor_repository()
        repo._campaigns.clear()
        repo._placements.clear()
        repo._vaults.clear()
        repo._impressions.clear()
        repo._clicks.clear()

    def test_create_sponsor_success(self):
        with TestClient(app) as client:
            res = client.post(
                "/api/sponsor",
                json={
                    "name": "Monad Ecosystem Fund",
                    "wallet": "0x1234567890123456789012345678901234567890",
                    "website": "https://monad.xyz/ecosystem",
                    "logo": "https://monad.xyz/logo.svg",
                },
            )
            assert res.status_code == 201
            data = res.json()
            assert data["name"] == "Monad Ecosystem Fund"
            assert data["wallet"] == "0x1234567890123456789012345678901234567890"
            assert data["website"] == "https://monad.xyz/ecosystem"
            assert data["id"].startswith("sp_")

    def test_create_sponsor_invalid_wallet_fails(self):
        with TestClient(app) as client:
            res = client.post(
                "/api/sponsor",
                json={
                    "name": "Bad Wallet Sponsor",
                    "wallet": "invalid_wallet",
                    "website": "https://example.com",
                },
            )
            assert res.status_code == 400
            assert "Invalid wallet address" in res.json()["detail"]

    def test_step_by_step_funding_flow(self):
        """Verify: Create Campaign -> DRAFT -> PAYMENT_PENDING -> Mock funding -> verification -> FUNDED -> ACTIVE."""
        with TestClient(app) as client:
            # 1. Create sponsor
            sp_res = client.post(
                "/api/sponsor",
                json={
                    "name": "Arcade Legends",
                    "wallet": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "website": "https://legends.monad.xyz",
                },
            )
            assert sp_res.status_code == 201
            sponsor_id = sp_res.json()["id"]

            # 2. Create campaign (starts in DRAFT)
            cmp_res = client.post(
                "/api/sponsor/campaign",
                json={
                    "sponsor_id": sponsor_id,
                    "placement": "home",
                    "budget": 50.0,
                    "auto_fund": False,
                },
            )
            assert cmp_res.status_code == 201
            cmp_data = cmp_res.json()
            campaign_id = cmp_data["id"]
            assert cmp_data["status"] == "DRAFT"

            # 3. Initiate funding (DRAFT -> PAYMENT_PENDING)
            init_res = client.post(f"/api/sponsor/campaign/{campaign_id}/initiate-funding")
            assert init_res.status_code == 200
            init_data = init_res.json()
            assert init_data["status"] == "PAYMENT_PENDING"
            assert init_data["is_mock"] is True
            assert init_data["chain"] == "monad-mock-local"
            assert "[MOCK / LOCAL]" in init_data["instructions"]

            # 4. Confirm/verify mock funding (PAYMENT_PENDING -> FUNDED)
            fund_res = client.post(
                f"/api/sponsor/campaign/{campaign_id}/confirm-funding",
                json={"auto_activate": False},
            )
            assert fund_res.status_code == 200
            fund_data = fund_res.json()
            assert fund_data["status"] == "FUNDED"
            assert fund_data["vault"]["deposit_tx"].startswith("0xmock_")
            assert fund_data["vault"]["is_mock"] is True
            assert fund_data["vault"]["chain"] == "monad-mock-local"

            # 5. Activate campaign (FUNDED -> ACTIVE)
            act_res = client.post(f"/api/sponsor/campaign/{campaign_id}/activate")
            assert act_res.status_code == 200
            assert act_res.json()["status"] == "ACTIVE"

            # 6. Verify active placement resolution now returns this sponsor
            active_res = client.get("/api/sponsor/active?placement_type=home")
            assert active_res.status_code == 200
            active_data = active_res.json()
            assert active_data["is_fallback"] is False
            assert active_data["name"] == "Arcade Legends"
            assert active_data["campaign_id"] == campaign_id

    def test_payment_failure_and_retry_recovery(self):
        """Verify: PAYMENT_PENDING -> PAYMENT_FAILED -> retry -> PAYMENT_PENDING -> FUNDED."""
        with TestClient(app) as client:
            sp_res = client.post(
                "/api/sponsor",
                json={
                    "name": "Retry Protocol",
                    "wallet": "0xcccccccccccccccccccccccccccccccccccccccc",
                    "website": "https://retry.monad.xyz",
                },
            )
            sponsor_id = sp_res.json()["id"]

            cmp_res = client.post(
                "/api/sponsor/campaign",
                json={
                    "sponsor_id": sponsor_id,
                    "placement": "vault",
                    "budget": 20.0,
                },
            )
            campaign_id = cmp_res.json()["id"]

            # Initiate
            client.post(f"/api/sponsor/campaign/{campaign_id}/initiate-funding")

            # Simulate failure
            fail_res = client.post(
                f"/api/sponsor/campaign/{campaign_id}/fail-funding",
                json={"reason": "Simulated timeout error"},
            )
            assert fail_res.status_code == 200
            assert fail_res.json()["status"] == "PAYMENT_FAILED"

            # Verify cannot activate from PAYMENT_FAILED
            bad_act = client.post(f"/api/sponsor/campaign/{campaign_id}/activate")
            assert bad_act.status_code == 400

            # Recover by re-initiating
            retry_res = client.post(f"/api/sponsor/campaign/{campaign_id}/initiate-funding")
            assert retry_res.status_code == 200
            assert retry_res.json()["status"] == "PAYMENT_PENDING"

            # Confirm funding with auto-activation
            confirm_res = client.post(
                f"/api/sponsor/campaign/{campaign_id}/confirm-funding",
                json={"auto_activate": True},
            )
            assert confirm_res.status_code == 200
            assert confirm_res.json()["status"] == "ACTIVE"

    def test_confirm_funding_with_invalid_tx_hash_fails(self):
        """Submitting an invalid transaction hash must fail verification."""
        with TestClient(app) as client:
            sp_res = client.post(
                "/api/sponsor",
                json={
                    "name": "Bad Tx Sponsor",
                    "wallet": "0xdddddddddddddddddddddddddddddddddddddddd",
                    "website": "https://badtx.monad.xyz",
                },
            )
            sponsor_id = sp_res.json()["id"]

            cmp_res = client.post(
                "/api/sponsor/campaign",
                json={
                    "sponsor_id": sponsor_id,
                    "placement": "bluff",
                    "budget": 30.0,
                },
            )
            campaign_id = cmp_res.json()["id"]
            client.post(f"/api/sponsor/campaign/{campaign_id}/initiate-funding")

            # Non-0x hash fails verification in MockBlockchain
            bad_fund = client.post(
                f"/api/sponsor/campaign/{campaign_id}/confirm-funding",
                json={"tx_hash": "not_a_valid_0x_hash"},
            )
            assert bad_fund.status_code == 400
            assert "Transaction verification failed" in bad_fund.json()["detail"]

    def test_campaign_list_and_details_endpoints(self):
        with TestClient(app) as client:
            list_res = client.get("/api/sponsor/campaigns")
            assert list_res.status_code == 200
            assert isinstance(list_res.json(), list)

    def test_telemetry_endpoints(self):
        with TestClient(app) as client:
            imp_res = client.post("/api/sponsor/impression/pl_test_123")
            assert imp_res.status_code == 200
            assert imp_res.json()["status"] == "ok"
            assert imp_res.json()["recorded"] is True

            clk_res = client.post("/api/sponsor/click/pl_test_123")
            assert clk_res.status_code == 200
            assert clk_res.json()["status"] == "ok"
            assert clk_res.json()["recorded"] is True
