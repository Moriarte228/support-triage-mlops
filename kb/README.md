# Acme Bank knowledge base (fictional)

Help-centre articles for a **fictional** bank, used as the retrieval corpus of the support assistant.
Acme Bank does not exist; the policies are invented for this project and were drafted with an LLM,
then reviewed by the author. They are not based on any real bank's terms.

## Structure

- One Markdown file per topic, with YAML front matter (`id`, `title`).
- Every `##` section starts with an HTML comment listing the BANKING77 intents it answers:

  ```
  <!-- intents: card_arrival, card_delivery_estimate -->
  ```

  The router uses these tags to fetch the exact section for a predicted intent;
  similarity search over the same sections is the fallback. All 77 intents are covered.

## Facts that change live in the database, not here

Articles describe processes and rules. Amounts and lists that change over time are referenced by name
and come from PostgreSQL reference tables at answer time:

| Referenced in articles as | Table | Tools the model gets |
|---|---|---|
| fee schedule | `fees` | `get_fee`, `list_plans` |
| limits | `limits` | `get_limit`, `list_plans` |
| supported countries | `supported_countries` | `check_country` |
| supported countries, delivery times | `supported_countries` | `check_country` |
| ATM directory | `atms` | `find_atms` |
| current exchange rates | `exchange_rates` | `get_exchange_rate` |
| supported currencies | `currencies` | `list_currencies` |

Write a reference exactly as in the first column, in italics: `(see *fee schedule*)`.
When the assistant answers from a section, it can call only the tools of the tables that section refers to;
on the clarify and fallback routes it gets all tools. The same mapping is `REFERENCE_TOOLS` in
`src/assistant/tools/registry.py`, and `tests/test_tools.py` checks that the two stay identical.
