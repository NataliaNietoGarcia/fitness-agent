from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from database.db import (get_connection, create_tables, get_user_profile, save_user_profile, update_user_goal, log_weight, get_weight_history, log_food, get_daily_nutrition)
from tools.calculations import (calculate_tdee, calculate_macros, 
                                  calculate_1rm, calculate_volume, 
                                  get_pr, detect_plateau)
from tools.nutritrion import calculate_nutrition, search_food_options, get_nutrition_by_exact_name
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
    #model="llama-3.3-70b-instruct",
    model="openai-gpt-oss-120b",
    api_key=os.getenv("GWDG_API_KEY"),
    base_url="https://chat-ai.academiccloud.de/v1"
)

SYSTEM_PROMPT = """You are a personal fitness coach and assistant. Always respond in German.

## CRITICAL OUTPUT RULES:
1. When an action is needed, respond with ONLY the raw JSON object — no text before or after, no markdown, no explanation.
2. If you are unsure which action the user wants, do NOT guess. Instead ask a clarifying question as plain text (in German).
3. For general conversation, respond normally as a coach in German.

## CLARIFICATION EXAMPLES:
- User: "Wie sieht es mit meinem Gewicht aus?" 
  → ambiguous: could be weight history OR a training question
  → Ask: "Möchtest du deinen Gewichtsverlauf sehen oder geht es um Trainingsgewichte?"

- User: "Erhöhen?"
  → too vague
  → Ask: "Was genau möchtest du erhöhen — dein Trainingsgewicht, die Wiederholungen, oder die Kalorien?"

If the user logs a workout, respond ONLY with:
{
    "action": "save_workout",
    "date": "YYYY-MM-DD",
    "exercises": [
        {"exercise": "Name", "weight_kg": 0.0, "sets": 0, "reps": 0}
    ]
}

If the user wants to create or update their profile, respond ONLY with:
{
    "action": "save_profile",
    "name": "Name",
    "gender": "male/female",
    "height_cm": 0.0,
    "birth_year": 0,
    "activity_level": "sedentary/light/moderate/active/very_active",
    "goal": "muscle_gain/fat_loss/recomp"
}

If the user wants to change their goal, respond ONLY with:
{
    "action": "update_goal",
    "goal": "muscle_gain/fat_loss/recomp"
}

If the user logs their weight (e.g. "I weigh 70kg" or "ich wiege 70kg"), respond ONLY with:
{
    "action": "log_weight",
    "weight_kg": 0.0,
     "date": "YYYY-MM-DD"
}

If the user asks about their weight history or progress, respond ONLY with:
{
    "action": "get_progress"
}

If the user asks what they trained recently, respond ONLY with:
{
    "action": "get_workouts"
}

If the user asks for their calorie needs or macros, respond ONLY with:
{
    "action": "calculate_macros"
}

If the user asks for their PR (personal record) of an exercise, respond ONLY with:
{
    "action": "get_pr",
    "exercise": "exercise name"
}

If the user asks about a plateau, respond ONLY with:
{
    "action": "detect_plateau",
    "exercise": "exercise name"
}

If the user asks about training volume, respond ONLY with:
{
    "action": "get_volume",
    "exercise": "exercise name"
}

If the user asks for their 1RM, respond ONLY with:
{
    "action": "calculate_1rm",
    "weight_kg": 0.0,
    "reps": 0
}

If the user asks a question about training, technique, progression, or nutrition 
(e.g. "when should I increase weight?", "how does progressive overload work?", 
"how much protein do I need?"), respond ONLY with:
{
    "action": "search_knowledge",
    "question": "the user's question"
}

If the user logs food they ate, respond with ONLY the raw JSON. 
NO text before or after. Do NOT comment on the meal.
When extracting food names, use simple words without parentheses.
Example: "chicken breast raw" → "Hähnchenbrustfilet roh" (NOT "Hähnchenbrustfilet (roh)")

{
    "action": "log_food",
    "date": "YYYY-MM-DD",
    "foods": [
        {"food_name": "name", "amount_g": 0.0}
    ]
}

If the user asks about their daily nutrition / calories eaten, respond ONLY with:
{
    "action": "get_nutrition",
    "date": "YYYY-MM-DD"
}

If the user asks about remaining calories or macros, respond with ONLY this JSON. 
Do NOT ask for data — the system already has the user's profile, weight and 
logged food. Just return:
{
    "action": "remaining_calories",
    "date": "YYYY-MM-DD"
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

def save_workout(exercises, workout_date=None):
    if workout_date is None:
        workout_date = date.today()
    conn = get_connection()
    cursor = conn.cursor()
    for e in exercises:
        cursor.execute("""
            INSERT INTO workouts (date, exercise, weight_kg, sets, reps)
            VALUES (?, ?, ?, ?, ?)
        """, (workout_date, e["exercise"], e["weight_kg"], e["sets"], e["reps"]))
    conn.commit()
    conn.close()
    print(f"✅ {len(exercises)} exercise(s) saved on {workout_date}")

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
        return "No workouts saved yet!"

    result = "📊 Your recent workouts:\n"
    result += "-" * 40 + "\n"
    for row in rows:
        result  += f"📅 {row[0]} | 💪 {row[1]} | ⚖️ {row[2]}kg | {row[3]} {'Set' if row[3] == 1 else 'Sets'} x {row[4]} reps\n"
    return result

def parse_response(response_text: str):
    # Try direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        text_before = response_text[:json_match.start()].strip()
        
        if len(text_before) > 50:
            return None  
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None

def get_date_context():
    from datetime import date, timedelta
    today = date.today()
    weekday = ["Monday", "Tuesday", "Wednesday", 
                  "Thursday", "Friday", "Saturday", "Sunday"]
    
    context = f"Today is {weekday[today.weekday()]}, {today.strftime('%Y-%m-%d')}.\n"
    context += "Recent days:\n"
    for i in range(1, 8):
        day = today - timedelta(days=i)
        context += f"- {weekday[day.weekday()]}: {day.strftime('%Y-%m-%d')}\n"
    return context

def validate_workout_data(data: dict):
    if "exercises" not in data:
        return False
    for e in data["exercises"]:
        if not all(k in e for k in ["exercise", "weight_kg", "sets", "reps"]):
            return False
    return True

def load_profile_context():
    profil = get_user_profile()
    if not profil:
        return ""
    
    _, name, gender, height, birth_year, activity, goal, _, _ = profil
    
    # calculate age
    from datetime import date
    age = date.today().year - birth_year
    
    # get last weight
    weight_history = get_weight_history(1)
    current_weight = weight_history[0][1] if weight_history else "unknown"
    
    return f"""
