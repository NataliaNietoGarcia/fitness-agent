from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import os
import json
import re
from datetime import date, timedelta

from database.db import (get_user_profile, save_user_profile, update_user_goal,
                          log_weight, get_weight_history, log_food, get_daily_nutrition,
                          update_food_entry, find_recent_food_by_keyword)
from tools.calculations import (calculate_tdee, calculate_macros, calculate_1rm,
                                 calculate_volume, get_pr, detect_plateau,
                                 check_workout_plausibility, get_weekly_volume,
                                 get_weekly_volume_all_exercises, get_training_facts,
                                 get_nutrition_facts, get_weekly_nutrition_facts)
from tools.nutrition import search_food_options, get_nutrition_by_exact_name
from memory.chroma import suche_in_docs

# LangSmith monitoring
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "fitness-agent"

load_dotenv()

llm = ChatOpenAI(
    model="openai-gpt-oss-120b",
    api_key=os.getenv("GWDG_API_KEY"),
    base_url="https://chat-ai.academiccloud.de/v1"
)

MAX_HISTORY = 10
conversation_history = []

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

Extract weight, sets, and reps exactly as stated by the user, in whatever order 
they appear (e.g. "20 Sätze X 5kg 50 Wiederholungen" or "X 5kg 20x50"). 
Do NOT ask for clarification just because a number seems unusual — a separate 
system check will flag implausible values automatically after extraction. 
Only ask if a number is genuinely missing from the message.
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

If the user asks for their calorie/macro targets (without asking about remaining amounts), respond ONLY with:
{
    "action": "calculate_macros"
}

If the user asks for their PR (personal record) of an exercise, respond ONLY with:
{
    "action": "get_pr",
    "exercise": "exercise name"
}

If the user explicitly asks whether they have a plateau in an exercise, respond ONLY with:
{
    "action": "detect_plateau",
    "exercise": "exercise name"
}

If the user asks about training volume (e.g. "Wie war mein Volumen diese Woche?"), respond ONLY with:
{
    "action": "get_volume",
    "exercise": "exercise name, or 'all' if not specified"
}

