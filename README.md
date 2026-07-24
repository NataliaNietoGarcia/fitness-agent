# Fitness Agent 🏋️

A conversational AI agent that helps strength athletes track workouts, nutrition,
and progression — and get evidence-based coaching, all in one place.

## Demo Video

[![Watch the demo](https://img.shields.io/badge/▶-Watch%20Demo%20Video-EA5B0C?style=for-the-badge)](https://drive.google.com/file/d/1TY-pqsu1-zaTsclJ_xBaPOHxSCkb2blR/view?usp=sharing)

A 2-3 minute walkthrough of the agent in action — profile creation, workout and
food logging, progression tracking, and science-based coaching feedback.

## Problem
Tracking workouts and nutrition usually means juggling several apps and entering
data manually during training. This agent lets you log everything in natural
language, stores your progression, calculates your nutrition targets, and gives
science-based coaching feedback — through one simple chat interface, on desktop
or smartphone.

## Features

### Training
- Natural language workout logging (e.g. "Yesterday bench press 80kg 3x8")
- Workout history retrieval
- Personal Records (PR) per exercise
- Automatic plateau detection
- Training volume (per exercise or overall, weekly)
- 1RM calculation (Epley formula)
- Plausibility checks on logged values (e.g. flags an implausible 12kg leg press)
- Science-based training coaching feedback, automatic after logging and on demand

### Nutrition
- Natural language food logging, matched against the official German food
  database (BLS 4.0, ~7,140 items)
- Automatic portion size estimation when no amount is given
- Smart food matching — picks the most likely match automatically, only asks
  when genuinely ambiguous
- LLM-suggested alternative search terms when a food isn't found directly
  (e.g. "Hafermilch" → "Haferdrink")
- Correct previously logged food via chat (e.g. "I meant it grilled, not raw")
- Daily and weekly nutrition overview, with a custom date range in the app
- Calorie/macro targets (TDEE-based, personalized by goal) and remaining
  calories/macros for the day
- Science-based nutrition coaching feedback, automatic after logging and on demand

### Profile & Progress
- Profile creation via form (in the app) or natural language (in chat)
- Weight tracking with history
- Goal history — every change is recorded, not overwritten
- Progress charts: weight, exercise progression, training volume

### Knowledge
- Answers training and nutrition questions from a curated scientific knowledge
  base (RAG via ChromaDB) — not just the model's general knowledge

### Design principle
Facts come from the database, scientific thresholds come from the RAG knowledge
base, and the LLM combines both to write the actual feedback — no hardcoded
nutrition/training thresholds in the code.

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

### Run with Docker (recommended for deployment)

Requires Docker and Docker Compose. Make sure your `.env` file exists first
(see Configuration above).

```bash
docker compose up --build
```

The app will be available at `http://localhost:8501`. The SQLite database and
ChromaDB vector store are persisted in `./database` and `./data/chroma_db` via
volume mounts, so your data survives container restarts.

To stop it:
```bash
docker compose down
```

### Optional: demo data
`demo_setup.py` fills the app with 4 weeks of sample workouts, weight, and
nutrition history for a demo profile — useful for trying out charts and
coaching feedback without logging weeks of real data first. See the comments
at the bottom of the file for usage.

## Usage
```
You: Yesterday I did bench press 80kg 3x8, squats 100kg 4x6
Agent: 💪 Workout saved for 2026-06-05! 2 exercise(s) logged.

You: I ate 200g chicken breast and 150g rice
Agent: 🍽️ Saved: ... 525 kcal | P:66g C:42g F:8g

You: How many calories do I have left?
Agent: 🎯 Target: 3136 kcal | Eaten: 614 | Remaining: 2522

You: How's my nutrition looking today?
Agent: 🍎 Your protein intake is a bit behind target for this time of day...
       (based on ISSN guidelines)

You: How does progressive overload work?
Agent: 📚 Based on scientific sources: ...
```

## Project Structure
```
fitness-agent/
├── agent.py               # Main agent logic
├── app.py                 # Streamlit web interface
├── demo_setup.py           # Generates sample data for demos/videos
├── AGENTS.md               # Agent identity and capabilities
├── CHANGELOG.md             # Full development history by sprint
├── requirements.txt        # Python dependencies
├── Dockerfile               # Container image definition
├── docker-compose.yml        # Container orchestration & volumes
├── .streamlit/
│   └── config.toml         # App theme
├── static/
│   └── logo.png             # App logo
├── database/
│   └── db.py                # SQLite setup & data functions
├── memory/
│   └── chroma.py             # ChromaDB / RAG setup
├── tools/
│   ├── calculations.py       # TDEE, macros, 1RM, volume, PR, plateau
│   ├── nutritrion.py          # Food lookup (BLS database)
│   ├── import_bls.py          # Imports the BLS food database
│   └── charts.py               # Data preparation for visualizations
└── data/
    └── docs/                   # Curated scientific knowledge base for RAG
```

See [CHANGELOG.md](./CHANGELOG.md) for the full development history, sprint by sprint.

## Data Sources
- **Nutrition data:** Bundeslebensmittelschlüssel (BLS) 4.0, © Max Rubner-Institut, licensed under CC BY 4.0
- **Training knowledge (RAG):** curated from peer-reviewed sources (Schoenfeld et al., ISSN Position Stands, Plotkin et al., Helms et al., WHO guidelines)

## Academic Context
Developed as part of an Agentic AI seminar project.
LLM hosted by GWDG (Gesellschaft für wissenschaftliche Datenverarbeitung Göttingen).
