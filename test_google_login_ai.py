from google import genai
from google.genai.types import HttpOptions

client = genai.Client(http_options=HttpOptions(api_version="v1"))
prompt = f"""
        You are a news editor. 
        1. Summarize the article for a radio broadcast (approx 150 chars).
        2. Translate that summary into hindi.
        """
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[prompt, "How does AI work?"],
)
print(response.text)