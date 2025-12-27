import os
from dotenv import load_dotenv
from services.tts_service import TTSService

# Load environment variables
load_dotenv()

def test_real_voice():
    # 1. Get API Key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ ERROR: ELEVENLABS_API_KEY not found in .env file.")
        return

    print(f"✓ Found API Key: {api_key[:5]}...")

    # 2. Initialize Service
    print("Initializing ElevenLabs Service...")
    tts = TTSService(
        provider="elevenlabs",
        api_key=api_key,
        output_dir="test_audio_output"
    )

    # 3. Define test phrases
    phrases = {
        "en": "This is a test broadcast from the Dynamic News Desk.",
        "hi": "यह डायनामिक न्यूज़ डेस्क से एक परीक्षण प्रसारण है।",  # Hindi
        "bn": "এটি ডায়নামিক নিউজ ডেস্ক থেকে একটি পরীক্ষামূলক সম্প্রচার।" # Bengali
    }

    # 4. Generate
    for lang, text in phrases.items():
        print(f"\nGeneratng {lang.upper()} audio...")
        try:
            filename = f"test_voice_{lang}.mp3"
            path = tts.save_speech(text, lang, filename=filename)
            print(f"✅ Success! Saved to: {path}")
            
            # Check file size
            size = os.path.getsize(path)
            print(f"   File size: {size/1024:.2f} KB")
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_real_voice()