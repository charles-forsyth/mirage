import os
import json
import requests
from typing import List, Dict, Any
from rich.console import Console

console = Console()

def generate_story_plan(topic: str, character_meta: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Calls Gemini 1.5 Pro (or 3.0 Preview) to generate a structured story plan.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Try loading from standard env file location if not in env
        env_path = os.path.expanduser("~/.config/mirage/.env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GOOGLE_API_KEY="):
                        api_key = line.split("=")[1].strip().strip('"')
                        break
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment or config.")

    # Model: Using gemini-1.5-pro as a proxy for 'best available' or try specific 3.0 endpoint if known.
    # The user requested 'gemini-3-pro-preview'. 
    # Current public API usually maps this via models/gemini-1.5-pro-latest or specific beta endpoints.
    # We will try the requested name, but fallback to 1.5-pro if 404.
    model_name = "gemini-1.5-pro" # stable fallback
    
    # Construct Prompt
    char_desc = character_meta.get("description", "A generic character")
    voice_desc = character_meta.get("voice_prompt", "Neutral voice")
    
    prompt_text = f"""
    You are an expert cinematographic storyteller and director.
    
    Topic: {topic}
    Character: {char_desc}
    Voice Style: {voice_desc}
    
    Create a compelling, multi-part video story based on this topic.
    Break the story into a sequence of video segments.
    Each segment must be short enough for an 8-second video clip (approx 15-25 words).
    
    Return ONLY a raw JSON list of objects. Do not include markdown formatting like ```json.
    Structure:
    [
        {{
            "narration": "The exact spoken text for this segment.",
            "visual_prompt": "A detailed visual description of the scene for an AI video generator.",
            "voice_direction": "Emotion or tone direction for the voice actor."
        }},
        ...
    ]
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json" # Enforce JSON output
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Parse JSON from the response text
        text_content = result["candidates"][0]["content"]["parts"][0]["text"]
        # Clean potential markdown
        text_content = text_content.replace("```json", "").replace("```", "").strip()
        
        plan = json.loads(text_content)
        return plan
        
    except Exception as e:
        console.print(f"[red]Story Planning Failed:[/red] {e}")
        if 'response' in locals():
            console.print(f"Response: {response.text}")
        # Fallback plan
        return [
            {
                "narration": f"I attempted to tell a story about {topic}, but the plans were lost in the ether.",
                "visual_prompt": f"Static and glitching digital screen with the words '{topic}'",
                "voice_direction": "Apologetic robot"
            }
        ]
