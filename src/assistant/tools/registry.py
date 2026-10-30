"""Tool descriptions for the model and a safe way to run a tool by name.

The model decides which tool to call from these descriptions, so they say
what each tool is for, not how it works.
"""

import logging

from src.assistant.tools import functions as f

logger = logging.getLogger(__name__)


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return {"json": schema}


_PLAN = {"type": "string", "enum": list(f.PLANS), "description": "Customer's plan. Omit to get all plans."}

TOOLS = {
    "check_country": (
        f.check_country,
        (
            "Whether customers living in a country can open an account, card delivery time there, "
            "cash top-ups at partner points and whether transfers are allowed. Use for questions about "
            "supported countries or card delivery to a specific country."
        ),
        _schema({"country": {"type": "string", "description": "Country name in English, e.g. Poland"}}, ["country"]),
    ),
    "list_plans": (
        f.list_plans,
        "The available plans and their monthly prices.",
        _schema({}),
    ),
    "get_fee": (
        f.get_fee,
        (
            "Our fee for an action, per plan: card delivery, ATM withdrawals, currency exchange, weekend exchange "
            "markup, international transfers, top-ups by card. Includes the free monthly allowance if there is one."
        ),
        _schema({"fee_type": {"type": "string", "enum": list(f.FEE_TYPES)}, "plan": _PLAN}, ["fee_type"]),
    ),
    "get_limit": (
        f.get_limit,
        "A limit per plan: number of cards, disposable cards, contactless payments, top-ups, ATM withdrawals per day.",
        _schema({"limit_type": {"type": "string", "enum": list(f.LIMIT_TYPES)}, "plan": _PLAN}, ["limit_type"]),
    ),
    "list_currencies": (
        f.list_currencies,
        "Currencies customers can hold and top up in.",
        _schema({}),
    ),
    "get_exchange_rate": (
        f.get_exchange_rate,
        "Current indicative exchange rate between two currencies.",
        _schema(
            {
                "base": {"type": "string", "description": "3-letter code of the currency to convert from, e.g. EUR"},
                "quote": {"type": "string", "description": "3-letter code of the currency to convert to, e.g. PLN"},
            },
            ["base", "quote"],
        ),
    ),
    "find_atms": (
        f.find_atms,
        "ATMs in a city and whether their operator charges its own fee.",
        _schema({"city": {"type": "string", "description": "City name in English, e.g. Warsaw"}}, ["city"]),
    ),
}


# Knowledge-base articles refer to reference tables by name, in italics: "(see *fee schedule*)".
# The table in kb/README.md lists these names; this is the same list, mapped to the tools that read the table.
REFERENCE_TOOLS = {
    "fee schedule": ["get_fee", "list_plans"],
    "limits": ["get_limit", "list_plans"],
    "supported countries": ["check_country"],
    "supported countries, delivery times": ["check_country"],
    "current exchange rates": ["get_exchange_rate"],
    "supported currencies": ["list_currencies"],
    "ATM directory": ["find_atms"],
}


def tools_for_texts(texts: list[str]) -> list[str]:
    """Tools needed by these sections: the ones whose tables the sections refer to."""
    names: list[str] = []
    for text in texts:
        for reference, tools in REFERENCE_TOOLS.items():
            if f"*{reference}*" in text:
                names += [name for name in tools if name not in names]
    return names


def tool_config(names: list[str] | None = None) -> dict | None:
    """The toolConfig block for the Bedrock Converse API: all tools, or only `names` (None if empty)."""
    selected = list(TOOLS) if names is None else names
    if not selected:
        return None
    return {
        "tools": [
            {"toolSpec": {"name": name, "description": TOOLS[name][1], "inputSchema": TOOLS[name][2]}}
            for name in selected
        ]
    }


def run_tool(name: str, arguments: dict) -> dict:
    """Run a tool requested by the model. Never raises: problems come back as {"error": ...}."""
    if name not in TOOLS:
        return {"error": f"unknown tool {name!r}"}
    function = TOOLS[name][0]
    try:
        return function(**(arguments or {}))
    except f.ToolError as error:
        return {"error": str(error)}
    except TypeError:
        return {"error": f"wrong arguments for {name}: {sorted((arguments or {}).keys())}"}
    except Exception:
        logger.exception("tool %s failed", name)
        return {"error": "the reference database is not available right now"}
