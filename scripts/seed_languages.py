import sys
import os
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.language_manager import get_language_manager

def seed():
    mgr = get_language_manager()
    
    config = {
        "en": {
            "name": "English",
            "flag": "ENG",
            "voice_id": "JBFqnCBsd6RMkjVDRZzb", # George
            "enabled": True
        },
        "hi": {
            "name": "Hindi",
            "flag": "HI",
            "voice_id": "zs7UfyHqCCmny7uTxCYi", # Fin
            "enabled": True
        },
        "bn": {
            "name": "Bengali",
            "flag": "BEN",
            "voice_id": "c7VOtb2tmfLXLqWBCXlt", # Fin
            "enabled": True
        }
    }
    
    mgr.set_config(config)
    print("✓ Language configuration seeded to Redis")

if __name__ == "__main__":
    seed()