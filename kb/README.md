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

| Referenced in articles as | Table |
|---|---|
| fee schedule | `fees` |
| limits | `limits` |
| supported countries, delivery times | `supported_countries` |
| ATM directory | `atms` |
| current exchange rates | `exchange_rates` |
| supported currencies | `currencies` |
