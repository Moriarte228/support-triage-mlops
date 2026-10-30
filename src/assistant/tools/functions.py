"""Tools the assistant can call.

Each tool validates its arguments, runs one fixed parameterised query on the
read-only database and returns plain JSON data. The model never writes SQL:
it can only choose a tool and fill in its arguments.
"""

import re

from src.assistant.tools.db import fetch_all

PLANS = ("standard", "plus", "premium")
FEE_TYPES = (
    "physical_card_delivery",
    "atm_withdrawal",
    "exchange",
    "weekend_fx_markup",
    "international_transfer",
    "top_up_by_card",
)
LIMIT_TYPES = (
    "active_physical_cards",
    "disposable_cards_per_day",
    "disposable_card_max_payment",
    "contactless_max_payment",
    "top_up_per_transaction",
    "top_up_per_day",
    "top_up_per_month",
    "atm_withdrawal_per_day",
)
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class ToolError(ValueError):
    """A problem with the arguments: the message is shown to the model."""


# ---- argument checks ----

def _text(value, field: str, max_len: int = 60) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > max_len:
        raise ToolError(f"{field} is longer than {max_len} characters")
    return value


def _choice(value, field: str, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value.strip().lower() not in allowed:
        raise ToolError(f"unknown {field} {value!r}; allowed: {', '.join(allowed)}")
    return value.strip().lower()


def _optional_plan(plan) -> str | None:
    return None if plan is None else _choice(plan, "plan", PLANS)


def _currency(value, field: str) -> str:
    code = value.strip().upper() if isinstance(value, str) else ""
    if not _CURRENCY.match(code):
        raise ToolError(f"{field} must be a 3-letter currency code such as EUR")
    return code


# ---- tools ----

def check_country(country: str) -> dict:
    name = _text(country, "country")
    rows = fetch_all(
        """
        SELECT name, can_open_account, card_delivery_days_min, card_delivery_days_max,
               cash_top_up, transfers_allowed
        FROM reference.supported_countries
        WHERE lower(name) = lower(:q) OR country_code = upper(:q) OR lower(:q) = ANY(aliases)
        """,
        q=name,
    )
    if not rows:
        return {
            "country": name,
            "listed": False,
            "note": "Not in the list of supported countries: customers living there cannot open an account "
            "and cards are not delivered there.",
        }
    row = rows[0]
    return {
        "country": row["name"],
        "listed": True,
        "can_open_account": row["can_open_account"],
        "card_delivery_days": (
            {"min": row["card_delivery_days_min"], "max": row["card_delivery_days_max"]}
            if row["card_delivery_days_min"] is not None
            else None
        ),
        "cash_top_up_at_partner_points": row["cash_top_up"],
        "transfers_allowed": row["transfers_allowed"],
    }


def list_plans() -> dict:
    rows = fetch_all("SELECT plan_id, name, monthly_price_eur FROM reference.plans ORDER BY monthly_price_eur")
    return {"plans": rows}


def get_fee(fee_type: str, plan: str | None = None) -> dict:
    fee_type = _choice(fee_type, "fee_type", FEE_TYPES)
    plan = _optional_plan(plan)
    rows = fetch_all(
        """
        SELECT plan_id AS plan, fixed_eur, percent, monthly_free_eur, note
        FROM reference.fees
        WHERE fee_type = :fee_type AND (CAST(:plan AS text) IS NULL OR plan_id = :plan)
        ORDER BY plan_id
        """,
        fee_type=fee_type,
        plan=plan,
    )
    return {"fee_type": fee_type, "fees": rows}


def get_limit(limit_type: str, plan: str | None = None) -> dict:
    limit_type = _choice(limit_type, "limit_type", LIMIT_TYPES)
    plan = _optional_plan(plan)
    rows = fetch_all(
        """
        SELECT plan_id AS plan, value, unit, note
        FROM reference.limits
        WHERE limit_type = :limit_type AND (CAST(:plan AS text) IS NULL OR plan_id = :plan)
        ORDER BY plan_id
        """,
        limit_type=limit_type,
        plan=plan,
    )
    return {"limit_type": limit_type, "limits": rows}


def list_currencies() -> dict:
    rows = fetch_all("SELECT code, name, can_hold, can_top_up FROM reference.currencies ORDER BY code")
    return {"currencies": rows}


def get_exchange_rate(base: str, quote: str) -> dict:
    base, quote = _currency(base, "base"), _currency(quote, "quote")
    rows = fetch_all(
        "SELECT quote, rate, updated_at FROM reference.exchange_rates WHERE base = 'EUR' AND quote IN (:a, :b)",
        a=base,
        b=quote,
    )
    per_eur = {"EUR": 1.0} | {row["quote"]: row["rate"] for row in rows}
    missing = [code for code in (base, quote) if code not in per_eur]
    if missing:
        raise ToolError(f"no exchange rate for {', '.join(missing)}: see list_currencies for supported currencies")
    return {
        "base": base,
        "quote": quote,
        "rate": round(per_eur[quote] / per_eur[base], 6),
        "updated_at": max((row["updated_at"] for row in rows), default=None),
        "note": "Indicative rate. The exact rate is shown in the app before the customer confirms.",
    }


def find_atms(city: str) -> dict:
    city = _text(city, "city")
    rows = fetch_all(
        """
        SELECT city, location, operator, fee_free
        FROM reference.atms
        WHERE lower(city) = lower(:city)
        ORDER BY atm_id
        """,
        city=city,
    )
    result = {"city": city, "atms": rows}
    if not rows:
        result["note"] = (
            "No ATMs listed for this city. Any ATM with the Visa logo works; its operator may charge a fee."
        )
    return result
