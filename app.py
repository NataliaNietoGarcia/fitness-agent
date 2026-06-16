import streamlit as st
from agent import chat
from database.db import create_tables, get_user_profile
from tools.charts import (get_weight_chart_data, get_exercise_progress_data,
                          get_volume_chart_data, get_all_exercises)

st.set_page_config(page_title="Fitness Agent", page_icon="🏋️", layout="wide")
create_tables()

# ============ SIDEBAR: Charts ============
with st.sidebar:
    st.header("📊 Deine Fortschritte")

    # Weight chart
    st.subheader("⚖️ Gewichtsverlauf")
    weight_data = get_weight_chart_data()
    if weight_data is not None:
        st.line_chart(weight_data)
    else:
        st.info("Noch keine Gewichtsdaten.")

    # Exercise selector
    exercises = get_all_exercises()
    if exercises:
        st.subheader("💪 Übungs-Progression")
        selected = st.selectbox("Übung wählen:", exercises)

        # Progression (max weight)
        progress_data = get_exercise_progress_data(selected)
        if progress_data is not None:
            st.caption("Maximalgewicht über Zeit")
            st.line_chart(progress_data)

        # Volume
        volume_data = get_volume_chart_data(selected)
        if volume_data is not None:
            st.caption("Trainingsvolumen über Zeit")
            st.bar_chart(volume_data)
    else:
        st.info("Noch keine Workouts.")

# ============ MAIN: Chat ============
st.title("🏋️ Fitness Agent")
st.caption("Dein persönlicher KI-Fitness-Coach")

if "messages" not in st.session_state:
    st.session_state.messages = []
    profil = get_user_profile()
    if profil:
        welcome = f"👋 Willkommen zurück, {profil[1]}! Wie kann ich dir heute helfen?"
    else:
        welcome = "👋 Willkommen! Erstelle zuerst dein Profil."
    st.session_state.messages.append({"role": "assistant", "content": welcome})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Schreibe eine Nachricht..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Denke nach..."):
            response = chat(user_input)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    # Refresh charts after new data
    st.rerun()