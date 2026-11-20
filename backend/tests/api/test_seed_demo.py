from __future__ import annotations

from datetime import date

from app.seed_demo import build_demo_plan, seed_demo

TODAY = date(2026, 11, 17)  # mardi, aligné sur la fixture « client »
PERIOD_START = "2026-11-17"


def _available_by_day(week: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for volunteer in week["volunteers"]:
        for day in volunteer["days"]:
            if day["status"] in {"all_day", "slot"}:
                counts[day["date"]] = counts.get(day["date"], 0) + 1
    return counts


def test_demo_data_fills_the_admin_planning(client, admin, settings) -> None:
    seed_demo(settings, build_demo_plan(TODAY))

    volunteers = client.get("/api/admin/volunteers").json()
    assert len(volunteers) == 21
    assert sum(1 for volunteer in volunteers if volunteer["is_active"]) == 20

    vaire = client.get(
        "/api/admin/week", params={"period_start": PERIOD_START, "site": "vaire"}
    )
    assert vaire.status_code == 200, vaire.text
    assert _available_by_day(vaire.json()) == {
        "2026-11-17": 9,
        "2026-11-18": 5,
        "2026-11-19": 8,
        "2026-11-20": 6,
        "2026-11-21": 15,
    }

    essarts = client.get(
        "/api/admin/week", params={"period_start": PERIOD_START, "site": "les-essarts"}
    )
    assert essarts.status_code == 200, essarts.text
    counts = _available_by_day(essarts.json())
    assert counts["2026-11-18"] == 8
    assert counts.get("2026-11-21", 0) == 0
