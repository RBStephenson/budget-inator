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

    def test_filters_by_category(self, client: TestClient) -> None:
        client.post("/bills", json=MONTHLY_BILL)  # housing
        client.post("/bills", json=ANCHOR_BILL)  # utilities

        r = client.get("/bills?category=housing")
        assert r.status_code == 200
        bills = r.json()
        assert len(bills) == 1
        assert bills[0]["name"] == "Rent"

    def test_category_filter_returns_empty_for_no_match(
        self, client: TestClient
    ) -> None:
        client.post("/bills", json=MONTHLY_BILL)  # housing

        r = client.get("/bills?category=debt")
        assert r.status_code == 200
        assert r.json() == []

    def test_rejects_invalid_category_filter(self, client: TestClient) -> None:
        r = client.get("/bills?category=food")
        assert r.status_code == 422


class TestCreateBill:
    def test_creates_monthly_bill(self, client: TestClient) -> None:
        r = client.post("/bills", json=MONTHLY_BILL)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Rent"
        assert data["amount"] == "1200.00"
        assert data["recurrence"] == "monthly"
        assert data["due_day"] == 1
        assert data["due_day_is_month_end"] is False
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

    def test_accepts_due_days_through_31(self, client: TestClient) -> None:
        for due_day in (29, 30, 31):
            r = client.post("/bills", json={**MONTHLY_BILL, "due_day": due_day})
            assert r.status_code == 201
            assert r.json()["due_day"] == due_day

    def test_rejects_due_day_above_31(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "due_day": 32})
        assert r.status_code == 422

    def test_rejects_due_day_zero(self, client: TestClient) -> None:
        r = client.post("/bills", json={**MONTHLY_BILL, "due_day": 0})
        assert r.status_code == 422

    def test_rejects_monthly_without_due_day(self, client: TestClient) -> None:
        payload = {k: v for k, v in MONTHLY_BILL.items() if k != "due_day"}
        r = client.post("/bills", json=payload)
        assert r.status_code == 422

    def test_creates_month_end_bill_without_fixed_due_day(
        self, client: TestClient
    ) -> None:
        payload = {k: v for k, v in MONTHLY_BILL.items() if k != "due_day"} | {
            "due_day_is_month_end": True
        }
        r = client.post("/bills", json=payload)
        assert r.status_code == 201
        assert r.json()["due_day"] is None
        assert r.json()["due_day_is_month_end"] is True

    def test_rejects_month_end_bill_with_fixed_due_day(
        self, client: TestClient
    ) -> None:
        r = client.post(
            "/bills",
            json={**MONTHLY_BILL, "due_day_is_month_end": True},
        )
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

    def test_updates_notes(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"notes": "Autopay on 1st"})
        assert r.status_code == 200
        assert r.json()["notes"] == "Autopay on 1st"

    def test_explicit_null_clears_notes(self, client: TestClient) -> None:
        """Regression for #80: clearing notes in the edit modal must persist."""
        payload = {**MONTHLY_BILL, "notes": "Autopay on 1st"}
        created = client.post("/bills", json=payload).json()
        r = client.patch(f"/bills/{created['id']}", json={"notes": None})
        assert r.status_code == 200
        assert r.json()["notes"] is None

    def test_omitting_notes_preserves_them(self, client: TestClient) -> None:
        payload = {**MONTHLY_BILL, "notes": "Autopay on 1st"}
        created = client.post("/bills", json=payload).json()
        r = client.patch(f"/bills/{created['id']}", json={"name": "Apartment Rent"})
        assert r.status_code == 200
        assert r.json()["notes"] == "Autopay on 1st"

    def test_empty_patch_is_no_op(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={})
        assert r.status_code == 200
        assert r.json()["amount"] == "1200.00"

    def test_rejects_invalid_amount(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"amount": "0"})
        assert r.status_code == 422

    def test_accepts_due_day_31(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"due_day": 31})
        assert r.status_code == 200
        assert r.json()["due_day"] == 31

    def test_switches_between_fixed_day_and_month_end(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()

        month_end = client.patch(
            f"/bills/{created['id']}",
            json={"due_day": None, "due_day_is_month_end": True},
        )
        assert month_end.status_code == 200
        assert month_end.json()["due_day"] is None
        assert month_end.json()["due_day_is_month_end"] is True

        fixed = client.patch(
            f"/bills/{created['id']}",
            json={"due_day": 31, "due_day_is_month_end": False},
        )
        assert fixed.status_code == 200
        assert fixed.json()["due_day"] == 31
        assert fixed.json()["due_day_is_month_end"] is False

    def test_returns_404_for_missing_bill(self, client: TestClient) -> None:
        r = client.patch("/bills/999", json={"name": "Ghost"})
        assert r.status_code == 404

    def test_switches_to_monthly_with_due_day(self, client: TestClient) -> None:
        created = client.post("/bills", json=ANCHOR_BILL).json()
        r = client.patch(
            f"/bills/{created['id']}", json={"recurrence": "monthly", "due_day": 5}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["recurrence"] == "monthly"
        assert data["due_day"] == 5
        assert data["due_date"] is None  # anchor cleared

    def test_switches_to_weekly_with_due_date(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(
            f"/bills/{created['id']}",
            json={"recurrence": "weekly", "due_date": "2024-03-01"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["recurrence"] == "weekly"
        assert data["due_date"] == "2024-03-01"
        assert data["due_day"] is None  # month-day cleared

    def test_rejects_switch_to_monthly_without_due_day(
        self, client: TestClient
    ) -> None:
        """Regression for #79: this used to persist and 500 GET /schedule."""
        created = client.post("/bills", json=ANCHOR_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"recurrence": "monthly"})
        assert r.status_code == 422

        # Bill is unchanged and still consistent
        bill = client.get(f"/bills/{created['id']}").json()
        assert bill["recurrence"] == "biweekly"
        assert bill["due_date"] == "2024-01-10"

    def test_rejects_switch_to_non_monthly_without_due_date(
        self, client: TestClient
    ) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"recurrence": "weekly"})
        assert r.status_code == 422
        bill = client.get(f"/bills/{created['id']}").json()
        assert bill["recurrence"] == "monthly"
        assert bill["due_day"] == 1

    def test_rejects_due_date_on_monthly_bill(self, client: TestClient) -> None:
        created = client.post("/bills", json=MONTHLY_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"due_date": "2024-03-01"})
        assert r.status_code == 422
        assert client.get(f"/bills/{created['id']}").json()["due_date"] is None

    def test_rejects_due_day_on_anchor_bill(self, client: TestClient) -> None:
        created = client.post("/bills", json=ANCHOR_BILL).json()
        r = client.patch(f"/bills/{created['id']}", json={"due_day": 5})
        assert r.status_code == 422
        assert client.get(f"/bills/{created['id']}").json()["due_day"] is None


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