If the user asks about their weekly nutrition or weekly average calories
(e.g. "Wie war meine Ernährung diese Woche?", "Wöchentliche Kalorien"), respond ONLY with:
{
    "action": "weekly_nutrition"
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

If the user logs food they ate, extract the food name and amount in grams.
If the user does NOT specify an amount, estimate a reasonable typical portion
size yourself using general knowledge (e.g. a bread roll ~80g, an egg ~60g,
a banana ~120g, a glass of juice ~200ml). Do NOT ask the user for the exact
weight — just use your best estimate and proceed.
Only ask for clarification if the food itself is too vague to estimate at all
(e.g. "etwas Snacks" with no further description).
Respond ONLY with the raw JSON (no text before or after):
{
    "action": "log_food",
    "date": "YYYY-MM-DD",
    "foods": [
        {"food_name": "name", "amount_g": 0.0, "estimated": true, "confirmed": false}
    ]
}
If the user is confirming a previously flagged amount (e.g. "Ja", "stimmt",
"ich bestätige", "genau" — as a reply to a plausibility warning), look at the
conversation history to find which food and amount was flagged, and respond
with the SAME log_food JSON but set "confirmed": true for that food. Do NOT
ask again and do NOT change the amount.

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

If the user wants to correct/change a previously logged food item
(e.g. "Ich meinte gebraten beim Hähnchen", "ändere den Reis zu roh"), respond ONLY with:
{
    "action": "correct_food",
    "food_keyword": "the food they're referring to (e.g. 'Hähnchen')",
    "new_variant": "the correction they want (e.g. 'gebraten')"
}

If the user asks for training feedback or how their progress looks
(e.g. "Gib mir Feedback zu meinem Bankdrücken", "Wie läuft mein Training?"), respond ONLY with:
{
    "action": "training_feedback",
    "exercise": "exercise name"
}

If the user asks for nutrition feedback or how their eating looks today
(e.g. "Wie läuft meine Ernährung heute?", "Gib mir Feedback zu meiner Ernährung"), respond ONLY with:
{
    "action": "nutrition_feedback"
}

## Plausibility check (before logging):
- Food amounts: typical portions are 20-1000g. If an amount seems too small
  (e.g. "20g Hähnchenbrust" — usually people eat 100-300g) or too large,
  ask for confirmation instead of logging directly.
- Workout weights: if a weight seems implausibly low or high for the exercise
  (e.g. "12kg Beinpresse" when the typical range is 40-300kg), ask the user
  to confirm the number before saving.
If a value is plausible, log it normally without asking.

For all other messages, respond normally as a coach in German.
"""


def load_agents_md():
    try:
        with open("AGENTS.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


AGENTS_CONTEXT = load_agents_md()


# ============================================================
# CONTEXT HELPERS
# ============================================================

def get_date_context():
    """Provides today's date and the last 7 days as weekday references."""
    today = date.today()
    weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    context = f"Today is {weekday[today.weekday()]}, {today.strftime('%Y-%m-%d')}.\n"
    context += "Recent days:\n"
    for i in range(1, 8):
        day = today - timedelta(days=i)
        context += f"- {weekday[day.weekday()]}: {day.strftime('%Y-%m-%d')}\n"
    return context


def load_profile_context():
    """Injects the current user profile into the system prompt."""
    profile = get_user_profile()
    if not profile:
        return ""

    _, name, gender, height, birth_year, activity, goal, _, _ = profile
    age = date.today().year - birth_year

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


# ============================================================
# RESPONSE PARSING & VALIDATION
# ============================================================

def parse_response(response_text: str):
    """Extracts a JSON action object from the LLM response, if present."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        text_before = response_text[:json_match.start()].strip()
        if len(text_before) > 50:
            return None  # likely a conversational reply, not an action
        try:
            return json.loads(json_match.group())
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


def check_food_plausibility(food_name, amount_g):
    """Basic sanity check for food amounts."""
    if amount_g < 5:
        return f"⚠️ {amount_g}g {food_name} wirkt sehr wenig — meintest du vielleicht {amount_g * 10}g?"
    if amount_g > 2000:
        return f"⚠️ {amount_g}g {food_name} wirkt sehr viel — bitte bestätige die Menge."
    return None


# ============================================================
# WORKOUT
# ============================================================

def save_workout(exercises, workout_date=None):
    from database.db import get_connection
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


def get_recent_workouts():
    from database.db import get_connection
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
        return "Noch keine Workouts gespeichert!"

    result = "📊 Deine letzten Workouts:\n" + "-" * 40 + "\n"
    for row in rows:
        sets_label = "Satz" if row[3] == 1 else "Sätze"
        result += f"📅 {row[0]} | 💪 {row[1]} | ⚖️ {row[2]}kg | {row[3]} {sets_label} x {row[4]} Wdh\n"
    return result


def handle_get_volume(exercise):
    if exercise.lower() == "all":
        rows = get_weekly_volume_all_exercises(weeks=1)
        if not rows:
            return "❌ Keine Trainingsdaten für diese Woche gefunden."

        response = "📊 **Wochenvolumen (letzte 7 Tage):**\n\n"
        response += "| Übung | Sätze | Volumen |\n"
        response += "|-------|-------|--------|\n"
        for ex, sets, volume in rows:
            response += f"| {ex} | {sets} | {volume:.0f}kg |\n"
        return response

    weekly_sets = get_weekly_volume(exercise, weeks=1)
    return calculate_volume(exercise) + f"\n📊 Gesamt diese Woche: {weekly_sets} Sätze"


def handle_training_feedback(exercise):
    facts = get_training_facts(exercise)
    if not facts["recent_sessions"]:
        return f"❌ Keine Daten für {exercise} gefunden."

    rag_context = suche_in_docs(
        "empfohlenes Trainingsvolumen Sätze pro Woche Hypertrophie progressive overload plateau"
    )

    prompt = f"""You are a fitness coach. Give the user brief, science-based feedback
about their training for "{exercise}", based on the following data and scientific context.

## User's training data:
- Sets this week: {facts['weekly_sets']}
- Recent sessions: {facts['recent_sessions']}
- Same weight for last 3+ sessions: {facts['same_weight_streak']}

## Scientific context (knowledge base):
{rag_context}

Compare the user's data to the recommendations in the context. Give 2-3 sentences
of concrete, motivating feedback in German. Mention the source if you cite a number
(e.g. "laut Schoenfeld 2017"). If everything looks good, say so briefly."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return f"💪 {response.content}"


def check_automatic_training_feedback(exercises):
    """Runs a RAG-based check after logging a workout; stays silent if nothing stands out."""
    hints = []
    rag_context = suche_in_docs("Trainingsvolumen progressive overload Empfehlung Sätze pro Woche")

    for e in exercises:
        facts = get_training_facts(e["exercise"])
        prompt = f"""The user just logged a workout for "{e['exercise']}".

Training data:
- Sets this week: {facts['weekly_sets']}
- Recent sessions (most recent first): {facts['recent_sessions']}
- Same weight for 3+ consecutive sessions: {facts['same_weight_streak']}

Scientific context: {rag_context}

Is there anything worth flagging? For example: weekly volume far outside the
recommended range, or a clear sign it's time to increase weight/reps
(progressive overload). If yes, give ONE short, concrete, motivating German
sentence with a brief reason. If everything looks fine or there's not enough
data to say anything meaningful, respond with exactly: NONE"""

        check = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        if check != "NONE":
            hints.append(check)

    return hints


# ============================================================
# WEIGHT & PROGRESS
# ============================================================

def get_progress_summary():
    weight_history = get_weight_history(10)
    if not weight_history:
        return "❌ Noch keine Gewichtsdaten. Sag mir einfach 'Ich wiege X kg' um zu starten!"

    result = "📊 Dein Gewichtsverlauf:\n" + "-" * 40 + "\n"
    for row in weight_history:
        result += f"📅 {row[0]} | ⚖️ {row[1]}kg"
        if row[2]:
            result += f" | 📝 {row[2]}"
        result += "\n"

    if len(weight_history) >= 2:
        diff = weight_history[0][1] - weight_history[-1][1]
        emoji = "📈" if diff > 0 else "📉"
        result += f"\n{emoji} Veränderung: {diff:+.1f}kg"

    return result


# ============================================================
# NUTRITION TARGETS
# ============================================================

def get_macros_for_user():
    profile = get_user_profile()
    if not profile:
        return "❌ Kein Profil gefunden! Bitte erstelle zuerst dein Profil."

    _, name, gender, height, birth_year, activity, goal, _, _ = profile
    age = date.today().year - birth_year

    weight_history = get_weight_history(1)
    if not weight_history:
        return " Wie viel wiegst du gerade? Ich brauche dein Gewicht, um deine Ziele zu berechnen."

    current_weight = weight_history[0][1]
    tdee = calculate_tdee(current_weight, height, age, gender, activity)
    macros = calculate_macros(tdee, goal, current_weight)

    return f"""🎯 Deine Ernährungsziele ({goal}):
-----------------------------
⚡ TDEE: {tdee} kcal
🎯 Zielkalorien: {macros['calories']} kcal
🥩 Protein: {macros['protein_g']}g
🍚 Carbs: {macros['carbs_g']}g
🥑 Fett: {macros['fat_g']}g"""


def get_remaining_calories(target_date):
    profile = get_user_profile()
    if not profile:
        return "❌ Kein Profil gefunden."

    _, name, gender, height, birth_year, activity, goal, _, _ = profile
    age = date.today().year - birth_year
    weight_history = get_weight_history(1)
    if not weight_history:
        return "Wie viel wiegst du gerade? Ich brauche dein Gewicht, um deine Kalorienziele zu berechnen."

    current_weight = weight_history[0][1]
    tdee = calculate_tdee(current_weight, height, age, gender, activity)
    macros = calculate_macros(tdee, goal, current_weight)

    foods = get_daily_nutrition(target_date)
    eaten_cal = sum(f[2] for f in foods)
    eaten_protein = sum(f[3] for f in foods)
    eaten_carbs = sum(f[4] for f in foods)
    eaten_fat = sum(f[5] for f in foods)

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


def get_nutrition_summary(target_date):
    foods = get_daily_nutrition(target_date)
    if not foods:
        return f"❌ Keine Mahlzeiten für {target_date} gespeichert."

    response = f"🍽️ Ernährung am {target_date}:\n" + "-" * 40 + "\n"
    total_cal = total_p = total_c = total_f = 0
    for food in foods:
        response += f"• {food[0]} ({food[1]}g): {food[2]}kcal\n"
        total_cal += food[2]
        total_p += food[3]
        total_c += food[4]
        total_f += food[5]

    response += f"\n📊 Tagessumme: {round(total_cal)}kcal | P:{round(total_p)}g C:{round(total_c)}g F:{round(total_f)}g"
    return response


def handle_weekly_nutrition():
    facts = get_weekly_nutrition_facts()
    if not facts:
        return "❌ Keine Ernährungsdaten für diese Woche gefunden."

    profile = get_user_profile()
    if not profile:
        return "❌ Kein Profil gefunden."

    _, name, gender, height, birth_year, activity, goal, _, _ = profile
    age = date.today().year - birth_year
    weight_history = get_weight_history(1)
    current_weight = weight_history[0][1] if weight_history else None

    response = f"📊 **Wochenübersicht ({facts['days_logged']} Tage geloggt):**\n\n"
    response += f"Ø Kalorien: {facts['avg_calories']} kcal/Tag\n"
    response += f"Ø Protein: {facts['avg_protein_g']}g/Tag\n"
    response += f"Ø Carbs: {facts['avg_carbs_g']}g/Tag\n"
    response += f"Ø Fett: {facts['avg_fat_g']}g/Tag\n"

    if current_weight:
        tdee = calculate_tdee(current_weight, height, age, gender, activity)
        target_macros = calculate_macros(tdee, goal, current_weight)
        response += f"\n🎯 Ziel: {target_macros['calories']} kcal/Tag\n"
        diff = facts['avg_calories'] - target_macros['calories']
        response += f"📈 Durchschnittliche Abweichung: {diff:+.0f} kcal/Tag"

    return response


def handle_nutrition_feedback(target_date=None):
    facts = get_nutrition_facts(target_date)
    if facts and facts.get("error") == "no_profile":
        return "❌ Ich habe noch kein Profil von dir. Sag mir kurz: Name, Größe, Geburtsjahr, Geschlecht, Aktivitätslevel und dein Ziel!"
    if facts and facts.get("error") == "no_weight":
        return "⚖️ Wie viel wiegst du gerade? Ich brauche dein Gewicht, um dir Feedback geben zu können."
    if not facts:
        return "❌ Ich brauche dein Profil und Gewicht, um Feedback zu geben."
    if facts["num_meals_logged"] == 0:
        return "📊 Noch nichts gegessen heute — ich kann noch kein Feedback geben."

    rag_context = suche_in_docs(
        f"Makronährstoffe Protein Kohlenhydrate Fett Zucker Empfehlung {facts['goal']}"
    )

    prompt = f"""You are a fitness and nutrition coach. Give the user brief,
science-based feedback on their nutrition today, based on the data and context below.

## User's goal: {facts['goal']}
## Time of day: {facts['current_hour']}:00 ({facts['day_progress_pct']}% of day passed)

## Eaten so far today:
- Calories: {facts['eaten']['calories']} / {facts['target']['calories']} target
- Protein: {facts['eaten']['protein_g']}g / {facts['target']['protein_g']}g target
- Carbs: {facts['eaten']['carbs_g']}g / {facts['target']['carbs_g']}g target
- Fat: {facts['eaten']['fat_g']}g / {facts['target']['fat_g']}g target
- Sugar: {facts['eaten']['sugar_g']}g

## Scientific context (knowledge base):
{rag_context}

Consider the time of day: if it's late and protein is far below target, flag it clearly.
If sugar or fat looks excessive relative to the target, mention it with the WHO/scientific
guideline. If everything looks on track, say so briefly and positively.
Give 2-4 sentences, in German, concrete and motivating. Cite sources briefly if relevant
(e.g. "laut WHO-Richtlinie")."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return f"🍎 {response.content}"


def check_automatic_nutrition_feedback(log_date):
    """Runs a RAG-based check after logging food; stays silent if nothing stands out."""
    facts = get_nutrition_facts(log_date)
    if not facts or facts["num_meals_logged"] == 0:
        return None

    rag_context = suche_in_docs(
        f"Makronährstoffe Empfehlung Protein Kohlenhydrate Fett Zucker {facts['goal']}"
    )

    prompt = f"""The user's nutrition so far today ({facts['current_hour']}:00,
{facts['day_progress_pct']}% of the day passed):
- Calories: {facts['eaten']['calories']} / {facts['target']['calories']} target
- Protein: {facts['eaten']['protein_g']}g / {facts['target']['protein_g']}g target
- Carbs: {facts['eaten']['carbs_g']}g / {facts['target']['carbs_g']}g target
- Fat: {facts['eaten']['fat_g']}g / {facts['target']['fat_g']}g target
- Sugar: {facts['eaten']['sugar_g']}g