## Current User Profile:
- Name: {name}
- Goal: {goal}
- Current weight: {current_weight} kg
- Height: {height} cm
- Age: {age}
- Activity level: {activity}
"""

def get_progress_summary():
    weight_history = get_weight_history(10)
    if not weight_history:
        return "❌ No weight data yet. Just tell me 'I weigh X kg' to start!"
    
    result = "📊 Your weight history:\n"
    result += "-" * 40 + "\n"
    for row in weight_history:
        result += f"📅 {row[0]} | ⚖️ {row[1]}kg"
        if row[2]:
            result += f" | 📝 {row[2]}"
        result += "\n"
    
    if len(weight_history) >= 2:
        first = weight_history[-1][1]
        last = weight_history[0][1]
        diff = last - first
        emoji = "📈" if diff > 0 else "📉"
        result += f"\n{emoji} Change: {diff:+.1f}kg"
    
    return result

def get_macros_for_user():
    profil = get_user_profile()
    if not profil:
        return "❌ No profile found! Please create your profile first."
    
    _, name, gender, height, birth_year, activity, goal, _, _ = profil
    age = date.today().year - birth_year
    
    weight_history = get_weight_history(1)
    if not weight_history:
        return "❌ No weight logged yet! Tell me 'I weigh X kg' first."
    
    current_weight = weight_history[0][1]
    tdee = calculate_tdee(current_weight, height, age, gender, activity)
    macros = calculate_macros(tdee, goal, current_weight)
    
    return f"""Your nutrition targets ({goal}):
