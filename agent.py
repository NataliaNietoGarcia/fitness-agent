from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from database.db import get_connection, create_tables
from dotenv import load_dotenv
import os
import json
import re
from datetime import date
from memory.chroma import suche_in_docs

# LangSmith monitoring
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "fitness-agent"

load_dotenv()

# LLM setup via GWDG API
llm = ChatOpenAI(
    model="llama-3.3-70b-instruct",
    #model="llama-3.1-8b-instruct",
    api_key=os.getenv("GWDG_API_KEY"),
    base_url="https://chat-ai.academiccloud.de/v1"
)

SYSTEM_PROMPT = """You are a personal fitness coach and assistant. Always respond in German.

If the user logs a workout, respond ONLY with:
{
    "action": "save_workout",
    "exercises": [
        {"exercise": "Name", "weight_kg": 0.0, "sets": 0, "reps": 0}
    ]
}

If the user asks what they trained recently, respond with:
{
    "action": "get_workouts"
}

If the user asks a question about training or nutrition, respond with:
{
    "action": "search_knowledge",
    "question": "the user's question"
}

For all other messages, respond normally as a coach in German.
"""

def load_agents_md():
    try:
        with open("AGENTS.md", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

AGENTS_CONTEXT = load_agents_md()

def save_workout(exercises):
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today()
    for e in exercises:
        cursor.execute("""
            INSERT INTO workouts (date, exercise, weight_kg, sets, reps)
            VALUES (?, ?, ?, ?, ?)
        """, (today, e["exercise"], e["weight_kg"], e["sets"], e["reps"]))
    conn.commit()
    conn.close()
    print(f"✅ {len(exercises)} exercise(s) saved!")

def get_recent_workouts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, exercise, weight_kg, sets, reps 
        FROM workouts 
        ORDER BY date DESC, id DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "Du hast noch keine Workouts gespeichert!"

    result = "📊 Deine letzten Workouts:\n"
    result += "-" * 40 + "\n"
    for row in rows:
        result  += f"📅 {row[0]} | 💪 {row[1]} | ⚖️ {row[2]}kg | {row[3]} {'Satz' if row[3] == 1 else 'Sätze'} x {row[4]} Wdh\n"
    return result

def parse_response(response_text: str):
    # Try direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON anywhere in text
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None

def validate_workout_data(data: dict):
    if "exercises" not in data:
        return False
    for e in data["exercises"]:
        if not all(k in e for k in ["exercise", "weight_kg", "sets", "reps"]):
            return False
    return True

# Conversation history with max limit to control context window
MAX_HISTORY = 10
conversation_history = []

def chat(user_input):
    global conversation_history

    conversation_history.append(HumanMessage(content=user_input))

    # Keep history within limit
    if len(conversation_history) > MAX_HISTORY:
        conversation_history = conversation_history[-MAX_HISTORY:]

    messages = [
        SystemMessage(content=AGENTS_CONTEXT + "\n\n" + SYSTEM_PROMPT),
        *conversation_history
    ]

    response = llm.invoke(messages)
    answer = response.content.strip()

    conversation_history.append(response)

    data = parse_response(answer)
    if data:
        action = data.get("action")

        if action == "save_workout":
            if not validate_workout_data(data):
                return "❌ Konnte Workout nicht korrekt lesen. Bitte nochmal eingeben!"
            save_workout(data["exercises"])
            return f"💪 Workout gespeichert! {len(data['exercises'])} Übung(en) eingetragen."

        elif action == "get_workouts":
            return get_recent_workouts()

        elif action == "search_knowledge":
            context = suche_in_docs(data["question"])
            messages2 = [
                SystemMessage(content="You are a fitness coach. Answer the question based on the following context. Always respond in German."),
                HumanMessage(content=f"Context:\n{context}\n\nQuestion: {data['question']}")
            ]
            answer2 = llm.invoke(messages2)
            return f"📚 {answer2.content}"

        else:
            return answer
    else:
        return answer

if __name__ == "__main__":
    create_tables()
    print("🏋️ Fitness Agent bereit! (Schreibe 'exit' zum Beenden)")
    print("-" * 50)

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        answer = chat(user_input)
        print(f"Agent: {answer}\n")