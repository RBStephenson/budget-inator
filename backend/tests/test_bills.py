from fastapi.testclient import TestClient

MONTHLY_BILL = {
    "name": "Rent",
    "amount": "1200.00",
    "recurrence": "monthly",
    "due_day": 1,
    "grace_period_days": 5,
    "category": "housing",
}

ANCHOR_BILL = {
    "name": "Electric",
    "amount": "150.00",
    "recurrence": "biweekly",
    "due_date": "2024-01-10",
    "category": "utilities",
}


class TestListBills:
    def test_returns_empty_list_when_none_exist(self, client: TestClient) -> None:
        r = client.get("/bills")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_all_bills_including_inactive(self, client: TestClient) -> None:
        client.post("/bills", json=MONTHLY_BILL)
        created = client.post("/bills", json=ANCHOR_BILL).json()
        client.delete(f"/bills/{created['id']}")  # soft-delete

        r = client.get("/bills")
        assert r.status_code == 200
        bills = r.json()
        assert len(bills) == 2
        statuses = {b["name"]: b["is_active"] for b in bills}
        assert statuses["Rent"] is True
        assert statuses["Electric"] is False


class TestCreateBill:
    def test_creates_monthly_bill(self, client: TestClient) -> None:
        r = client.post("/bills", json=MONTHLY_BILL)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Rent"
        assert data["amount"] == "1200.00"
        assert data["recurrence"] == "monthly"
        assert data["due_day"] == 1
        assert data["due_date"] is None
        assert data["grace_period_days"] == 5
        assert data["category"] == "housing"
        assert data["is_variable"] is False
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_creates_anchor_date_bill(self, client: TestClient) -> None:
        r = client.post("/bills", json=ANCHOR_BILL)
        assert r.status_code == 201
        data = r.json()
        assert data["due_date"] == "2024-01-10"
        assert data["due_day"] is None

    def test_creates_bill_with_optional_fields(self, client: TestClient) -> None:
        payload = {**MONTHLY_BILL, "is_variable": True, "notes": "May vary by season"}
        r = client.post("/bills", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["is_variable"] is True
        assert data["notes"] == "May vary by season"

    def test_grace_period_defaults_to_zero(self, client: TestClient) -> None:
        payload = {k: v for k, v in MONTHLY_BILL.items() if k != "grace_period_days"}
        r = client.post("/bills", json=payload)
        assert r.status_code == 201
        assert r.json()["grace_period_days"] == 0

    def test_rejects_zero_amount(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "amount": "0"})
        assert r.status_code == 422

    def test_rejects_negative_amount(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "amount": "-10"})
        assert r.status_code == 422

    def test_rejects_due_day_above_28(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "due_day": 29})
        assert r.status_code == 422

    def test_rejects_due_day_zero(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "due_day": 0})
        assert r.status_code == 422

    def test_rejects_monthly_without_due_day(self, client: TestClient) -> None:
        payload = {k: v for k, v in MONTHLY_BILL.items() if k != "due_day"}
        r = client.post("/bills", json=payload)
        assert r.status_code == 422

    def test_rejects_monthly_with_due_date(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "due_date": "2024-01-01"})
        assert r.status_code == 422

    def test_rejects_non_monthly_without_due_date(self, client: TestClient) -> None:
        payload = {k: v for k, v in ANCHOR_BILL.items() if k != "due_date"}
        r = client.post("/bills", json=payload)
        assert r.status_code == 422

    def test_rejects_non_monthly_with_due_day(self, client: TestClient) -> None:
        r = client.post("/bills", json={**ANCHOR_BILL, "due_day": 5})
        assert r.status_code == 422

    def test_rejects_invalid_recurrence(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "recurrence": "daily"})
        assert r.status_code == 422

    def test_rejects_invalid_category(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "category": "food"})
        assert r.status_code == 422

    def test_accepts_all_valid_recurrences(self, client: TestClient) -> None:
        monthly_recurrences = ("monthly",)
        anchor_recurrences = (
            "weekly",
            "biweekly",
            "quarterly",
            "semiannual",
            "annual",
            "one_time",
        )

        for rec in monthly_recurrences:
            payload = {**MONTHLY_BILL, "recurrence": rec}
            r = client.post("/bills", json=payload)
            assert r.status_code == 201, f"recurrence={rec} should be accepted"

        for rec in anchor_recurrences:
            payload = {**ANCHOR_BILL, "recurrence": rec}
            r = client.post("/bills", json=payload)
            assert r.status_code == 201, f"recurrence={rec} should be accepted"

    def test_accepts_all_valid_categories(self, client: TestClient) -> None:
        categories = (
            "housing",
            "utilities",
            "subscriptions",
            "insurance",
            "debt",
            "savings",
            "other",
        )
        for cat in categories:
            payload = {**MONTHLY_BILL, "category": cat}
            r = client.post("/bills", json=payload)
            assert r.status_code == 201, f"category={cat} should be accepted"


class TestGetBill:
    def test_returns_bill_by_id(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.get(f"/bills/{created['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]
        assert r.json()["name"] == "Rent"

    def test_returns_404_for_missing_bill(self, client: TestClient) -> None:
        r = client.get("/bills/999")
        assert r.status_code == 404


class TestPatchBill:
    def test_updates_name(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"name": "Apartment Rent"})
        assert r.status_code == 200
        assert r.json()["name"] == "Apartment Rent"
        assert r.json()["amount"] == "1200.00"  # unchanged

    def test_updates_amount(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"amount": "1300.00"})
        assert r.status_code == 200
        assert r.json()["amount"] == "1300.00"

    def test_updates_grace_period(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"grace_period_days": 3})
        assert r.status_code == 200
        assert r.json()["grace_period_days"] == 3

    def test_reactivates_inactive_bill(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        client.delete(f"/bills/{created['id']}")
        r = client.patch(f"/bills/{created['id']}", json={"is_active": True})
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_empty_patch_is_no_op(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={})
        assert r.status_code == 200
        assert r.json()["amount"] == "1200.00"

    def test_rejects_invalid_amount(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"amount": "0"})
        assert r.status_code == 422

    def test_rejects_invalid_due_day(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"due_day": 31})
        assert r.status_code == 422

    def test_returns_404_for_missing_bill(self, client: TestClient) -> None:
        r = client.patch("/bills/999", json={"name": "Ghost"})
        assert r.status_code == 404


class TestDeleteBill:
    def test_soft_deletes_bill(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.delete(f"/bills/{created['id']}")
        assert r.status_code == 204

        # Bill still exists but is inactive
        bill = client.get(f"/bills/{created['id']}").json()
        assert bill["is_active"] is False

    def test_bill_still_in_list_after_delete(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        client.delete(f"/bills/{created['id']}")
        bills = client.get("/bills").json()
        assert any(b["id"] == created["id"] for b in bills)

    def test_returns_404_for_missing_bill(self, client: TestClient) -> None:
        r = client.delete("/bills/999")
        assert r.status_code == 404