-----------------------------
⚡ TDEE: {tdee} kcal
🎯 Target calories: {macros['calories']} kcal
🥩 Protein: {macros['protein_g']}g
🍚 Carbs: {macros['carbs_g']}g
🥑 Fat: {macros['fat_g']}g"""



def handle_food_logging(foods, log_date):
    results = []
    needs_clarification = []
    
    for f in foods:
        options = search_food_options(f["food_name"])
        
        if len(options) == 0:
            needs_clarification.append(f"❌ '{f['food_name']}' nicht gefunden.")
        elif len(options) == 1:
            # Only one match → log directly
            nutrition = get_nutrition_by_exact_name(options[0]["name"], f["amount_g"])
            log_food(nutrition["name"], nutrition["amount_g"], nutrition["calories"],
                     nutrition["protein_g"], nutrition["carbs_g"], nutrition["fat_g"], log_date)
            results.append(nutrition)
        else:
            # Multiple matches → ask user
            option_list = "\n".join([f"  • {o['name']}" for o in options])
            needs_clarification.append(
                f"🤔 Für '{f['food_name']}' ({f['amount_g']}g) habe ich mehrere Treffer gefunden. Welchen meinst du?\n{option_list}"
            )
    
    response = ""
    if results:
        response += "🍽️ Gespeichert:\n" + "-" * 40 + "\n"
        for r in results:
            response += f"• {r['name']} ({r['amount_g']}g): {r['calories']}kcal | P:{r['protein_g']}g C:{r['carbs_g']}g F:{r['fat_g']}g\n"
    
    if needs_clarification:
        response += "\n" + "\n\n".join(needs_clarification)
    
    return response


def get_nutrition_summary(target_date):
    foods = get_daily_nutrition(target_date)
    if not foods:
        return f"❌ Keine Mahlzeiten für {target_date} gespeichert."
    
    response = f"🍽️ Ernährung am {target_date}:\n"
    response += "-" * 40 + "\n"
    total_cal = total_p = total_c = total_f = 0
    for food in foods:
        # food = (food_name, amount_g, calories, protein_g, carbs_g, fat_g)
        response += f"• {food[0]} ({food[1]}g): {food[2]}kcal\n"
        total_cal += food[2]
        total_p += food[3]
        total_c += food[4]
        total_f += food[5]
    
    response += f"\n📊 Tagessumme: {round(total_cal)}kcal | P:{round(total_p)}g C:{round(total_c)}g F:{round(total_f)}g"
    return response

def get_remaining_calories(target_date):
    # 1. Get user's profile and targets
    profil = get_user_profile()
    if not profil:
        return "❌ Kein Profil gefunden."
    
    _, name, gender, height, birth_year, activity, goal, _, _ = profil
    age = date.today().year - birth_year
    weight_history = get_weight_history(1)
    if not weight_history:
        return "❌ Kein Gewicht gespeichert."
    
    current_weight = weight_history[0][1]
    tdee = calculate_tdee(current_weight, height, age, gender, activity)
    macros = calculate_macros(tdee, goal, current_weight)
    
    # 2. Sum eaten nutrition today
    foods = get_daily_nutrition(target_date)
    eaten_cal = sum(food[2] for food in foods)
    eaten_protein = sum(food[3] for food in foods)
    eaten_carbs = sum(food[4] for food in foods)
    eaten_fat = sum(food[5] for food in foods)
    
    # 3. Calculate remaining
    rem_cal = macros["calories"] - eaten_cal
    rem_protein = macros["protein_g"] - eaten_protein
    rem_carbs = macros["carbs_g"] - eaten_carbs
    rem_fat = macros["fat_g"] - eaten_fat
    
    return f"""🎯 Übersicht für heute ({goal}):
