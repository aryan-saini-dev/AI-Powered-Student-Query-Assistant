"""
Database Module for the AI-Powered Student Query Assistant.

Handles SQLite database operations including:
- User registration and authenticated logins with PBKDF2 hashing.
- Query response caching to minimize duplicate API calls and lower latency.
- Event logging for conversation history tracking.
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime
from config import DB_PATH
from logger import logger

def get_connection():
    """Establishes and returns a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database at {DB_PATH}: {e}")
        raise

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Create Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Create Response Cache Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                track TEXT NOT NULL,
                response_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Create Conversation Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                track TEXT NOT NULL,
                user_query TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

# --- PASSWORD HASHING UTILITIES ---

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2 HMAC SHA-256.
    If salt is not provided, a random 16-byte salt is generated.
    Returns (hex_hash, hex_salt).
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    # 100,000 iterations is a reasonable standard for desktop/small server apps
    iterations = 100000
    pwd_bytes = password.encode('utf-8')
    
    dk = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt, iterations)
    return dk.hex(), salt.hex()

# --- USER AUTHENTICATION ACTIONS ---

def register_user(username: str, password: str) -> bool:
    """
    Registers a new user in the database.
    Returns True if successful, False if the username already exists or on error.
    """
    username = username.strip().lower()
    if not username or not password:
        logger.warning("Signup attempt with empty username or password.")
        return False
        
    password_hash, salt = hash_password(password)
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt)
        )
        conn.commit()
        logger.info(f"User '{username}' registered successfully.")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Registration failed: Username '{username}' already exists.")
        return False
    except sqlite3.Error as e:
        logger.error(f"Error during registration of user '{username}': {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_user(username: str, password: str) -> bool:
    """
    Verifies a user's login credentials.
    Returns True if valid, False otherwise.
    """
    username = username.strip().lower()
    if not username or not password:
        return False
        
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            logger.info(f"Login failed: Username '{username}' not found.")
            return False
            
        stored_hash, stored_salt_hex = row
        salt = bytes.fromhex(stored_salt_hex)
        
        # Hash the incoming password with the retrieved salt
        computed_hash, _ = hash_password(password, salt)
        
        if secrets.compare_digest(stored_hash, computed_hash):
            logger.info(f"User '{username}' logged in successfully.")
            return True
        else:
            logger.info(f"Login failed: Incorrect password for user '{username}'.")
            return False
            
    except sqlite3.Error as e:
        logger.error(f"Error verifying user '{username}': {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- RESPONSE CACHING ACTIONS ---

def _get_query_key(query_text: str, track: str) -> str:
    """Helper to generate a unique query key using SHA-256."""
    normalized = f"{track.lower().strip()}:{query_text.lower().strip()}"
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def get_cached_response(query_text: str, track: str) -> str | None:
    """
    Retrieves a cached response for the specific query and track.
    Returns the response text if a match is found, otherwise None.
    """
    query_hash = _get_query_key(query_text, track)
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT response_text FROM response_cache WHERE query_hash = ?",
            (query_hash,)
        )
        row = cursor.fetchone()
        if row:
            logger.info(f"Cache HIT for query: '{query_text[:30]}...' in track '{track}'")
            return row[0]
        logger.info(f"Cache MISS for query: '{query_text[:30]}...' in track '{track}'")
        return None
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch from cache: {e}")
        return None
    finally:
        if conn:
            conn.close()

def cache_response(query_text: str, track: str, response_text: str) -> bool:
    """
    Saves a query and its response to the cache.
    Returns True if successful, False otherwise.
    """
    if not query_text.strip() or not response_text.strip():
        return False
        
    query_hash = _get_query_key(query_text, track)
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO response_cache (query_hash, query_text, track, response_text, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (query_hash, query_text.strip(), track.strip(), response_text.strip(), datetime.now())
        )
        conn.commit()
        logger.info(f"Successfully cached response for query hash '{query_hash[:8]}'.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to save query to cache: {e}")
        return False
    finally:
        if conn:
            conn.close()

def clear_cache() -> bool:
    """Clears all entries in the response cache table."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM response_cache")
        conn.commit()
        logger.info("Response cache cleared successfully.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to clear response cache: {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- CONVERSATION LOGS ACTIONS ---

def log_conversation(username: str, track: str, user_query: str, bot_response: str) -> bool:
    """
    Logs a single query-response event for a user.
    Returns True if successful, False otherwise.
    """
    username = username.strip().lower()
    if not username:
        return False
        
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO conversation_logs (username, track, user_query, bot_response, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (username, track, user_query, bot_response, datetime.now())
        )
        conn.commit()
        logger.info(f"Logged conversation details for user '{username}'.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to log conversation details for user '{username}': {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_conversation_history(username: str, limit: int = 50) -> list[dict]:
    """
    Retrieves conversation logs for a specific user.
    Returns a list of dictionaries with keys: id, timestamp, track, query, response.
    """
    username = username.strip().lower()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, timestamp, track, user_query, bot_response
               FROM conversation_logs
               WHERE username = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (username, limit)
        )
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "timestamp": row[1],
                "track": row[2],
                "query": row[3],
                "response": row[4]
            })
        return history
    except sqlite3.Error as e:
        logger.error(f"Failed to retrieve conversation history for user '{username}': {e}")
        return []
    finally:
        if conn:
            conn.close()

def clear_user_history(username: str) -> bool:
    """Clears conversation logs for a specific user."""
    username = username.strip().lower()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation_logs WHERE username = ?", (username,))
        conn.commit()
        logger.info(f"Cleared conversation history for user '{username}'.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to clear conversation history for user '{username}': {e}")
        return False
    finally:
        if conn:
            conn.close()

# Initialize database on import to ensure tables exist
init_db()
