# Fitness Coaching Agent 🏋️

A conversational AI agent that helps strength athletes track workouts, 
analyze progression, and get evidence-based training advice — all in one place.

## Problem
Tracking workouts across multiple apps is tedious and often gets skipped. 
This agent lets you log workouts in natural language after training, 
stores your progression, and answers training questions based on scientific documents.

## Features (Sprint 1 & 2)
- Natural language workout logging
- Workout history retrieval
- RAG-based training knowledge (scientific PDFs via ChromaDB)
- Context window management
- Monitoring via LangSmith & Langfuse

## Planned Features
- Progression analysis (PR detection, plateau, volume tracking)
- Nutrition module (TDEE, macros)
- Visualizations and coaching feedback
- Streamlit interface

## Tech Stack
| Component | Technology |
|-----------|-----------|
| Framework | LangChain |
| LLM | Llama 3.3 70B via GWDG API |
| Database | SQLite |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
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
GWDG_API_KEY=your_key_here
LANGCHAIN_API_KEY=your_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=fitness-agent

### Load documents into ChromaDB
```bash
python memory/chroma.py
```

### Run
```bash
python agent.py
```

## Usage
You: Benchpress 100kg 3x8, Squats 120kg 4x6
Agent: 💪 Workout saved! 2 exercise(s) logged.
You: What did I train recently?
Agent: 📊 Your recent workouts: ...
You: What is progressive overload?
Agent: 📚 Based on scientific documents: ...

## Project Structure

```
fitness-agent/
├── agent.py              # Main agent logic
├── AGENTS.md             # Agent identity and capabilities
├── requirements.txt      # Python dependencies
├── database/
│   └── db.py             # SQLite setup
├── memory/
│   └── chroma.py         # ChromaDB / RAG setup
├── tools/
│   └── calculations.py   # Training & nutrition tools
└── data/
    └── docs/             # Scientific PDFs for RAG
```

## Academic Context
Developed as part of an Agentic AI seminar project.
LLM hosted by GWDG (Gesellschaft für wissenschaftliche Datenverarbeitung Göttingen).
