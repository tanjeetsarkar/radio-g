import redis
import os
import sys

# Try to load .env manually if python-dotenv is installed, otherwise rely on shell env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed, reading environment variables directly.")

host = os.getenv("REDIS_HOST")
port = os.getenv("REDIS_PORT")
password = os.getenv("REDIS_PASSWORD")
ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
username = os.getenv("REDIS_USERNAME", "default")

print(f"🔌 Connecting to: {host}:{port}")
print(f"🔒 SSL: {ssl}")

if not host or not port:
    print("❌ Error: REDIS_HOST or REDIS_PORT not found in environment.")
    sys.exit(1)

try:
    r = redis.Redis(
        host=host, 
        port=int(port), 
        password=password, 
        username=username,
        socket_connect_timeout=10,
        decode_responses=True
    )
    # Test command
    r.set("test_key", "Hello from Local!")
    value = r.get("test_key")

    if value == "Hello from Local!":
        print("✅ SUCCESS! Connected to Redis Cloud and verified read/write.")
    else:
        print(f"⚠️  Connected, but value mismatch: {value}")

except Exception as e:
    print(f"❌ Connection Failed: {e}")