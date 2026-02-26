import streamlit as st
from openai import OpenAI
import random
import time
import json
import datetime

# [SECURITY] OpenAI API Key
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("🚨 Error: OPENAI_API_KEY not found in Secrets.")
    st.stop()

# [MODEL SETTING] - 2024-04-09 snapshot of gpt-4-turbo
client = OpenAI(api_key=api_key)
MODEL_VERSION = "gpt-4-turbo-2024-04-09"

st.set_page_config(page_title="Sci-Fi Brainstorming Pilot", page_icon="🧪", layout="wide")

# =========================================================
# [ANTI-SLEEP] Prevent app from sleeping (Heartbeat)
# =========================================================
st.components.v1.html(
    """
    <script>
    // Sends a signal to the server in the background every 5 minutes (300,000ms) to prevent connection loss.
    setInterval(function() {
        fetch(window.location.href, {cache: "no-store"});
    }, 300000);
    </script>
    """,
    height=0
)

# =========================================================
# [TIME MANAGEMENT] 
# =========================================================
def init_phase_timer():
    if "phase_start_time" not in st.session_state:
        st.session_state.phase_start_time = datetime.datetime.now()

def get_remaining_seconds(duration_minutes):
    if "phase_start_time" not in st.session_state:
        init_phase_timer()
    elapsed = (datetime.datetime.now() - st.session_state.phase_start_time).total_seconds()
    remaining = (duration_minutes * 60) - elapsed
    return max(0, int(remaining))

# [JAVASCRIPT TIMER] Banner Timer (Fixed UI clipping)
def show_timer(duration_minutes, message="Time Remaining"):
    remaining_sec = get_remaining_seconds(duration_minutes)
    
    timer_html = f"""
        <div style="
            background-color: #fff0f6; border: 2px solid #d63384; 
            padding: 15px; border-radius: 10px; 
            font-size: 1.5rem; font-weight: bold; color: #d63384; 
            text-align: center; font-family: sans-serif;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1); 
            margin: 5px; 
            box-sizing: border-box;">
            ⏳ {message}: <span id="time">Loading...</span>
        </div>
        <script>
        function startTimer(duration, display) {{
            var timer = duration, minutes, seconds;
            var interval = setInterval(function () {{
                minutes = parseInt(timer / 60, 10);
                seconds = parseInt(timer % 60, 10);

                minutes = minutes < 10 ? "0" + minutes : minutes;
                seconds = seconds < 10 ? "0" + seconds : seconds;

                display.textContent = minutes + ":" + seconds;

                if (--timer < 0) {{
                    clearInterval(interval);
                    display.textContent = "00:00 (Time's Up!)";
                }}
            }}, 1000);
        }}
        window.onload = function () {{
            var duration = {remaining_sec};
            var display = document.querySelector('#time');
            startTimer(duration, display);
        }};
        </script>
    """
    st.components.v1.html(timer_html, height=100)

