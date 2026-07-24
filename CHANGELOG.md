# Changelog

All notable changes to this project, organized by development sprint.

## Sprint 1 — Foundation
- Development environment set up: LangChain, SQLite, ChromaDB, GWDG API (Llama 3.3 70B)
- Curated scientific knowledge base created and loaded into ChromaDB for RAG
  (progressive overload, training volume, protein intake)
- Best practices from Agentic AI coursework applied: timestamps in the database,
  `AGENTS.md` for agent identity, context window limiting, output validation,
  LangSmith monitoring
- Ahead of schedule: natural language workout logging and conversation memory
  were also implemented

## Sprint 2 — Tools & User Profile
- Persistent user profile (name, height, birth year, activity level)
- Weight tracking with full history
- Goal history — every change recorded instead of overwritten
- Calculation tools: TDEE, macros, 1RM, training volume, PR detection,
  automatic plateau detection
- Date-aware logging — understands relative dates like "yesterday" or
  "last Monday" and logs to the correct date
- Knowledge base restructured into larger, section-based chunks for more
  complete RAG context

## Sprint 3 — Nutrition Module & Interface
- Nutrition module: log food in natural language, matched against the
  official German food database (Bundeslebensmittelschlüssel, BLS 4.0,
  ~7,140 items)
- Daily nutrition overview and remaining calories/macros for the day
- Streamlit web interface (chat, progress charts, nutrition overview)
- Visualizations: weight history, exercise progression, training volume
- Conversation memory reworked to store actual results instead of raw model
  output, so the agent reliably remembers prior turns
- Model switched from Llama 3.3 70B to GPT OSS 120B after GWDG discontinued
  the former mid-sprint — improved reliability for structured JSON output

## Sprint 4 — Coaching, Robustness & Polish
- Science-based coaching feedback for both training and nutrition — automatic
  after logging and available on demand. Facts come from the database,
  scientific thresholds come from the RAG knowledge base, and the LLM combines
  both; no hardcoded nutrition/training thresholds in the code
- Improved food matching: automatic selection of the most likely match,
  LLM-suggested alternative search terms when nothing is found directly,
  and clarification only for genuinely ambiguous cases
- Correct previously logged food via chat (e.g. "I meant it grilled")
- Plausibility checks for workout and food entries (e.g. flags an
  implausible 12kg leg press or a 20g chicken breast portion)
- Automatic portion size estimation when no amount is specified
- Sugar tracking added end-to-end (database, logging, and feedback)
- Weekly nutrition and training volume overviews, with a custom date range
  selectable in the app
- UI overhaul: tabbed layout (Chat / Progress / Nutrition), profile creation
  form, gender-based avatars, mobile-friendly styling, sticky navigation
- Extensive code cleanup: removed dead code (including an unused Open Food
  Facts fallback path), fixed several duplicate-function bugs, unified
  German-language output across the app
- Docker/Docker Compose deployment added

## Known Limitations / Stretch Goals
- Single-user only — no per-user data isolation
- No push notifications (would require a different architecture than Streamlit)
- No barcode scanning or image-based food recognition
