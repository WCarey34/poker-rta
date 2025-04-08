import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from core.odds_calculator import calculate_equity_vs_random
from core.action_suggester import suggest_action, suggest_push_fold
from core.player_tracker import (
    init_db, log_action, get_player_stats, get_all_player_stats,
    save_note, get_note, start_new_session, get_latest_session_id,
    get_current_session_summary, get_all_session_ids, get_session_actions
)
from ocr.reader import extract_cards_from_image
import io
import csv

# Initialize DB
init_db()

st.title("🃏 Poker RTA - Full HUD + OCR")

# ----- SESSION INFO -----
st.header("🎯 Current Session")

col1, col2 = st.columns([2, 1])
with col1:
    summary = get_current_session_summary()
    if summary:
        st.markdown(f"""
        **Session ID:** `{summary['session_id']}`  
        **Hands Logged:** `{summary['hands_logged']}`  
        **VPIP Avg:** `{summary['vpip_avg']}%`  
        **PFR Avg:** `{summary['pfr_avg']}%`  
        **Unique Players:** `{summary['unique_players']}`
        """)
    else:
        st.info("No session started yet.")

with col2:
    if st.button("➕ Start New Session"):
        sid = start_new_session()
        st.success(f"New session #{sid} started!")

# ----- OCR IMAGE UPLOAD -----
st.header("🧠 Auto-Fill Cards from Image (OCR)")

uploaded_file = st.file_uploader("Upload image (screenshot of cards)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    temp_image_path = "data/temp_uploaded.png"
    with open(temp_image_path, "wb") as f:
        f.write(uploaded_file.read())

    detected_cards = extract_cards_from_image(temp_image_path)

    st.image(temp_image_path, caption="Uploaded Image", use_column_width=True)
    st.write("🃏 Detected Cards:", detected_cards)

    if len(detected_cards) == 2:
        st.session_state['hole_input'] = " ".join(detected_cards)
    elif len(detected_cards) == 5:
        st.session_state['board_input'] = " ".join(detected_cards)
    elif len(detected_cards) == 7:
        st.session_state['hole_input'] = " ".join(detected_cards[:2])
        st.session_state['board_input'] = " ".join(detected_cards[2:])

# ----- EQUITY CALCULATOR -----
st.header("📈 Hand Equity Calculator")

hole_input = st.text_input("Your hole cards (e.g. Ah Kh):", value=st.session_state.get("hole_input", ""))
board_input = st.text_input("Board cards (e.g. 2c 7d Jc):", value=st.session_state.get("board_input", ""))
num_opponents = st.slider("Number of opponents", 1, 8, 1)

position = st.selectbox("Your position", ["BTN", "SB", "BB"])
stack_size = st.slider("Stack size (BB)", 1, 20, 10)
hand_input = st.text_input("Your hand for chart lookup (e.g. AJo, KTs):")

if st.button("💡 Calculate Recommendations"):
    try:
        hole = hole_input.strip().split()
        board = board_input.strip().split()
        equity = calculate_equity_vs_random(hole, board, num_opponents)
        action = suggest_action(equity)
        chart_suggestion = suggest_push_fold(position, stack_size, hand_input)

        st.success(f"Equity vs {num_opponents} players: **{equity:.2%}**")
        st.info(f"Equity-Based Suggestion: **{action}**")
        st.warning(f"Push/Fold Chart Suggestion: **{chart_suggestion}**")
    except Exception as e:
        st.error(f"Error: {e}")

# ----- ACTION LOGGER -----
st.header("📋 Log Player Action")

with st.form("log_form"):
    col1, col2 = st.columns(2)
    player_name = col1.text_input("Player name")
    player_position = col1.selectbox("Position", ["UTG", "MP", "CO", "BTN", "SB", "BB"])
    player_action = col2.selectbox("Action", ["Fold", "Call", "Raise"])
    player_stack = col2.number_input("Stack size (BB)", min_value=1, step=1)

    submitted = st.form_submit_button("Log Action")
    if submitted and player_name:
        log_action(player_name, player_position, player_action, player_stack)
        st.success(f"Logged {player_action} for {player_name} in position {player_position}")

# ----- PLAYER STATS -----
st.header("📊 Player Stats")

selected_player = st.text_input("View stats for player:")
if selected_player:
    stats = get_player_stats(selected_player)
    note_data = get_note(selected_player)

    st.write(f"**Hands Tracked:** {stats['hands_logged']}")
    st.write(f"**VPIP:** {stats['VPIP']}%")
    st.write(f"**PFR:** {stats['PFR']}%")
    st.write(f"**Type:** {stats['type']}")
    st.write(f"**Tag:** {note_data.get('tag', '')}")
    st.write(f"**Note:** {note_data.get('note', '')}")

# ----- PLAYER NOTES -----
st.header("📝 Player Notes & Tags")

with st.form("note_form"):
    note_player = st.text_input("Select player to note:")
    current_note_data = get_note(note_player) if note_player else {"note": "", "tag": ""}
    
    note_text = st.text_area("Notes", value=current_note_data["note"])
    tag = st.selectbox("Behavior tag", ["", "Loose Passive", "Trappy", "Aggro Donk", "Bluffy", "Tight AF"], index=0)

    save_btn = st.form_submit_button("💾 Save Note")
    if save_btn and note_player:
        save_note(note_player, note_text, tag)
        st.success(f"Note saved for {note_player}")

# ----- HUD OVERVIEW -----
st.header("📋 All Tracked Players")

player_data = get_all_player_stats()

def get_badge(player_type):
    badge_map = {
        "TAG": "🟢 **TAG**",
        "LAG": "🟡 **LAG**",
        "NIT": "🔵 **NIT**",
        "Maniac": "🔴 **Maniac**",
        "Unknown": "⚪ Unknown"
    }
    return badge_map.get(player_type, "⚪ Unknown")

if player_data:
    st.markdown("### Player Overview")

    table = "| Player | VPIP | PFR | Hands | Type | Tag | Note |\n"
    table += "|--------|------|-----|--------|------|-----|------|\n"
    for player in sorted(player_data, key=lambda x: x["VPIP"], reverse=True):
        table += f"| {player['player_name']} | {player['VPIP']}% | {player['PFR']}% | {player['hands_logged']} | {get_badge(player['type'])} | {player.get('tag', '')} | {player.get('note', '')} |\n"

    st.markdown(table)

    st.subheader("🔍 VPIP vs PFR Chart")
    df = pd.DataFrame(player_data)
    st.bar_chart(df.set_index("player_name")[["VPIP", "PFR"]])
else:
    st.info("No players tracked yet.")

# ----- EXPORT SESSION -----
st.header("📤 Export Session Log")

session_ids = get_all_session_ids()

if session_ids:
    selected_session_id = st.selectbox("Select session to export", session_ids)

    if st.button("📁 Export as CSV"):
        actions = get_session_actions(selected_session_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Player", "Position", "Action", "Stack"])
        writer.writerows(actions)

        st.download_button(
            label="📥 Download CSV",
            data=output.getvalue(),
            file_name=f"session_{selected_session_id}.csv",
            mime="text/csv"
        )
else:
    st.info("No sessions available to export.")