# [CSS STYLING]
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; text-align: center; color: #1E1E1E; margin-bottom: 10px; }
    .phase-header { font-size: 1.5rem; font-weight: 600; color: #0068C9; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    .instruction-box { background-color: #f8f9fa; padding: 25px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px; line-height: 1.6; }
    .stTextArea textarea { font-size: 1.1rem !important; line-height: 1.6 !important; font-family: 'Arial', sans-serif !important; height: 500px !important; }
    </style>
""", unsafe_allow_html=True)

# [SESSION STATE INITIALIZATION]
if "participant_id" not in st.session_state: st.session_state.participant_id = None
if "assigned_group" not in st.session_state: st.session_state.assigned_group = None
if "current_phase" not in st.session_state: st.session_state.current_phase = "Login"
if "messages" not in st.session_state: st.session_state.messages = []
# (Pilot) story_content는 쓰지 않지만 에러 방지용으로 남겨둡니다.
if "story_content" not in st.session_state: st.session_state.story_content = ""

# =========================================================
# [CONTENT SETTINGS] - System Prompts & Images
# =========================================================

# 1. Strategic AI Prompt (Discourse Engineering)
SYS_PROMPT_STRATEGIC = """
You are a Generative AI (GenAI) partner for a creative writing brainstorming session. Today, the user will be preparing to write a short Science-Fiction story. Before they write, you will brainstorm ideas for the story with the user for 10 minutes. Your goal is to work with the user to develop ideas for the story’s characters, settings, and plotline with a clear beginning, middle, and end. 

You must strictly follow the “Discourse Engineering” guidelines below to effectively and efficiently collaborate with the user. 

What is Discourse Engineering? 

Discourse engineering is your guide for structuring your chats so that you can tackle a big creative agenda, like building a great story, together, step by step. Instead of just answering a simple prompt, you must help the user move their ideas from a simple concept to a richer, more thoughtful narrative via discourse. You do this by working through three key stages: Construction, Co-construction, and Conflict. 

How to apply Discourse Engineering (Your Instructions): 

1. Construction 
This initial step involves exploring and developing early ideas. You must use thoughtful questions to help the user move beyond surface-level thinking. 

Action: When the user shares initial ideas, thoughts, characters, or settings, do not just accept them. 
Action: Ask more questions that help you and the user elaborate on each other’s information and ideas. 
Action: Listen carefully to the user's suggestions and let them spark new ideas in your responses. 
Action: If something is unclear in the interaction, ask clarifying questions to the user. 

2. Co-construction 
This phase follows the construction step; you and the user must build on each other’s ideas through ongoing conversation, making the story richer. 

Action: Combine the user's suggestions with your own imagination. 
Action: Talk through ideas together, letting the story grow and change (aim for shared conclusions from the discussion). 
Action: If there are differences of opinions, handle them by addressing them directly. 
Action: Use feedback to refine ideas collaboratively. 

3. Conflict 
This phase helps to find the blind spot of the idea and improve creative concepts and the story. 

Action: Review the story’s main ideas and ensure co-construction ideas are aligned. 
Action: Question the user's assumptions and engage in critical dialogue to validate the ideas and approaches. (Do not just agree with everything). 
Action: Work with the user to build a common understanding of the story and the best methods for tackling the creative process. 
"""

# 2. Baseline AI Prompt (Non-Discourse / Control) - [empty]
SYS_PROMPT_BASELINE = ""

# 3. Guideline Images (Filename Check Required!)
IMAGES_EXP = ["Discourse_page1.png", "Discourse_page2.png", "Discourse_page3.png"]
IMAGES_CTRL = ["Discourse_absent_page1.png"] 

# [GROUP DEFINITION] 
GROUPS = {
    "G1": {"type": "Instructed_Strategic", "guide": IMAGES_EXP,  "sys_prompt": SYS_PROMPT_STRATEGIC},
    "G2": {"type": "Instructed_Baseline",  "guide": IMAGES_EXP,  "sys_prompt": SYS_PROMPT_BASELINE},
    "G3": {"type": "Neutral_Strategic",    "guide": IMAGES_CTRL, "sys_prompt": SYS_PROMPT_STRATEGIC},
    "G4": {"type": "Neutral_Baseline",     "guide": IMAGES_CTRL, "sys_prompt": SYS_PROMPT_BASELINE},
}

# =========================================================
# [SIDEBAR] ADMIN PANEL (Researcher Only)
# =========================================================
with st.sidebar:
    st.title("🛡️ Researcher Admin")
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_pass == "1357":
        st.success("Unlocked")
        
        st.markdown("---")
        st.markdown("### 📊 Status Monitor")
        if st.session_state.participant_id:
            st.write(f"**ID:** {st.session_state.participant_id}")
            grp = st.session_state.assigned_group
            st.write(f"**Group:** {grp} ({GROUPS[grp]['type']})")
            st.write(f"**Phase:** {st.session_state.current_phase}")
            
            if st.button("Reset Timer"):
                if "phase_start_time" in st.session_state:
                    del st.session_state.phase_start_time
                st.rerun()
        else:
            st.warning("No participant logged in.")

        st.markdown("---")
        st.markdown("### 🕹️ Controls")
        
        # delete writing phase 
        phase_options = ["Login", "Phase 0: Instruction", "Phase 1: Brainstorming", "Submission"]
        try: idx = phase_options.index(st.session_state.current_phase)
        except: idx = 0
        new_phase = st.selectbox("Force Phase Jump:", phase_options, index=idx)
        if st.button("Go to Phase"):
            st.session_state.current_phase = new_phase
            if "phase_start_time" in st
