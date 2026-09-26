import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore
from rich.console import Console

console = Console()


# Text model for story and news planning. Current GA Pro-class model with JSON output.
PLANNER_MODEL = os.environ.get("MIRAGE_PLANNER_MODEL", "gemini-3.1-pro-preview")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def _load_api_key() -> str:
    """Mirage's own Gemini key: GEMINI_API_KEY (or legacy GOOGLE_API_KEY) from
    ~/.config/mirage/.env, falling back to the process environment."""
    env_path = os.path.expanduser("~/.config/mirage/.env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                name, _, value = line.strip().partition("=")
                if name in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and value:
                    return value.strip().strip('"').strip("'")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY not found in ~/.config/mirage/.env or the environment."
        )
    return key


def _post_gemini(payload: Dict[str, Any]) -> "requests.Response":
    response = requests.post(
        GEMINI_URL.format(model=PLANNER_MODEL),
        headers={"x-goog-api-key": _load_api_key()},
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    return response


def generate_story_plan(
    topic: str, character_meta: Dict[str, str], image_path: Optional[Path] = None
) -> List[Dict[str, str]]:
    """
    Calls Gemini to generate a structured story plan.
    Supports multimodal input (Text + Image).
    """

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
        Each segment must be short enough for an 8-second video clip (MAXIMUM 18 words). Keep dialogue natural and flowing.
        
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
        Each segment must be short enough for an 8-second video clip (MAXIMUM 18 words). Keep dialogue natural and flowing.
        
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

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",  # Enforce JSON output
        },
    }

    try:
        response = _post_gemini(payload)
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


def generate_news_plan(news_text: str) -> List[Dict[str, str]]:
    """
    Calls Gemini to break down a long news report into visual B-roll segments.
    """

    prompt_text = f"""
    You are a Video Editor aligning visuals to a pre-recorded audio track.
    
    Source Text:
    {news_text}
    
    Task: Split this EXACT text into a sequence of video segments.
    1. Group related sentences together into logical B-roll chunks.
       - IMPORTANT: Make segments SHORT (approx 5-10 seconds of speech).
       - Aim for MANY segments to keep the visuals dynamic.
       - Break long sentences into multiple segments if natural to do so.
    2. CONSTRAINT: Do NOT rewrite, summarize, or change the text. The 'narration' field must match the input text EXACTLY, chunk by chunk.
    3. For EACH segment, write a "visual_prompt" for an AI image generator (Lumina).
       - Photorealistic B-Roll description.
       - NO text, NO charts, NO infographics in the image.
    4. Return valid JSON.
    
    Structure:
    [
        {{
            "narration": "Exact substring from source text.",
            "visual_prompt": "Detailed visual description."
        }},
        ...
    ]
    """

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.5,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = _post_gemini(payload)
        result = response.json()

        text_content = result["candidates"][0]["content"]["parts"][0]["text"]
        text_content = text_content.replace("```json", "").replace("```", "").strip()
        plan = json.loads(text_content)
        return plan

    except Exception as e:
        console.print(f"[red]News Planning Failed:[/red] {e}")
        return [
            {
                "narration": "We are experiencing technical difficulties generating the news feed.",
                "visual_prompt": "TV static and color bars, retro style",
            }
        ]
