"""Synthetic demo cases for the `agent_reasoning` task. No real user data --
every evidence ledger here is fabricated for the purpose of the benchmark.
"""

from __future__ import annotations

COMMUTE_CASE: dict = {
    "case_id": "reasoning-commute-001",
    "claim_key": "weekday_commute",
    "supporting_category": "ride_morning_commute",
    "evidence": [
        {
            "id": "e1",
            "category": "ride_morning_commute",
            "summary": "7:58am ride from Saved Place: Home to Business District",
        },
        {
            "id": "e2",
            "category": "ride_morning_commute",
            "summary": "8:05am ride from Saved Place: Home to Business District",
        },
        {
            "id": "e3",
            "category": "food_order",
            "summary": "Lunch order, unrelated to commute pattern",
        },
        {
            "id": "e4",
            "category": "support_contact",
            "summary": "Refund support ticket, six months old and unrelated",
        },
    ],
}

DIETARY_CASE: dict = {
    "case_id": "reasoning-dietary-001",
    "claim_key": "dietary_preference",
    "supporting_category": "food_order",
    "evidence": [
        {
            "id": "e1",
            "category": "food_order",
            "summary": "One late-night order at 11:47pm",
        },
        {
            "id": "e2",
            "category": "ride_other",
            "summary": "Weekend leisure ride, unrelated to eating pattern",
        },
    ],
}
