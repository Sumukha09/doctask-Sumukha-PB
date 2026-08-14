import os
from app.llm.gemini import GeminiLLMAdapter
from app.llm.schemas import LLMRequest
from app.config import get_settings

def test_api():
    settings = get_settings()
    print("API KEY SET:", bool(settings.gemini_api_key))
    if not settings.gemini_api_key:
        print("NO API KEY")
        return
        
    llm = GeminiLLMAdapter()
    req = LLMRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say hello!"
    )
    print("Generating...")
    try:
        resp = llm.generate(req)
        print("Success:", resp.content)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_api()
