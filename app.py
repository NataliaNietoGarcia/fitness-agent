import streamlit as st
import streamlit.components.v1 as components
from agent import chat, choose_best_food
from database.db import (create_tables, get_user_profile,save_user_profile, get_daily_nutrition_with_id, update_food_entry, delete_food_entry, log_weight)
from tools.nutrition import get_nutrition_by_exact_name, search_food_options
from tools.charts import (get_weight_chart_data, get_exercise_progress_data,
                          get_volume_chart_data, get_all_exercises)
from tools.calculations import get_weekly_nutrition_facts
from datetime import date, timedelta

st.set_page_config(page_title="Fitness Agent", page_icon="🏋️", layout="wide")
create_tables()

def get_user_avatar():
    profile = get_user_profile()
    if profile:
        gender = profile[2]  # gender column
        if gender and gender.lower() == "male":
            return "👨"
        elif gender and gender.lower() == "female":
            return "👩"
    return "🧑"  # fallback if no profile yet

# ============ Custom CSS ============
st.markdown("""
            
            
<style>
    html, body {
        overflow: hidden;
    }

    [data-testid="stAppViewContainer"] {
        height: 100vh;
        overflow: hidden;
    }

    .block-container {
        height: 100vh;
        overflow: hidden;
        padding-bottom: 0 !important;
        padding-top: 0rem !important;
    } 
    
    [data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 8px;
        margin-bottom: 8px;
        background-color: #FAFAFA;
        border: 1px solid #EEEEEE;
    }
    [data-testid="stChatInput"] {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: white;
        padding: 1rem 2rem;
        z-index: 999;
        border-top: 1px solid #EEEEEE;
    }
            
    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0px;
    }

    header[data-testid="stHeader"] {
        height: 0px;
        visibility: hidden;
    }

    .stTabs [data-baseweb="tab-panel"] {
        height: calc(100vh - 200px);  /* Höhe anpassen je nach Logo/Tabs-Größe */
        overflow-y: auto;
        padding-top: 0px !important;
    }
    .stButton button {
        border-radius: 20px;
        font-weight: 600;
        background-color: #EA5B0C;
        color: white;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #C94A08;
        transform: scale(1.03);
        box-shadow: 0 4px 12px rgba(234, 91, 12, 0.3);
    }
    hr { border-color: #EEEEEE; }
    .stCaption, [data-testid="stCaptionContainer"] { color: #666666 !important; }
    h2, h3 { color: #1A1A1A; }
    
    /* Sticky tabs — stay fixed at the top while scrolling */
    .stTabs [data-baseweb="tab-list"] {
        position: sticky;
        top: 0;
        z-index: 998;
        background-color: white;
        padding-top: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px 12px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFF3EC;
        color: #EA5B0C !important;
    }
</style>
""", unsafe_allow_html=True)



st.markdown(
    """
    <div style="text-align: center; margin-top:0px; margin-bottom:0px">
        <img src="app/static/logo.png" width="220">
    </div>
    """,
    unsafe_allow_html=True
)

# ============ Tabs ============
tab_chat, tab_progress, tab_nutrition = st.tabs(["💬 Chat", "📊 Fortschritt", "🍽️ Ernährung"])

# ---------- TAB 1: Chat ----------
with tab_chat:
    profile = get_user_profile()

    if not profile:
        st.subheader("👋 Willkommen! Erstelle zuerst dein Profil")

        with st.form("profile_form"):
            name = st.text_input("Name")
            height_cm = st.number_input("Größe (cm)", min_value=100, max_value=250, value=175)
            weight_kg = st.number_input("Aktuelles Gewicht (kg)", min_value=30.0, max_value=300.0, value=75.0, step=0.5)
            birth_year = st.number_input("Geburtsjahr", min_value=1930, max_value=2020, value=1980)

            gender_label = st.selectbox("Geschlecht", ["männlich", "weiblich"])
            activity_label = st.selectbox(
                "Aktivitätslevel",
                ["wenig aktiv", "leicht aktiv", "moderat aktiv", "aktiv", "sehr aktiv"]
            )
            goal_label = st.selectbox("Ziel", ["Muskelaufbau", "Fettabbau", "Recomp"])

            submitted = st.form_submit_button("Profil erstellen")

            if submitted:
                gender_map = {"männlich": "male", "weiblich": "female"}
                activity_map = {
                    "wenig aktiv": "sedentary", "leicht aktiv": "light",
                    "moderat aktiv": "moderate", "aktiv": "active", "sehr aktiv": "very_active"
                }
                goal_map = {"Muskelaufbau": "muscle_gain", "Fettabbau": "fat_loss", "Recomp": "recomp"}

                save_user_profile(
                    name, gender_map[gender_label], height_cm, birth_year,
                    activity_map[activity_label], goal_map[goal_label]
                )

                log_weight(weight_kg)
                st.success(f"Profil für {name} erstellt! 🎉")
                st.rerun()

    else:
        if "messages" not in st.session_state:
            st.session_state.messages = []
            welcome = f"👋 Willkommen zurück, {profile[1]}! Wie kann ich dir heute helfen?"
            st.session_state.messages.append({"role": "assistant", "content": welcome})

        user_avatar = get_user_avatar()

        # Chat history scrolls INSIDE this fixed-height container —
        # tabs, logo, and page stay stable no matter how long the chat gets
        chat_container = st.container(height=480)

        with chat_container:
            for message in st.session_state.messages:
                avatar = "🏋️" if message["role"] == "assistant" else user_avatar
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        if user_input := st.chat_input("Schreibe eine Nachricht..."):
            components.html("""
                <script>
                    window.parent.document.activeElement.blur();
                </script>
            """, height=0)

            st.session_state.messages.append({"role": "user", "content": user_input})

            with chat_container:
                with st.chat_message("user", avatar=user_avatar):
                    st.markdown(user_input)

                with st.chat_message("assistant", avatar="🏋️"):
                    with st.spinner("Denke nach..."):
                        response = chat(user_input)
                    st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
