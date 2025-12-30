import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore
from rich.console import Console

console = Console()


def generate_story_plan(
    topic: str, character_meta: Dict[str, str], image_path: Optional[Path] = None
) -> List[Dict[str, str]]:
    """
    Calls Gemini 1.5 Pro (or 3.0 Preview) to generate a structured story plan.
    Supports multimodal input (Text + Image).
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
    model_name = "gemini-2.0-flash-exp"  # Using Flash for speed/multimodal, or stick to Pro if preferred.

    # Construct Prompt
    char_desc = character_meta.get("description", "A generic character")
    voice_desc = character_meta.get("voice_prompt", "Neutral voice")

    if image_path:
        prompt_text = f"""
        You are an expert cinematographic storyteller and director.
        
        Topic: {topic}
        Character: Look at the character in the attached image. This is the protagonist.
        Voice Style: {voice_desc}
        
        Create a compelling, multi-part video story based on this topic.
        The dialogue and tone should match the visual vibe of the character in the image.
        Break the story into a sequence of video segments.
        Each segment must be short enough for an 8-second video clip (MAXIMUM 12 words). Keep dialogue concise.
        
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
    else:
        prompt_text = f"""
        You are an expert cinematographic storyteller and director.
        
        Topic: {topic}
        Character: {char_desc}
        Voice Style: {voice_desc}
        
        Create a compelling, multi-part video story based on this topic.
        Break the story into a sequence of video segments.
        Each segment must be short enough for an 8-second video clip (MAXIMUM 12 words). Keep dialogue concise.
        
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

    parts: List[Dict[str, Any]] = [{"text": prompt_text}]

    # Add Image Part if exists
    if image_path and image_path.exists():
        try:
            with open(image_path, "rb") as img_f:
                img_data = base64.b64encode(img_f.read()).decode("utf-8")

            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/png",  # Assuming PNG, logic could be smarter
                        "data": img_data,
                    }
                }
            )
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to load character image for planner: {e}[/yellow]"
            )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",  # Enforce JSON output
        },
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        # Parse JSON from the response text
        # Candidates -> Content -> Parts -> Text
        text_content = result["candidates"][0]["content"]["parts"][0]["text"]
        # Clean potential markdown
        text_content = text_content.replace("```json", "").replace("```", "").strip()

        plan = json.loads(text_content)
        return plan

    except Exception as e:
        console.print(f"[red]Story Planning Failed:[/red] {e}")
        if "response" in locals():
            console.print(f"Response: {response.text}")
        # Fallback plan
        return [
            {
                "narration": f"I attempted to tell a story about {topic}, but the plans were lost in the ether.",
                "visual_prompt": f"Static and glitching digital screen with the words '{topic}'",
                "voice_direction": "Apologetic robot",
            }
        ]
