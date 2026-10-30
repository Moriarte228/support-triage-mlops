"""Tests for the database tools.

Unit tests replace the database with a fake `fetch_all`, so they check argument
validation and query parameters without Postgres. Integration tests run only
when the database from docker-compose is reachable.
"""

import pytest

from src.assistant.tools import ToolError, run_tool, tool_config
from src.assistant.tools import functions as f


class FakeDB:
    """Stands in for fetch_all: returns prepared rows and remembers every query."""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, sql: str, **params):
        self.calls.append((sql, params))
        return self.rows


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(f, "fetch_all", db)  # functions.py now calls the fake instead of Postgres
    return db


def test_every_tool_has_a_spec():
    names = [tool["toolSpec"]["name"] for tool in tool_config()["tools"]]
    assert sorted(names) == sorted(["check_country", "list_plans", "get_fee", "get_limit",
                                    "list_currencies", "get_exchange_rate", "find_atms"])


def test_user_text_is_passed_as_a_parameter_not_pasted_into_sql(fake_db):
    attack = "Poland'; DROP TABLE reference.atms; --"
    f.check_country(attack)
    sql, params = fake_db.calls[0]
    assert attack not in sql
    assert params == {"q": attack}


def test_unknown_country_is_reported_as_not_listed(fake_db):
    assert f.check_country("Atlantis")["listed"] is False


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: f.get_fee("crypto"), "unknown fee_type"),
        (lambda: f.get_fee("exchange", plan="gold"), "unknown plan"),
        (lambda: f.get_limit("everything"), "unknown limit_type"),
        (lambda: f.get_exchange_rate("euro", "USD"), "3-letter currency code"),
        (lambda: f.check_country("   "), "non-empty"),
        (lambda: f.find_atms("x" * 100), "longer than"),
    ],
)
def test_bad_arguments_are_rejected_before_the_database(fake_db, call, message):
    with pytest.raises(ToolError, match=message):
        call()
    assert fake_db.calls == []  # nothing was sent to the database


def test_plan_is_case_insensitive(fake_db):
    f.get_fee("atm_withdrawal", plan="Standard")
    assert fake_db.calls[0][1]["plan"] == "standard"


def test_run_tool_turns_problems_into_errors(fake_db):
    assert "unknown tool" in run_tool("drop_everything", {})["error"]
    assert "unknown fee_type" in run_tool("get_fee", {"fee_type": "crypto"})["error"]
    assert "wrong arguments" in run_tool("check_country", {})["error"]


def test_run_tool_hides_database_failures(monkeypatch):
    def broken(sql, **params):
        raise ConnectionError("password authentication failed for user assistant_ro")

    monkeypatch.setattr(f, "fetch_all", broken)
    result = run_tool("check_country", {"country": "Poland"})
    assert result == {"error": "the reference database is not available right now"}  # no internals leak to the model


# ---- integration: real database ----

def _db_available() -> bool:
    try:
        from src.assistant.tools.db import fetch_all
        fetch_all("SELECT 1")
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="database is not running: docker compose up -d db")


@needs_db
def test_real_country_lookup_by_alias():
    assert f.check_country("holland")["country"] == "Netherlands"


@needs_db
def test_real_database_is_read_only():
    from sqlalchemy import text

    from src.assistant.tools.db import get_engine

    with pytest.raises(Exception, match="read-only"), get_engine().connect() as conn:
        conn.execute(text("DELETE FROM reference.atms"))


# ---- which tools a section makes available ----

def test_sections_without_table_references_get_no_tools():
    from src.assistant.tools import tools_for_texts

    assert tools_for_texts(["Go to **Profile → Close account** and confirm."]) == []


def test_table_references_select_their_tools():
    from src.assistant.tools import tools_for_texts

    text = "You can open an account if you live in one of the countries listed in *supported countries*."
    assert tools_for_texts([text]) == ["check_country"]
    assert tools_for_texts(["see *fee schedule*", "see *limits*"]) == ["get_fee", "list_plans", "get_limit"]


def test_kb_readme_documents_the_same_tools_as_the_code():
    """kb/README.md lists every table name and its tools; REFERENCE_TOOLS must say exactly the same."""
    import re
    from pathlib import Path

    from src.assistant.tools import REFERENCE_TOOLS, TOOLS

    readme = (Path(__file__).resolve().parents[1] / "kb" / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| ([^|`]+?) \| `\w+` \| (.+) \|$", readme, flags=re.M)
    documented = {name: re.findall(r"`(\w+)`", tools) for name, tools in rows}
    assert documented == REFERENCE_TOOLS
    assert all(tool in TOOLS for tools in REFERENCE_TOOLS.values() for tool in tools)


def test_every_see_reference_in_the_kb_is_a_table_or_a_section():
    """A '(see *...*)' in an article must point to a known table or to another section's heading."""
    import re
    from pathlib import Path

    from src.assistant.tools import REFERENCE_TOOLS

    kb = Path(__file__).resolve().parents[1] / "kb"
    texts = [path.read_text(encoding="utf-8") for path in kb.glob("[0-9]*.md")]
    headings = {h.lower() for text in texts for h in re.findall(r"^## (.+)$", text, flags=re.M)}
    tables = {name.lower() for name in REFERENCE_TOOLS}
    references = {r.lower() for text in texts for r in re.findall(r"see (?:the )?\*([^*]+)\*", text)}
    # a reference to a section may use the start of its heading: *Someone used my card*
    unknown = sorted(r for r in references - tables if not any(h.startswith(r) for h in headings))
    assert not unknown, f"references to nothing: {unknown}"
