from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "net_salary": "2500.00",
    "first_paycheck_date": "2024-01-05",
    "beginning_balance": "500.00",
    "frequency": "biweekly",
}


class TestGetPaySchedule:
    def test_returns_404_when_none_configured(self, client: TestClient) -> None:
        r = client.get("/pay-schedule")
        assert r.status_code == 404

    def test_returns_schedule_after_create(self, client: TestClient) -> None:
        assert client.post("/pay-schedule", json=VALID_PAYLOAD).status_code == 201
        r = client.get("/pay-schedule")
        assert r.status_code == 200
        data = r.json()
        assert data["net_salary"] == "2500.00"
        assert data["first_paycheck_date"] == "2024-01-05"
        assert data["beginning_balance"] == "500.00"
        assert data["frequency"] == "biweekly"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data


class TestPostPaySchedule:
    def test_creates_schedule(self, client: TestClient) -> None:
        r = client.post("/pay-schedule", json=VALID_PAYLOAD)
        assert r.status_code == 201
        data = r.json()
        assert data["net_salary"] == "2500.00"
        assert data["frequency"] == "biweekly"

    def test_replaces_existing_schedule(self, client: TestClient) -> None:
        client.post("/pay-schedule", json=VALID_PAYLOAD)
        replacement = {**VALID_PAYLOAD, "net_salary": "3000.00", "frequency": "weekly"}
        r = client.post("/pay-schedule", json=replacement)
        assert r.status_code == 201
        assert r.json()["net_salary"] == "3000.00"
        assert r.json()["frequency"] == "weekly"
        # Only one row should exist
        assert client.get("/pay-schedule").json()["net_salary"] == "3000.00"

    def test_rejects_zero_salary(self, client: TestClient) -> None:
        r = client.post("/pay-schedule", json={**VALID_PAYLOAD, "net_salary": "0"})
        assert r.status_code == 422

    def test_rejects_negative_salary(self, client: TestClient) -> None:
        r = client.post("/pay-schedule", json={**VALID_PAYLOAD, "net_salary": "-1"})
        assert r.status_code == 422

    def test_rejects_negative_beginning_balance(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "beginning_balance": "-0.01"}
        r = client.post("/pay-schedule", json=payload)
        assert r.status_code == 422

    def test_rejects_invalid_frequency(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "frequency": "fortnight"}
        r = client.post("/pay-schedule", json=payload)
        assert r.status_code == 422

    def test_accepts_zero_beginning_balance(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "beginning_balance": "0.00"}
        r = client.post("/pay-schedule", json=payload)
        assert r.status_code == 201

    def test_accepts_all_valid_frequencies(self, client: TestClient) -> None:
        for freq in ("weekly", "biweekly", "semimonthly", "monthly"):
            anchor = (
                "2024-01-01"
                if freq == "semimonthly"
                else VALID_PAYLOAD["first_paycheck_date"]
            )
            payload = {
                **VALID_PAYLOAD,
                "frequency": freq,
                "first_paycheck_date": anchor,
            }
            r = client.post("/pay-schedule", json=payload)
            assert r.status_code == 201, f"frequency={freq} should be accepted"
            assert r.json()["frequency"] == freq

    def test_rejects_semimonthly_anchor_not_on_recognized_day(
        self, client: TestClient
    ) -> None:
        # BI-18 repro: an anchor day outside {1, 15, month-end} silently
        # collapsed a pay period boundary instead of being rejected.
        payload = {
            **VALID_PAYLOAD,
            "frequency": "semimonthly",
            "first_paycheck_date": "2025-01-16",
        }
        r = client.post("/pay-schedule", json=payload)
        assert r.status_code == 422
        assert "first_paycheck_date" in r.json()["detail"]

    def test_accepts_semimonthly_month_end_anchor(self, client: TestClient) -> None:
        payload = {
            **VALID_PAYLOAD,
            "frequency": "semimonthly",
            "first_paycheck_date": "2024-02-29",
        }
        r = client.post("/pay-schedule", json=payload)
        assert r.status_code == 201


class TestPatchPaySchedule:
    def test_returns_404_when_none_configured(self, client: TestClient) -> None:
        r = client.patch("/pay-schedule", json={"net_salary": "3000.00"})
        assert r.status_code == 404

    def test_updates_single_field(self, client: TestClient) -> None:
        client.post("/pay-schedule", json=VALID_PAYLOAD)
        r = client.patch("/pay-schedule", json={"net_salary": "2750.00"})
        assert r.status_code == 200
        data = r.json()
        assert data["net_salary"] == "2750.00"
        assert data["frequency"] == "biweekly"  # unchanged

    def test_updates_multiple_fields(self, client: TestClient) -> None:
        client.post("/pay-schedule", json=VALID_PAYLOAD)
        patch = {"frequency": "monthly", "beginning_balance": "1000.00"}
        r = client.patch("/pay-schedule", json=patch)
        assert r.status_code == 200
        data = r.json()
        assert data["frequency"] == "monthly"
        assert data["beginning_balance"] == "1000.00"
        assert data["net_salary"] == "2500.00"  # unchanged

    def test_rejects_invalid_patch_salary(self, client: TestClient) -> None:
        client.post("/pay-schedule", json=VALID_PAYLOAD)
        r = client.patch("/pay-schedule", json={"net_salary": "0"})
        assert r.status_code == 422

    def test_empty_patch_is_no_op(self, client: TestClient) -> None:
        client.post("/pay-schedule", json=VALID_PAYLOAD)
        r = client.patch("/pay-schedule", json={})
        assert r.status_code == 200
        assert r.json()["net_salary"] == "2500.00"

    def test_rejects_switching_frequency_to_semimonthly_with_bad_anchor(
        self, client: TestClient
    ) -> None:
        # VALID_PAYLOAD's anchor (day 5) is fine for biweekly but not
        # semimonthly.
        client.post("/pay-schedule", json=VALID_PAYLOAD)
        r = client.patch("/pay-schedule", json={"frequency": "semimonthly"})
        assert r.status_code == 422
        assert client.get("/pay-schedule").json()["frequency"] == "biweekly"

    def test_rejects_patching_anchor_off_recognized_day_while_semimonthly(
        self, client: TestClient
    ) -> None:
        client.post(
            "/pay-schedule",
            json={
                **VALID_PAYLOAD,
                "frequency": "semimonthly",
                "first_paycheck_date": "2024-01-01",
            },
        )
        r = client.patch("/pay-schedule", json={"first_paycheck_date": "2024-01-10"})
        assert r.status_code == 422
        assert client.get("/pay-schedule").json()["first_paycheck_date"] == "2024-01-01"
