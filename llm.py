"""
LLM Integration Module for the AI-Powered Student Query Assistant.

Wraps the Gemini API for text generation and audio transcription.
Implements robust exception handling for API failures, quota limits,
and network disconnects.
"""

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError
from config import GEMINI_API_KEY, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_OUTPUT_TOKENS, TRACK_PROMPTS, GENERAL_SYSTEM_PROMPT
from logger import logger

def configure_gemini(api_key: str = None):
    """
    Configures the google-generativeai library with the provided API key.
    Falls back to the config or environment variable.
    """
    key = api_key or GEMINI_API_KEY
    if not key:
        logger.error("Gemini API configuration failed: No API key provided.")
        raise ValueError("Gemini API Key is missing. Please configure it in your settings.")
    
    try:
        genai.configure(api_key=key)
        logger.info("Gemini API configured successfully.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        raise

def generate_response(
    query: str,
    track: str,
    chat_history: list[dict],
    api_key: str = None,
    model_name: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE
) -> str:
    """
    Generates a response from the Gemini model given the query, track, and session history.
    
    Args:
        query: The user's query text.
        track: The student track (Programming, AI/ML, etc.)
        chat_history: A list of dicts: [{"role": "user"|"assistant", "content": "..."}]
        api_key: Optional API key override.
        model_name: Optional model override.
        temperature: Optional temperature override.
        
    Returns:
        The generated response string.
    """
    if not query.strip():
        return "I cannot generate a response for an empty query. Please enter a valid question!"
        
    # Configure the client
    configure_gemini(api_key)
    
    # Select the system prompt based on track
    system_prompt = TRACK_PROMPTS.get(track, GENERAL_SYSTEM_PROMPT)
    
    try:
        # Define model with system instructions
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
            }
        )
        
        # Convert chat history to format expected by Gemini API:
        # role: 'user' -> 'user', 'assistant' -> 'model'
        # content -> 'parts' (must be list of parts, e.g. ["string"])
        gemini_history = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({
                "role": role,
                "parts": [msg["content"]]
            })
            
        # Start a multi-turn chat session with the historical context
        chat = model.start_chat(history=gemini_history)
        
        # Log the outgoing request
        logger.info(f"Sending prompt to model {model_name} for track '{track}'")
        
        # Generate the next response
        response = chat.send_message(query)
        
        if not response.text:
            logger.warning("Empty response received from Gemini API.")
            return "I received an empty response from the assistant. Please try rephrasing your question."
            
        logger.info("Response generated successfully.")
        return response.text
        
    except GoogleAPIError as e:
        logger.error(f"Gemini API Error during generation: {e}")
        return f"⚠️ **Gemini API Error:** We encountered an issue contacting the AI models. Details: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in generate_response: {e}")
        return f"⚠️ **Application Error:** An unexpected error occurred: {str(e)}"

def transcribe_audio(audio_bytes: bytes, api_key: str = None) -> str:
    """
    Transcribes raw audio bytes (WebM/WAV) into text using Gemini 2.5 Flash's
    multimodal audio capabilities.
    
    Args:
        audio_bytes: The raw audio data.
        api_key: Optional API key override.
        
    Returns:
        The transcribed text.
    """
    if not audio_bytes:
        logger.warning("Transcription called with empty audio bytes.")
        raise ValueError("Audio data is empty.")
        
    # Configure client
    configure_gemini(api_key)
    
    try:
        # Use gemini-2.5-flash as requested and configure it for transcription
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Prepare the audio block structure using webm MIME type (default for browsers)
        audio_part = {
            "mime_type": "audio/webm",
            "data": audio_bytes
        }
        
        prompt = (
            "You are an expert speech-to-text transcriber. Transcribe the provided audio data into text. "
            "Only return the transcribed words exactly as they are spoken. "
            "Do not add any greetings, commentary, punctuation analysis, or other conversational text. "
            "If the audio is silent or contains no recognizable speech, return an empty string."
        )
        
        logger.info("Sending audio recording to Gemini for transcription...")
        response = model.generate_content([prompt, audio_part])
        
        transcription = response.text.strip()
        logger.info(f"Audio transcription complete. Result: '{transcription[:50]}...'")
        return transcription
        
    except GoogleAPIError as e:
        logger.error(f"Gemini API Error during audio transcription: {e}")
        raise RuntimeError(f"Failed to transcribe audio via Gemini API: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {e}")
        raise RuntimeError(f"An error occurred while transcribing your voice: {str(e)}")