Scientific context: {rag_context}

Considering the time of day and the goal ({facts['goal']}), is anything already
notably off track? If yes:
1. Name the issue briefly with the relevant guideline.
2. Give ONE concrete, actionable tip for the REST of today.
3. Remind the user that body composition change depends on the WEEKLY average,
   not a single day — one high day is not a failure.
Keep it to 3-4 sentences total, German, supportive tone (not shaming).
If nothing is concerning yet, respond with exactly: NONE"""

    check = llm.invoke([HumanMessage(content=prompt)]).content.strip()
    return check if check != "NONE" else None


# ============================================================
# FOOD LOGGING
# ============================================================

def choose_best_food(user_input_name, candidate_names):
    """Lets the LLM pick the most likely food, or flag genuine ambiguity."""
    if not candidate_names:
        return None
    if len(candidate_names) == 1:
        return candidate_names[0]

    candidate_list = "\n".join([f"- {c}" for c in candidate_names])
    prompt = f"""The user logged the food "{user_input_name}".

Pick the SINGLE most likely match from the list below.
Use common-sense defaults: e.g. "Ei" almost always means "Hühner Ei" (chicken egg)
unless stated otherwise. "Milch" without further info usually means cow's milk.

Only respond with "UNCLEAR" if the food name is genuinely ambiguous between
very different foods with no reasonable default.