# ---------- TAB 2: Fortschritt ----------
with tab_progress:
    st.subheader("Gewichtsverlauf")
    weight_data = get_weight_chart_data()
    if weight_data is not None:
        st.line_chart(weight_data)
    else:
        st.info("Noch keine Gewichtsdaten.")

    st.divider()

    exercises = get_all_exercises()
    if exercises:
        st.subheader("Übungs-Progression")
        selected = st.selectbox("Übung wählen:", exercises)

        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Maximalgewicht über Zeit")
            progress_data = get_exercise_progress_data(selected)
            if progress_data is not None:
                st.line_chart(progress_data)
        with col_b:
            st.caption("Trainingsvolumen über Zeit")
            volume_data = get_volume_chart_data(selected)
            if volume_data is not None:
                st.bar_chart(volume_data)
    else:
        st.info("Noch keine Workouts.")

# ---------- TAB 3: Ernährung ----------
with tab_nutrition:
    st.subheader("Heutige Mahlzeiten")
    foods_today = get_daily_nutrition_with_id(date.today())
    
    if foods_today:
        total_cal = sum(f[3] for f in foods_today)
        total_protein = sum(f[4] for f in foods_today)
        total_carbs = sum(f[5] for f in foods_today)
        total_fat = sum(f[6] for f in foods_today)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Kalorien", f"{round(total_cal)} kcal")
        m2.metric("Protein", f"{round(total_protein)}g")
        m3.metric("Carbs", f"{round(total_carbs)}g")
        m4.metric("Fett", f"{round(total_fat)}g")

        st.divider()
        
        st.caption("Alle Mahlzeiten heute — klicke zum Bearbeiten")

        for f in foods_today:
            entry_id, food_name, amount_g, calories, protein, carbs, fat, sugar = f
            
            with st.expander(f"🍽️ **{food_name}** ({amount_g}g) — {calories}kcal"):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    new_name = st.text_input("Lebensmittel", value=food_name, key=f"name_{entry_id}")
                with col_b:
                    new_amount = st.number_input("Menge (g)", value=float(amount_g), key=f"amount_{entry_id}")

                col_save, col_delete = st.columns(2)
                with col_save:
                    if st.button("💾 Speichern", key=f"save_{entry_id}", use_container_width=True):
                        options = search_food_options(new_name)
                        if not options:
                            st.error(f"'{new_name}' nicht in der Datenbank gefunden")
                        else:
                            chosen_name = options[0]["name"] if len(options) == 1 else choose_best_food(new_name, [o["name"] for o in options])
                            nutrition = get_nutrition_by_exact_name(chosen_name, new_amount)
                            if nutrition:
                                update_food_entry(entry_id, nutrition["name"], new_amount,
                                                nutrition["calories"], nutrition["protein_g"],
                                                nutrition["carbs_g"], nutrition["fat_g"], nutrition["sugar_g"])
                                st.success(f"Aktualisiert: {nutrition['name']}")
                                st.rerun()
                with col_delete:
                    if st.button("🗑️ Löschen", key=f"delete_{entry_id}", use_container_width=True):
                        delete_food_entry(entry_id)
                        st.rerun()
    else:
        st.info("Noch nichts heute gegessen. Sag es mir im Chat!")

    st.divider()

    use_custom_range = st.checkbox("Eigenen Zeitraum wählen")
    if use_custom_range:
        date_range = st.date_input(
            "Zeitraum",
            value=(date.today() - timedelta(days=6), date.today())
        )
        if len(date_range) == 2:
            range_start, range_end = date_range
        else:
            range_start, range_end = date.today() - timedelta(days=6), date.today()
    else:
        range_start, range_end = date.today() - timedelta(days=6), date.today()

    st.subheader(f"Übersicht ({range_start.strftime('%d.%m.')} – {range_end.strftime('%d.%m.')})")

    weekly_facts = get_weekly_nutrition_facts(range_start, range_end)
    if weekly_facts:
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Ø Kalorien/Tag", f"{weekly_facts['avg_calories']} kcal")
        w2.metric("Ø Protein/Tag", f"{weekly_facts['avg_protein_g']}g")
        w3.metric("Ø Carbs/Tag", f"{weekly_facts['avg_carbs_g']}g")
        w4.metric("Ø Fett/Tag", f"{weekly_facts['avg_fat_g']}g")
        st.caption(f"Basierend auf {weekly_facts['days_logged']} geloggten Tagen")
    else:
        st.info("Keine Daten für diesen Zeitraum.")