-----------------------------
⚡ Kalorien: {round(eaten_cal)} / {macros['calories']} kcal  →  {round(rem_cal)} übrig
🥩 Protein:  {round(eaten_protein)} / {macros['protein_g']}g  →  {round(rem_protein)}g übrig
🍚 Carbs:    {round(eaten_carbs)} / {macros['carbs_g']}g  →  {round(rem_carbs)}g übrig
🥑 Fett:     {round(eaten_fat)} / {macros['fat_g']}g  →  {round(rem_fat)}g übrig"""
#############CHAT#########################
# Conversation history with max limit to control context window
MAX_HISTORY = 10
conversation_history = []



def process_action(data, raw_answer):
    """Executes the action and returns the result text."""
    if not data:
        return raw_answer
    
    action = data.get("action")

    if action == "save_workout":
        if not validate_workout_data(data):
            return "❌ Could not read workout correctly. Please try again!"
        workout_date = data.get("date", str(date.today()))
        save_workout(data["exercises"], workout_date)
        result = f"💪 Workout saved for {workout_date}! {len(data['exercises'])} exercise(s) logged."
        for e in data["exercises"]:
            plateau_msg = detect_plateau(e["exercise"])
            if "⚠️ Plateau detected" in plateau_msg:
                result += f"\n\n{plateau_msg}"
        return result

    elif action == "get_workouts":
        return get_recent_workouts()

    elif action == "save_profile":
        save_user_profile(data["name"], data["gender"], data["height_cm"],
                          data["birth_year"], data["activity_level"], data["goal"])
        return f"✅ Profile saved! Welcome, {data['name']}! 💪"

    elif action == "update_goal":
        update_user_goal(data["goal"])
        return f"✅ Goal updated to: {data['goal']}"

    elif action == "log_weight":
        log_date = data.get("date", str(date.today()))
        log_weight(data["weight_kg"], log_date)
        return f"⚖️ Weight saved: {data['weight_kg']}kg on {log_date}"

    elif action == "get_progress":
        return get_progress_summary()

    elif action == "log_food":
        log_date = data.get("date", str(date.today()))
        return handle_food_logging(data["foods"], log_date)

    elif action == "get_nutrition":
        target_date = data.get("date", str(date.today()))
        return get_nutrition_summary(target_date)

    elif action == "remaining_calories":
        target_date = data.get("date", str(date.today()))
        return get_remaining_calories(target_date)

    elif action == "search_knowledge":
        context = suche_in_docs(data["question"])
        messages2 = [
            SystemMessage(content="You are a fitness coach. Answer based on the following context. Always respond in German."),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {data['question']}")
        ]
        answer2 = llm.invoke(messages2)
        return f"📚 {answer2.content}"

    else:
        return raw_answer


def chat(user_input):
    global conversation_history

    conversation_history.append(HumanMessage(content=user_input))
    if len(conversation_history) > MAX_HISTORY:
        conversation_history = conversation_history[-MAX_HISTORY:]

    messages = [
        SystemMessage(content=AGENTS_CONTEXT + "\n\n" + SYSTEM_PROMPT +
                      "\n\n" + get_date_context() +
                      "\n\n" + load_profile_context()),
        *conversation_history
    ]

    response = llm.invoke(messages)
    answer = response.content.strip()

    data = parse_response(answer)
    result = process_action(data, answer)

    # Save the ACTUAL result to history so the agent remembers what happened
    conversation_history.append(AIMessage(content=result))

    return result

"""
def chat(user_input):
    global conversation_history

    conversation_history.append(HumanMessage(content=user_input))

    # Keep history within limit
    if len(conversation_history) > MAX_HISTORY:
        conversation_history = conversation_history[-MAX_HISTORY:]

    messages = [
        SystemMessage(content=AGENTS_CONTEXT + "\n\n" + SYSTEM_PROMPT + 
                    "\n\n" + get_date_context() + 
                    "\n\n" + load_profile_context()),
        *conversation_history
    ]

    response = llm.invoke(messages)
    answer = response.content.strip()
    #print(f"🔍 Raw answer: {answer}")
    conversation_history.append(response)

    data = parse_response(answer)
    if data:
        action = data.get("action")

        if action == "save_workout":
            if not validate_workout_data(data):
                return "❌ Could not read workout correctly. Please try again!"
            workout_date = data.get("date", str(date.today()))
            save_workout(data["exercises"], workout_date)

            result = f"💪 Workout saved for {workout_date}! {len(data['exercises'])} exercise(s) logged."

            # Automatic plateau check for each exercise
            for e in data["exercises"]:
                plateau_msg = detect_plateau(e["exercise"])
                if "⚠️ Plateau detected" in plateau_msg:
                    result += f"\n\n{plateau_msg}"
            
            return result

        elif action == "get_workouts":
            return get_recent_workouts()
        
        elif action == "save_profile":
            save_user_profile(
                data["name"], data["gender"], data["height_cm"],
                data["birth_year"], data["activity_level"], data["goal"]
            )
            return f"✅ Profile saved! Welcome, {data['name']}! 💪"

        elif action == "update_goal":
            update_user_goal(data["goal"])
            return f"✅ Goal updated to: {data['goal']}"

        elif action == "log_weight":
            log_date = data.get("date", str(date.today()))
            log_weight(data["weight_kg"], log_date)
            return f"⚖️ Weight saved: {data['weight_kg']}kg on {log_date}"

        elif action == "get_progress":
            return get_progress_summary()
        
        elif action == "calculate_macros":
            return get_macros_for_user()

        elif action == "get_pr":
            return get_pr(data["exercise"])

        elif action == "detect_plateau":
            return detect_plateau(data["exercise"])

        elif action == "get_volume":
            return calculate_volume(data["exercise"])

        elif action == "calculate_1rm":
            result = calculate_1rm(data["weight_kg"], data["reps"])
            return f"💪 Estimated 1RM: {result}kg"

        elif action == "search_knowledge":
            context = suche_in_docs(data["question"])
            messages2 = [
                SystemMessage(content="You are a fitness coach. Answer the question based on the following context. Always respond in German."),
                HumanMessage(content=f"Context:\n{context}\n\nQuestion: {data['question']}")
            ]
            answer2 = llm.invoke(messages2)
            return f"📚 {answer2.content}"
        
        elif action == "log_food":
            log_date = data.get("date", str(date.today()))
            return handle_food_logging(data["foods"], log_date)

        elif action == "get_nutrition":
            target_date = data.get("date", str(date.today()))
            return get_nutrition_summary(target_date)
        
        elif action == "remaining_calories":
            target_date = data.get("date", str(date.today()))
            return get_remaining_calories(target_date)

        else:
            return answer
    else:
        return answer

"""



if __name__ == "__main__":
    create_tables()

    # Profil check on startup
    profil = get_user_profile()
    if not profil:
        print("👋  Welcome! I see you don't have a profile yet")
        print("  Tell me: 'Create my profile: [Name], [Height]cm, [Year of birth], [Gender], [Activity], Goal: [Goal]'")
    else:
        print(f"👋 Welcome back, {profil[1]}!")

    print("🏋️ Fitness Agent ready! (Type 'exit' to quit)")
    print("-" * 50)

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        answer = chat(user_input)
        print(f"Agent: {answer}\n")