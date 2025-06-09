import os
from core.memory import ChatHistoryManager

# File to store conversation history
TEST_HISTORY_FILE = "test_conversation_history.jsonl"

# Clean up if previous file exists
if os.path.exists(TEST_HISTORY_FILE):
    os.remove(TEST_HISTORY_FILE)

# Initialize chat history manager
history = ChatHistoryManager(max_history=3, history_file=TEST_HISTORY_FILE)

history.set_system_message({
    "role": "system",
    "content": "You are a helpful assistant. Only speak when asked."
})

# Add some messages
history.add_message({"role": "user", "content": "Hello!"})
history.add_message({"role": "assistant", "content": "Hi, how can I help?"})
history.add_message({"role": "user", "content": "What’s the weather today?"})

# Print recent messages (should include all three)
print("Recent messages:")
for msg in history.get_recent_messages():
    print(msg)

# Add one more message (this should trim the first message due to max_history=3)
history.add_message({"role": "assistant", "content": "It's sunny and 25°C."})

print("\nAfter adding a 4th message (oldest should be trimmed):")
for msg in history.get_recent_messages():
    print(msg)

# Record function attempts
print("\nFunction attempt counts:")
print("weather_check():", history.record_function_attempt("weather_check", {"location": "Nairobi"}))
print("weather_check():", history.record_function_attempt("weather_check", {"location": "Nairobi"}))
print("translate():", history.record_function_attempt("translate", {"text": "hello", "lang": "fr"}))

# Reload from file to confirm persistence
new_history = ChatHistoryManager(max_history=3, history_file=TEST_HISTORY_FILE)
print("\nLoaded from file:")
for msg in new_history.get_recent_messages():
    print(msg)

# Cleanup test file
os.remove(TEST_HISTORY_FILE)