Otherwise respond with ONLY the exact name from the list, nothing else.

List:
{candidate_list}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    chosen = response.content.strip()

    if chosen == "UNCLEAR":
        return None
    if chosen in candidate_names:
        return chosen
    return candidate_names[0]  # fallback: shortest match


def suggest_alternative_name(food_name):
    """Asks the LLM for an alternative/synonym name if nothing was found."""
    prompt = f"""The food "{food_name}" was not found in a German nutrition database (BLS).
German nutrition databases often use different or more technical terms.
Suggest ONE alternative name that might exist in the database instead.
Examples: "Hafermilch" → "Haferdrink", "Hähnchenbrust" → "Hähnchen Brustfilet"

Respond with ONLY the alternative name, nothing else."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def handle_food_logging(foods, log_date):
    results = []
    not_found = []
    needs_clarification = []

    for f in foods:
        options = search_food_options(f["food_name"])

        if len(options) == 0:
            alternative = suggest_alternative_name(f["food_name"])
            options = search_food_options(alternative)
            if len(options) == 0:
                not_found.append(f["food_name"])
                continue

        if len(options) == 1:
            chosen_name = options[0]["name"]
        else:
            candidate_names = [o["name"] for o in options]
            chosen_name = choose_best_food(f["food_name"], candidate_names)
            if chosen_name is None:
                option_list = "\n".join([f"  • {c}" for c in candidate_names[:8]])
                needs_clarification.append(
                    f"🤔 Für '{f['food_name']}' ({f['amount_g']}g) — welche Variante meinst du?\n{option_list}"
                )
                continue

        plausibility_warning = check_food_plausibility(f["food_name"], f["amount_g"])
        if plausibility_warning and not f.get("confirmed", False):
            needs_clarification.append(plausibility_warning)
            continue

        nutrition = get_nutrition_by_exact_name(chosen_name, f["amount_g"])
        if nutrition:
            log_food(nutrition["name"], nutrition["amount_g"], nutrition["calories"],
                      nutrition["protein_g"], nutrition["carbs_g"], nutrition["fat_g"],
                      nutrition.get("sugar_g", 0), log_date)
            results.append(nutrition)

    response = ""
    if results:
        response += "🍽️ Gespeichert:\n" + "-" * 40 + "\n"
        for r in results:
            response += f"• {r['name']} ({r['amount_g']}g): {r['calories']}kcal | P:{r['protein_g']}g C:{r['carbs_g']}g F:{r['fat_g']}g\n"

    if not_found:
        response += f"\n⚠️ Nicht gefunden: {', '.join(not_found)}"

    if needs_clarification:
        response += "\n" + "\n\n".join(needs_clarification)

    if results:
        feedback = check_automatic_nutrition_feedback(log_date)
        if feedback:
            response += f"\n\n💡 {feedback}"

    return response


def handle_food_correction(food_keyword, new_variant):
    """Finds a recently logged food and corrects it based on user feedback."""
    entry = find_recent_food_by_keyword(food_keyword)
    if not entry:
        return f"❌ Konnte keinen kürzlichen Eintrag zu '{food_keyword}' finden."

    entry_id, old_name, amount_g = entry
    search_term = f"{food_keyword} {new_variant}"
    options = search_food_options(search_term)
    if not options:
        return f"❌ Konnte '{search_term}' nicht in der Datenbank finden."

    chosen_name = options[0]["name"] if len(options) == 1 else choose_best_food(
        search_term, [o["name"] for o in options]
    )

    nutrition = get_nutrition_by_exact_name(chosen_name, amount_g)
    if not nutrition:
        return f"❌ Fehler beim Nachschlagen von '{chosen_name}'."

    update_food_entry(entry_id, nutrition["name"], amount_g, nutrition["calories"],
                       nutrition["protein_g"], nutrition["carbs_g"], nutrition["fat_g"])

    return (f"✅ Aktualisiert: {old_name} → **{nutrition['name']}** ({amount_g}g): "
            f"{nutrition['calories']}kcal | P:{nutrition['protein_g']}g "
            f"C:{nutrition['carbs_g']}g F:{nutrition['fat_g']}g")


# ============================================================
# ACTION DISPATCH
# ============================================================

def process_action(data, raw_answer):
    """Executes the action requested by the LLM and returns the result text."""
    if not data:
        return raw_answer

    action = data.get("action")

    if action == "save_workout":
        if not validate_workout_data(data):
            return "❌ Konnte das Workout nicht richtig lesen. Bitte nochmal versuchen!"

        for e in data["exercises"]:
            warnings = check_workout_plausibility(e["exercise"], e["weight_kg"], e["sets"], e["reps"])
            if warnings:
                return "\n".join(warnings) + "\n\nBitte bestätige die Werte oder korrigiere sie."

        workout_date = data.get("date", str(date.today()))
        save_workout(data["exercises"], workout_date)

        result = f"💪 Workout gespeichert für {workout_date}! {len(data['exercises'])} Übung(en) eingetragen."

        for e in data["exercises"]:
            plateau_msg = detect_plateau(e["exercise"])
            if "⚠️" in plateau_msg:
                result += f"\n\n{plateau_msg}"

        for hint in check_automatic_training_feedback(data["exercises"]):
            result += f"\n\n💡 {hint}"

        return result

    elif action == "get_workouts":
        return get_recent_workouts()

    elif action == "save_profile":
        save_user_profile(data["name"], data["gender"], data["height_cm"],
                           data["birth_year"], data["activity_level"], data["goal"])
        return f"✅ Profil gespeichert! Willkommen, {data['name']}! 💪"

    elif action == "update_goal":
        update_user_goal(data["goal"])
        return f"✅ Ziel aktualisiert auf: {data['goal']}"

    elif action == "log_weight":
        log_date = data.get("date", str(date.today()))
        log_weight(data["weight_kg"], log_date)
        return f"⚖️ Gewicht gespeichert: {data['weight_kg']}kg am {log_date}"

    elif action == "get_progress":
        return get_progress_summary()

    elif action == "calculate_macros":
        return get_macros_for_user()

    elif action == "get_pr":
        return get_pr(data["exercise"])

    elif action == "detect_plateau":
        return detect_plateau(data["exercise"])

    elif action == "get_volume":
        return handle_get_volume(data["exercise"])

    elif action == "weekly_nutrition":
        return handle_weekly_nutrition()

    elif action == "calculate_1rm":
        result = calculate_1rm(data["weight_kg"], data["reps"])
        return f"💪 Geschätztes 1RM: {result}kg"

    elif action == "search_knowledge":
        context = suche_in_docs(data["question"])
        messages = [
            SystemMessage(content="You are a fitness coach. Answer based on the following context. Always respond in German."),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {data['question']}")
        ]
        answer = llm.invoke(messages)
        return f"📚 {answer.content}"

    elif action == "log_food":
        log_date = data.get("date", str(date.today()))
        return handle_food_logging(data["foods"], log_date)

    elif action == "get_nutrition":
        target_date = data.get("date", str(date.today()))
        return get_nutrition_summary(target_date)

    elif action == "remaining_calories":
        target_date = data.get("date", str(date.today()))
        return get_remaining_calories(target_date)

    elif action == "correct_food":
        return handle_food_correction(data["food_keyword"], data["new_variant"])

    elif action == "training_feedback":
        return handle_training_feedback(data["exercise"])

    elif action == "nutrition_feedback":
        return handle_nutrition_feedback()

    return raw_answer


# ============================================================
# CHAT
# ============================================================

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

    # Store the actual result, not the raw JSON, so the agent remembers what happened
    conversation_history.append(AIMessage(content=result))

    return result


if __name__ == "__main__":
    from database.db import create_tables
    create_tables()

    profile = get_user_profile()
    if not profile:
        print("👋 Willkommen! Ich sehe, du hast noch kein Profil.")
        print("   Sag mir: 'Erstelle mein Profil: [Name], [Größe]cm, [Geburtsjahr], [Geschlecht], [Aktivität], Ziel: [Ziel]'")
    else:
        print(f"👋 Willkommen zurück, {profile[1]}!")

    print("🏋️ Fitness Agent bereit! (Schreibe 'exit' zum Beenden)")
    print("-" * 50)

    while True:
        user_input = input("Du: ")
        if user_input.lower() == "exit":
            break
        print(f"Agent: {chat(user_input)}\n")