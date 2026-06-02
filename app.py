"""
Streamlit Application for the AI-Powered Student Query Assistant.

Provides a polished, responsive web interface including:
- Dynamic styling (dark glassmorphism theme)
- Basic user authentication (login/sign-up forms)
- Multi-turn conversation tracking across 4 tracks (Programming, AI/ML, Career, Interview Prep)
- Mic recorder for voice inputs transcribed via Gemini
- Sidebar controls for models, API keys, cache settings, and log history
"""

import os
import hashlib
import streamlit as st
from streamlit_mic_recorder import mic_recorder

import config
import database
import llm
from logger import logger

# 1. Page Configuration & Aesthetic CSS Injection
st.set_page_config(
    page_title="AI Student Query Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS (Glassmorphism & SLEEK Dark Palette)
# Configures rounded cards, smooth gradients, typography, and hover animations
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif;
        background-color: #0c0d14;
        color: #e2e8f0;
    }
    
    /* Main Layout */
    .stApp {
        background-image: radial-gradient(circle at 10% 20%, rgba(90, 75, 218, 0.15) 0%, transparent 40%),
                          radial-gradient(circle at 90% 80%, rgba(0, 206, 201, 0.12) 0%, transparent 40%);
        background-attachment: fixed;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a55eea, #45aaf2, #00d2d3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: left;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    
    /* Sleek Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(165, 94, 234, 0.4);
        transform: translateY(-2px);
    }
    
    /* Buttons styling */
    .stButton>button {
        background: linear-gradient(135deg, #8c4ff2 0%, #5d2de2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(140, 79, 242, 0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #a06fff 0%, #764beb 100%);
        box-shadow: 0 6px 20px rgba(140, 79, 242, 0.5);
        transform: translateY(-1px);
        border: none;
        color: white;
    }
    
    /* Secondary and logout buttons */
    .stButton.logout-btn>button {
        background: transparent !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        box-shadow: none !important;
    }
    .stButton.logout-btn>button:hover {
        background: rgba(239, 68, 68, 0.1) !important;
        border-color: #ef4444 !important;
    }
    
    /* Custom tags for tracks */
    .track-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border: 1px solid transparent;
    }
    .track-Programming {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border-color: rgba(59, 130, 246, 0.3);
    }
    .track-AI {
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        border-color: rgba(168, 85, 247, 0.3);
    }
    .track-Career {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border-color: rgba(34, 197, 94, 0.3);
    }
    .track-Interview {
        background: rgba(249, 115, 22, 0.15);
        color: #fb923c;
        border-color: rgba(249, 115, 22, 0.3);
    }
    
    /* Styled Chat Area */
    .cache-notice {
        font-size: 0.8rem;
        color: #00cec9;
        margin-top: -10px;
        margin-bottom: 15px;
        font-style: italic;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    /* Fix Streamlit default layout spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Custom Sidebar design */
    section[data-testid="stSidebar"] {
        background-color: #0e0f17 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Voice input button container styling */
    .voice-box {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 10px;
        padding: 10px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        border: 1px dashed rgba(255, 255, 255, 0.1);
        margin-bottom: 1.5rem;
    }
    
    /* Logo styling */
    .logo-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 1.5rem;
    }
    .logo-text {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff;
        font-family: 'Space Grotesk', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "active_track" not in st.session_state:
    st.session_state.active_track = "Programming"

# Initialize conversation history dict per track
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {
        "Programming": [],
        "AI/ML": [],
        "Career Guidance": [],
        "Interview Preparation": []
    }

# Preferences
if "bypass_cache" not in st.session_state:
    st.session_state.bypass_cache = False
if "api_key_override" not in st.session_state:
    st.session_state.api_key_override = ""
if "model_selection" not in st.session_state:
    st.session_state.model_selection = config.DEFAULT_MODEL
if "temperature" not in st.session_state:
    st.session_state.temperature = config.DEFAULT_TEMPERATURE

# Log cache service status
logger.info("Streamlit application session state loaded.")

# --- NAVIGATION ROUTING ---

# Render Authentication flow if not logged in
if not st.session_state.authenticated:
    st.markdown(
        """
        <div style='text-align: center; padding-top: 3rem; margin-bottom: 2rem;'>
            <h1 style='font-size: 2.8rem; font-weight: 800; background: linear-gradient(135deg, #a55eea, #45aaf2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🎓 AI Student Query Assistant</h1>
            <p style='color: #94a3b8; font-size: 1.1rem; max-width: 600px; margin: 0.5rem auto 2rem auto;'>
                Access interactive coding support, machine learning tutorials, personalized career paths, and tailored interview prep.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Form layout
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        tab_login, tab_signup = st.tabs(["🔐 Sign In", "📝 Create Account"])
        
        with tab_login:
            st.markdown("<h3 style='margin-bottom: 1rem;'>Welcome Back</h3>", unsafe_allow_html=True)
            login_user = st.text_input("Username", key="login_username", placeholder="e.g., student123")
            login_pass = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")
            
            if st.button("Sign In", use_container_width=True):
                if not login_user or not login_pass:
                    st.warning("Please fill in all credentials.")
                else:
                    if database.verify_user(login_user, login_pass):
                        st.session_state.authenticated = True
                        st.session_state.username = login_user.lower().strip()
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")
                        
        with tab_signup:
            st.markdown("<h3 style='margin-bottom: 1rem;'>Register Student Profile</h3>", unsafe_allow_html=True)
            reg_user = st.text_input("Choose Username", key="reg_username", placeholder="e.g., student123")
            reg_pass = st.text_input("Choose Password", type="password", key="reg_password", placeholder="Min 6 characters")
            reg_pass_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm", placeholder="••••••••")
            
            if st.button("Create Account", use_container_width=True):
                reg_user_clean = reg_user.strip()
                if not reg_user_clean or not reg_pass:
                    st.warning("All fields are required.")
                elif len(reg_pass) < 6:
                    st.warning("Password should be at least 6 characters long.")
                elif reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match.")
                else:
                    if database.register_user(reg_user_clean, reg_pass):
                        st.success("Account created successfully! You can now log in from the Sign In tab.")
                    else:
                        st.error("Username is already taken or registration failed.")
                        
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# --- AUTHENTICATED PANEL ---

# Custom Track Class mappings for UI highlights
track_css_map = {
    "Programming": "track-Programming",
    "AI/ML": "track-AI",
    "Career Guidance": "track-Career",
    "Interview Preparation": "track-Interview"
}

# SIDEBAR: Preferences, configuration, and controls
with st.sidebar:
    st.markdown(
        """
        <div class='logo-container'>
            <span style='font-size: 2.2rem;'>🎓</span>
            <div class='logo-text'>STUDENT HUB</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(f"**Student Session:** `@{st.session_state.username}`")
    st.divider()
    
    st.markdown("### 🔑 API Key Status")
    if config.GEMINI_API_KEY:
        st.success("✅ API Key Loaded (.env)")
        api_key_override = st.text_input(
            "Override API Key (Optional)",
            type="password",
            value=st.session_state.api_key_override,
            help="Enter a key here to override the .env configuration."
        )
    else:
        st.warning("⚠️ API Key Missing")
        api_key_override = st.text_input(
            "Enter Gemini API Key",
            type="password",
            value=st.session_state.api_key_override,
            help="Enter your Gemini API key to activate the assistant."
        )
    if api_key_override != st.session_state.api_key_override:
        st.session_state.api_key_override = api_key_override
    
    st.divider()
    
    st.markdown("### 📂 Caching & Storage")
    
    # Cache toggles
    use_cache = st.toggle("Enable Response Caching", value=not st.session_state.bypass_cache, help="Caches identical questions locally to save rate limits and lower latency.")
    st.session_state.bypass_cache = not use_cache
    
    col_cache_clear, col_hist_clear = st.columns(2)
    with col_cache_clear:
        if st.button("Flush Cache", help="Clears global cached answers for all queries"):
            if database.clear_cache():
                st.success("Cache cleared!")
            else:
                st.error("Failed to clear.")
    with col_hist_clear:
        if st.button("Wipe Chat", help="Wipes the active track's session conversation history"):
            st.session_state.chat_histories[st.session_state.active_track] = []
            st.success("Chat wiped!")
            st.rerun()

    # Expand logs for administrative review
    with st.expander("👁️ View Conversation Logs"):
        logs = database.get_user_conversation_history(st.session_state.username, limit=10)
        if logs:
            for l in logs:
                st.markdown(f"**[{l['track']}]** *{l['timestamp']}*")
                st.markdown(f"**Q:** {l['query']}")
                st.markdown(f"**A:** {l['response'][:60]}...")
                st.divider()
            if st.button("Delete My Log History"):
                if database.clear_user_history(st.session_state.username):
                    st.success("Logs deleted!")
                    st.rerun()
        else:
            st.info("No conversation logs found.")
            
    st.divider()
    
    # Logout action
    st.markdown("<div class='logout-btn'>", unsafe_allow_html=True)
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.chat_histories = {
            "Programming": [],
            "AI/ML": [],
            "Career Guidance": [],
            "Interview Preparation": []
        }
        st.success("Logged out successfully.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# MAIN CONTENT AREA

# Title
st.markdown("<h1 class='main-title'>AI-Powered Student Query Assistant</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Select a track and post queries via text or audio. The assistant retains context for multi-turn chats.</div>", unsafe_allow_html=True)

# Select Track via Horizontal Radio Buttons
tracks = ["Programming", "AI/ML", "Career Guidance", "Interview Preparation"]
active_track = st.radio(
    "Choose Track Profile:",
    options=tracks,
    index=tracks.index(st.session_state.active_track),
    horizontal=True
)

# Update track selection in state
if active_track != st.session_state.active_track:
    st.session_state.active_track = active_track
    logger.info(f"Switched active track to: {active_track}")

# Dynamic Track Badge
css_class = track_css_map.get(active_track, "track-Programming")
st.markdown(f"<span class='track-tag {css_class}'>Focus: {active_track} Track</span>", unsafe_allow_html=True)

# Render Chat Messages for the Active Track
chat_history = st.session_state.chat_histories[active_track]

for message in chat_history:
    avatar = "🎓" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Voice Input Section - Overhauled to sit compactly above input
st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)
voice_cols = st.columns([1.5, 5])
with voice_cols[0]:
    audio = mic_recorder(
        start_prompt="🎙️ Speak Query",
        stop_prompt="🛑 Send Speech",
        key=f"voice_recorder_{active_track}"
    )
with voice_cols[1]:
    if audio and "bytes" in audio and audio["bytes"]:
        st.markdown(
            "<div style='margin-top: 6px; color: #00cec9; font-weight: 500; font-size: 0.95rem;'>🔊 Recording captured. Processing speech...</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='margin-top: 6px; color: #94a3b8; font-size: 0.9rem; font-style: italic;'>Click 'Speak Query' to ask using voice.</div>",
            unsafe_allow_html=True
        )

# Process Voice Input
voice_query_text = None
if audio and "bytes" in audio and audio["bytes"]:
    audio_bytes = audio["bytes"]
    
    # To prevent executing multiple times on hot reloads, check if this audio is already processed
    # We hash the audio bytes and compare with the last processed audio hash
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    
    if "last_processed_audio_hash" not in st.session_state or st.session_state.last_processed_audio_hash != audio_hash:
        st.session_state.last_processed_audio_hash = audio_hash
        
        with st.spinner("🎙️ Listening and transcribing your voice..."):
            try:
                # Use key overrides or main configuration
                resolved_key = st.session_state.api_key_override or config.GEMINI_API_KEY
                if not resolved_key:
                    st.error("Missing API Key. Please supply a valid Gemini API Key in the sidebar.")
                else:
                    transcription = llm.transcribe_audio(audio_bytes, resolved_key)
                    if transcription:
                        voice_query_text = transcription
                        st.info(f"🗣️ **Transcribed Voice Query:** \"{voice_query_text}\"")
                    else:
                        st.warning("No speech detected in your recording. Please try speaking louder.")
            except Exception as e:
                st.error(f"Voice Transcription Failed: {str(e)}")

# Get regular text input
user_query = st.chat_input(f"Send a query to the {active_track} assistant...")

# Determine final query (Voice overrides text if transcription just happened)
final_query = voice_query_text or user_query

# Execute query-response cycle
if final_query:
    final_query = final_query.strip()
    
    # 1. Show user message in chat
    with st.chat_message("user", avatar="🎓"):
        st.markdown(final_query)
        
    # Append to active history
    st.session_state.chat_histories[active_track].append({"role": "user", "content": final_query})
    
    # 2. Check Cache
    cached_res = None
    if not st.session_state.bypass_cache:
        cached_res = database.get_cached_response(final_query, active_track)
        
    response_text = ""
    is_cached_hit = False
    
    # 3. Generate response
    if cached_res:
        response_text = cached_res
        is_cached_hit = True
    else:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"Processing response for {active_track} track..."):
                resolved_key = st.session_state.api_key_override or config.GEMINI_API_KEY
                
                if not resolved_key:
                    response_text = "❌ **API Key Missing:** Please input a valid Gemini API Key in the sidebar settings."
                    st.markdown(response_text)
                else:
                    response_text = llm.generate_response(
                        query=final_query,
                        track=active_track,
                        chat_history=chat_history[:-1], # Pass up to current turn
                        api_key=resolved_key,
                        model_name=st.session_state.model_selection,
                        temperature=st.session_state.temperature
                    )
                    st.markdown(response_text)
                    
                    # Store response to cache if generation succeeded
                    if response_text and not response_text.startswith("⚠️"):
                        database.cache_response(final_query, active_track, response_text)

    # If it was a cache hit, output response with indicator
    if is_cached_hit:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(response_text)
            st.markdown(
                """
                <div class='cache-notice'>
                    <span>⚡ Served from local response cache. Saved API tokens.</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Append response to chat history
    st.session_state.chat_histories[active_track].append({"role": "assistant", "content": response_text})
    
    # 4. Log interaction in database
    database.log_conversation(
        username=st.session_state.username,
        track=active_track,
        user_query=final_query,
        bot_response=response_text
    )
    
    # Rerun to clear input widgets cleanly and render the chat bubble permanently
    st.rerun()
