"""
Verification script to test the backend components of the AI Student Query Assistant.

Tests database tables initialization, registration, verification, response caching,
and logger features.
"""

import os
import sys

# Ensure active directory is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logger import logger
import config
import database

def run_tests():
    logger.info("Starting verification tests for backend modules...")
    print("=== Verification Starting ===")
    
    # 1. Config Check
    print("1. Testing config values...")
    assert hasattr(config, "DB_PATH"), "config is missing DB_PATH"
    assert hasattr(config, "TRACK_PROMPTS"), "config is missing TRACK_PROMPTS"
    assert len(config.TRACK_PROMPTS) == 4, "config must contain 4 track prompts"
    print("   [PASSED] Config checks passed.")

    # 2. Database Schema Initialization Check
    print("2. Testing database initialization...")
    database.init_db()
    assert os.path.exists(config.DB_PATH), "Database file not created"
    print("   [PASSED] Database initialized successfully.")

    # 3. Authentication Tests
    print("3. Testing User Authentication (Signup & Login)...")
    test_user = "test_student"
    test_pass = "securepassword123"
    
    # Ensure test user doesn't already exist from a previous run
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (test_user,))
    conn.commit()
    conn.close()
    
    # Test signup
    signup_ok = database.register_user(test_user, test_pass)
    assert signup_ok is True, "Failed to register test user"
    
    # Test duplicate signup
    dup_signup = database.register_user(test_user, "anotherpassword")
    assert dup_signup is False, "Duplicate user signup should fail"
    
    # Test login success
    login_ok = database.verify_user(test_user, test_pass)
    assert login_ok is True, "Verify user failed with correct password"
    
    # Test login failure
    bad_login = database.verify_user(test_user, "wrongpassword")
    assert bad_login is False, "Verify user succeeded with incorrect password"
    print("   [PASSED] User registration and authentication verified.")

    # 4. Response Caching Tests
    print("4. Testing Response Caching...")
    test_query = "What is a neural network?"
    test_track = "AI/ML"
    test_response = "A neural network is a network or circuit of neurons..."
    
    # Clear cache first
    database.clear_cache()
    
    # Check cache miss
    cached = database.get_cached_response(test_query, test_track)
    assert cached is None, "Cache should be empty, but hit returned data"
    
    # Cache the response
    cache_saved = database.cache_response(test_query, test_track, test_response)
    assert cache_saved is True, "Failed to save response to cache"
    
    # Check cache hit
    cached_hit = database.get_cached_response(test_query, test_track)
    assert cached_hit == test_response, "Cache hit did not return matching response"
    print("   [PASSED] Query response caching verified.")

    # 5. Conversation Logs Tests
    print("5. Testing Conversation Logs...")
    log_ok = database.log_conversation(
        username=test_user,
        track=test_track,
        user_query=test_query,
        bot_response=test_response
    )
    assert log_ok is True, "Failed to log conversation details"
    
    history = database.get_user_conversation_history(test_user, limit=5)
    assert len(history) >= 1, "Log history should return at least 1 record"
    assert history[0]["query"] == test_query, "Log record query did not match input query"
    assert history[0]["response"] == test_response, "Log record response did not match input response"
    print("   [PASSED] Conversation logging verified.")
    
    # Clean up test user data
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (test_user,))
    conn.commit()
    conn.close()
    
    print("\n=== All Tests Passed Successfully! ===")
    logger.info("Verification tests completed. All modules verified.")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n❌ [FAILED] Assertion Error: {e}")
        logger.error(f"Backend verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ [FAILED] Unexpected Error: {e}")
        logger.error(f"Backend verification encountered an unexpected error: {e}")
        sys.exit(1)
