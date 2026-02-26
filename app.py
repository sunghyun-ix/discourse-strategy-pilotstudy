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
    </style>
""", unsafe_allow_html=True)

# [SESSION STATE INITIALIZATION]
if "participant_id" not in st.session_state: st.session_state.participant_id = None
if "assigned_group" not in st.session_state: st.session_state.assigned_group = None
if "current_phase" not in st.session_state: st.session_state.current_phase = "Login"
if "messages" not in st.session_state: st.session_state.messages = []

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

# 2. Baseline AI Prompt (Non-Discourse / Control)
SYS_PROMPT_BASELINE = ""

# 3. Guideline Images (Pilot Version - All participants read guidelines)
IMAGES_EXP = ["Discourse_page1.png", "Discourse_page2.png", "Discourse_page3.png"]

# [GROUP DEFINITION - PILOT VERSION] 
# G1: AI uses Strategy | G2: AI does NOT use Strategy (Control) | G3: Extra Control slot if needed
GROUPS = {
    "G1": {"type": "Human_Trained_&_AI_Trained",     "guide": IMAGES_EXP, "sys_prompt": SYS_PROMPT_STRATEGIC},
    "G2": {"type": "Human_Trained_&_AI_NOT_Trained", "guide": IMAGES_EXP, "sys_prompt": SYS_PROMPT_BASELINE},
    "G3": {"type": "Human_Trained_&_AI_Control",     "guide": IMAGES_EXP, "sys_prompt": SYS_PROMPT_BASELINE},
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
        
        # Writing phase removed for Pilot
        phase_options = ["Login", "Phase 0: Instruction", "Phase 1: Brainstorming", "Submission"]
        try: idx = phase_options.index(st.session_state.current_phase)
        except: idx = 0
        new_phase = st.selectbox("Force Phase Jump:", phase_options, index=idx)
        if st.button("Go to Phase"):
            st.session_state.current_phase = new_phase
            if "phase_start_time" in st.session_state:
                del st.session_state.phase_start_time
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 💾 Data Management")
        
        if st.session_state.participant_id:
            log_data = {
                "participant_id": st.session_state.participant_id,
                "assigned_group": st.session_state.assigned_group,
                "condition_detail": GROUPS[st.session_state.assigned_group]['type'],
                "chat_history": st.session_state.messages
            }
            json_str = json.dumps(log_data, indent=2, ensure_ascii=False)
            file_name = f"PILOT_LOG_{st.session_state.participant_id}_{st.session_state.assigned_group}.json"
            
            st.download_button(
                label="📥 Download Log JSON",
                data=json_str,
                file_name=file_name,
                mime="application/json",
                type="primary"
            )

        st.markdown("---")
        if st.button("⚠️ RESET FOR NEXT PARTICIPANT", type="primary"):
            st.session_state.clear()
            st.rerun()

# =========================================================
# [MAIN FLOW]
# =========================================================

# --- AUTO LOGIN CHECK (URL PARAMETER) ---
query_params = st.query_params
if "PID" in query_params and st.session_state.participant_id is None:
    p_id_from_url = query_params["PID"]
    st.session_state.participant_id = p_id_from_url
    st.session_state.assigned_group = random.choice(list(GROUPS.keys()))
    st.session_state.current_phase = "Phase 0: Instruction"
    
    if "phase_start_time" in st.session_state: del st.session_state.phase_start_time
    st.rerun()

# --- STEP 1: LOGIN ---
if st.session_state.current_phase == "Login":
    st.markdown("<div class='main-title'>🧪 Sci-Fi Brainstorming Pilot</div>", unsafe_allow_html=True)
    st.info("Waiting for Qualtrics redirection...")
    st.caption("(If you are testing manually, enter ID below)")
    
    with st.form("login_form"):
        p_id = st.text_input("Participant ID (e.g., P01):")
        submitted = st.form_submit_button("Start Experiment")
        
        if submitted and p_id:
            st.session_state.participant_id = p_id
            st.session_state.assigned_group = random.choice(list(GROUPS.keys()))
            st.session_state.current_phase = "Phase 0: Instruction"
            if "phase_start_time" in st.session_state: del st.session_state.phase_start_time
            st.rerun()

# --- STEP 2: INSTRUCTION ---
elif st.session_state.current_phase == "Phase 0: Instruction":
    init_phase_timer()
    show_timer(5, "Reading Time")
    
    st.markdown(f"<div class='phase-header'>Step 1: Guidelines (5 min)</div>", unsafe_allow_html=True)
    
    group_settings = GROUPS[st.session_state.assigned_group]
    
    try:
        images_to_show = group_settings['guide']
        if isinstance(images_to_show, list):
            for img_file in images_to_show:
                st.image(img_file, use_column_width=True)
        else:
            st.image(images_to_show, use_column_width=True)
    except Exception as e:
        st.error(f"🚨 Image load error: {e}")
    
    st.write("")
    st.info("Please read the instructions carefully. Click below when ready.")
    
    if st.button("Start Brainstorming (Go to Step 2) 👉"):
        st.session_state.current_phase = "Phase 1: Brainstorming"
        if "phase_start_time" in st.session_state: del st.session_state.phase_start_time
        st.rerun()

# --- STEP 3: BRAINSTORMING (10 Min) - DUAL SCREEN ---
elif st.session_state.current_phase == "Phase 1: Brainstorming":
    init_phase_timer()
    DURATION_MIN = 10 
    show_timer(DURATION_MIN, "Brainstorming")
    
    st.markdown(f"<div class='phase-header'>Step 2: Brainstorming with AI ({DURATION_MIN} min)</div>", unsafe_allow_html=True)
    
    group_settings = GROUPS[st.session_state.assigned_group]
    
    # [DUAL SCREEN LAYOUT] Left: Chat (1.2) | Right: Guidelines (1)
    col_chat, col_guide = st.columns([1.2, 1], gap="large")
    
    with col_chat:
        st.info("💬 Chat with AI")
        chat_container = st.container(height=600)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
    with col_guide:
        st.success("📖 Guidelines Reference")
        guide_container = st.container(height=600)
        with guide_container:
            try:
                images_to_show = group_settings['guide']
                for img_file in images_to_show:
                    st.image(img_file, use_column_width=True)
            except Exception as e:
                st.error(f"🚨 Image load error: {e}")

    # Chat Input Box
    if prompt := st.chat_input("Brainstorm ideas here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"): 
                st.markdown(prompt)

            messages_payload = [{"role": "system", "content": group_settings["sys_prompt"]}] + st.session_state.messages
            
            with st.chat_message("assistant"):
                with st.spinner("AI is thinking..."):
                    try:
                        response = client.chat.completions.create(
                            model=MODEL_VERSION,
                            messages=messages_payload,
                            temperature=0.7,
                            max_tokens=400
                        )
                        ai_msg = response.choices[0].message.content
                        st.markdown(ai_msg)
                        st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                    except Exception as e:
                        st.error(f"API Error: {e}")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col3:
        # qualtrics submit
        if st.button("Finish Brainstorming & Go to Survey 👉", type="primary", use_container_width=True):
            st.session_state.current_phase = "Submission"
            if "phase_start_time" in st.session_state: del st.session_state.phase_start_time
            st.rerun()

# --- STEP 4: SUBMISSION (Direct redirect to Qualtrics) ---
elif st.session_state.current_phase == "Submission":
    st.markdown("<div class='main-title'>🎉 Brainstorming Completed!</div>", unsafe_allow_html=True)
    st.success("Your brainstorming session has been recorded.")
    
    # pilot link 
    qualtrics_base_url = "https://iu.co1.qualtrics.com/jfe/form/SV_72tlOVEzYQ16Swu"
    final_link = f"{qualtrics_base_url}?PID={st.session_state.participant_id}&GROUP={st.session_state.assigned_group}"
    
    st.markdown(f"""
        <div style="background-color:#e8f4fd; padding:30px; border-radius:10px; text-align:center; margin-top:20px;">
            <h3>👇 Final Step</h3>
            <p style="font-size:1.1rem;">Please click the link below to complete the measurement survey.</p>
            <br>
            <a href="{final_link}" target="_blank" style="
                background-color: #0068C9; color: white; padding: 18px 30px; 
                text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 1.3rem; 
                box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
                Go to Post-Survey 🔗
            </a>
            <br><br>
        </div>
    """, unsafe_allow_html=True)
    
    st.warning("Please notify the researcher that you have finished.")
