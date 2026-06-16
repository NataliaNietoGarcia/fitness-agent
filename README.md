# Fitness Agent 🏋️

A conversational AI agent that helps strength athletes track workouts, nutrition,
and progression — and get evidence-based training advice, all in one place.

## Problem
Tracking workouts and nutrition usually means juggling several apps and entering
data manually during training. This agent lets you log everything in natural
language, stores your progression, calculates your nutrition targets, and answers
training questions based on scientific sources — through one simple chat interface.

## Features
- **Natural language workout logging** — "Yesterday I did bench press 80kg 3x8"
- **Persistent user profile** — remembers who you are across sessions
- **Weight tracking** with history and progress overview
- **Goal history** — every goal change is recorded, not overwritten
- **Nutrition module** — log food, get calories & macros (based on the official German BLS food database)
- **Daily nutrition overview** — calories and macros eaten vs. remaining
- **Calculation tools** — TDEE, macros, 1RM, training volume, PR detection, automatic plateau detection
- **RAG knowledge base** — answers training/nutrition questions from a curated scientific knowledge base (ChromaDB)
- **Date awareness** — understands "yesterday", "last Monday" and logs to the correct date
- **Conversation memory** — remembers the context of the current conversation
- **Visualizations** — charts for weight, exercise progression and training volume
- **Streamlit web interface** — usable on desktop and smartphone

## Tech Stack
| Component | Technology |
|-----------|-----------|
| Framework | LangChain |
| LLM | GPT OSS 120B via GWDG API |
| Database | SQLite |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Nutrition Data | Bundeslebensmittelschlüssel (BLS) 4.0 |
| Interface | Streamlit |
| Data / Charts | pandas |
| Monitoring | LangSmith + Langfuse |

## Setup

### Requirements
- Python 3.11+
- GWDG API Key (university access)
- LangSmith API Key

### Installation
```bash
git clone https://github.com/NataliaNietoGarcia/fitness-agent.git
cd fitness-agent
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Create a `.env` file:
```
GWDG_API_KEY=your_key_here
LANGCHAIN_API_KEY=your_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=fitness-agent
```

### Load the knowledge base into ChromaDB
```bash
python memory/chroma.py
```

### Import the BLS nutrition database
```bash
python tools/import_bls.py
```

### Run

**Terminal version:**
```bash
python agent.py
```

**Web interface (recommended):**
```bash
streamlit run app.py
```

## Usage
```
You: Yesterday I did bench press 80kg 3x8, squats 100kg 4x6
Agent: 💪 Workout saved for 2026-06-05! 2 exercise(s) logged.

You: I ate 200g chicken breast and 150g rice
Agent: 🍽️ Saved: ... 525 kcal | P:66g C:42g F:8g

You: How many calories do I have left?
Agent: 🎯 Target: 3136 kcal | Eaten: 614 | Remaining: 2522

You: How does progressive overload work?
Agent: 📚 Based on scientific sources: ...
```

## Project Structure
```
fitness-agent/
├── agent.py              # Main agent logic
├── app.py                # Streamlit web interface
├── AGENTS.md             # Agent identity and capabilities
├── requirements.txt      # Python dependencies
├── database/
│   └── db.py             # SQLite setup & data functions
├── memory/
│   └── chroma.py         # ChromaDB / RAG setup
├── tools/
│   ├── calculations.py   # TDEE, macros, 1RM, volume, PR, plateau
│   ├── nutrition.py      # Food lookup (BLS + Open Food Facts fallback)
│   ├── import_bls.py     # Imports the BLS food database
│   └── charts.py         # Data preparation for visualizations
└── data/
    └── docs/             # Curated scientific knowledge base for RAG
```

## Data Sources
- **Nutrition data:** Bundeslebensmittelschlüssel (BLS) 4.0, © Max Rubner-Institut, licensed under CC BY 4.0
- **Branded products (fallback):** Open Food Facts
- **Training knowledge (RAG):** curated from peer-reviewed sources (Schoenfeld et al., ISSN Position Stands, Plotkin et al.)

## Academic Context
Developed as part of an Agentic AI seminar project.
LLM hosted by GWDG (Gesellschaft für wissenschaftliche Datenverarbeitung Göttingen).