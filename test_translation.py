import os
from dotenv import load_dotenv
from services.translation_service import TranslationService

# Load environment variables
load_dotenv()

def test_real_translation():
    # 1. Get API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file.")
        return

    print(f"✓ Found API Key: {api_key[:5]}...")

    # 2. Initialize Service
    print("Initializing Gemini Service...")
    service = TranslationService(
        provider="gemini",
        api_key=api_key,
        model="gemini-2.5-flash"
    )

    # 3. Sample News Text
    news_text = """
    SpaceX has successfully launched its massive Starship rocket for the third time. 
    The spacecraft reached orbital velocity and completed several tests in space, 
    including a propellant transfer demonstration. Although communication was lost 
    during re-entry, the mission is considered a major success by engineers.
    This brings humanity one step closer to Mars.
    """

    # 4. Run Test (English -> Hindi)
    print("\nProcessing Article (English -> Hindi)...")
    try:
        result = service.translate_and_summarize(
            text=news_text,
            target_language="hi",
            max_length=200
        )
        
        print("\n✅ SUCCESS!")
        print("-" * 40)
        print(f"📄 English Summary:\n{result['summary']}")
        print("-" * 40)
        print(f"🕉️ Hindi Translation:\n{result['translated_summary']}")
        print("-" * 40)

        result = service.translate_and_summarize(
            text=news_text,
            target_language="bn",
            max_length=200
        )
        
        print("\n✅ SUCCESS!")
        print("-" * 40)
        print(f"📄 English Summary:\n{result['summary']}")
        print("-" * 40)
        print(f"🕉️ Bengali Translation:\n{result['translated_summary']}")
        print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == "__main__":
    test_real_translation()