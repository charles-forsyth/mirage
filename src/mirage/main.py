#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse
import datetime
import shutil
import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.traceback import install
from jinja2 import Environment, FileSystemLoader

from mirage.config import settings

# Install rich traceback handler
install(show_locals=True)

console = Console()

def run_command(command: str, shell: bool = True, quiet: bool = False) -> None:
    """Runs a shell command and raises an exception on failure."""
    try:
        if quiet:
            subprocess.run(
                command, 
                shell=shell, 
                check=True, 
                executable='/bin/bash', 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
        else:
            subprocess.run(command, shell=shell, check=True, executable='/bin/bash')
            
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running command:[/bold red] {command}")
        if quiet:
            console.print("[red]Captured Stderr:[/red]")
            console.print(e.stderr)
            console.print("[red]Captured Stdout:[/red]")
            console.print(e.stdout)
        else:
            console.print(e)
        raise

def get_audio_duration(file_path: Path) -> float:
    """Gets the duration of a media file in seconds using ffprobe."""
    try:
        cmd = [
            settings.ffprobe_cmd, 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        console.print(f"[yellow]Warning: Could not determine duration of {file_path}. Defaulting to 60s.[/yellow]")
        return 60.0

# Helper alias for video duration probing logic (can reuse get_audio_duration for video files too)
get_duration = get_audio_duration

def cmd_weather(args: argparse.Namespace) -> None:
    """Orchestrates the Weather Atmospheric Experience generation."""
    location = args.location
    generate_video = args.video
    silent = args.silent
    
    sanitized_loc = location.replace(" ", "_").replace("/", "-")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = settings.output_base_dir / f"Weather_{sanitized_loc}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not silent:
        console.print(Panel(f"[bold green]Starting Mirage: Weather[/bold green]\nLocation: [cyan]{location}[/cyan]\nOutput: [yellow]{output_dir}[/yellow]", title="Mirage"))

    context_file = output_dir / "context.txt"
    podcast_file = output_dir / "podcast.mp3"
    image_file = output_dir / "background_art.png"
    video_file = output_dir / "background_video.mp4"
    html_file = output_dir / "index.html"

    with console.status(f"[bold green]Gathering atmospheric data for {location}...[/bold green]", spinner="earth") as status:
        if not silent: status.update(f"[bold green]Gathering atmospheric data for {location}...[/bold green]")
        
        cmd_gather = (
            f"{settings.atmos_cmd} alert \"{location}\" > \"{context_file}\" && "
            f"{settings.atmos_cmd} \"{location}\" >> \"{context_file}\" && "
            f"{settings.atmos_cmd} stars \"{location}\" >> \"{context_file}\" && "
            f"{settings.atmos_cmd} forecast \"{location}\" >> \"{context_file}\" && "
            f"{settings.atmos_cmd} forecast \"{location}\" --hourly >> \"{context_file}\""
        )
        run_command(cmd_gather, quiet=True) 

        context_text = context_file.read_text(encoding="utf-8")

        if not silent: status.update("[bold blue]Synthesizing immersive audio podcast...[/bold blue]")
        run_command(f"cat \"{context_file}\" | {settings.gen_tts_cmd} --podcast --no-play --audio-format MP3 --output-file \"{podcast_file}\"", quiet=silent)

        if not silent: status.update("[bold magenta]Dreaming up background visual...[/bold magenta]")
        run_command(f"cat \"{context_file}\" | {settings.lumina_cmd} --opt --output-dir \"{output_dir}\" -f background_art.png", quiet=silent)

        if not image_file.exists():
            console.print("[yellow]Warning: Lumina failed to generate an image. Creating placeholder.[/yellow]")
            run_command(f"{settings.convert_cmd} -size 1024x1024 xc:black \"{image_file}\"", quiet=silent)
        
        has_video = False
        if generate_video:
            if image_file.exists():
                if not silent: status.update("[bold cyan]Animating scene with Vidius...[/bold cyan]")
                vid_prompt = f"Cinematic slow motion animation of {location}, realistic weather, highly detailed"
                run_command(f"{settings.vidius_cmd} \"{vid_prompt}\" -i \"{image_file}\" -o \"{video_file}\" -na", quiet=silent)
                has_video = video_file.exists()
            else:
                console.print("[yellow]Skipping video generation: No source image.[/yellow]")

        if not silent: status.update("[bold white]Assembling final experience...[/bold white]")
        
        env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
        template = env.get_template("index.html.j2")
        
        html_content = template.render(
            location=location,
            context_text=context_text,
            image_file=image_file.name,
            audio_file=podcast_file.name,
            video_file=video_file.name if has_video else None
        )
        html_file.write_text(html_content, encoding="utf-8")

    if not silent:
        console.print(Panel(f"[bold green]Experience Ready![/bold green]\nOpen: [link=file://{html_file.absolute()}]{html_file}[/link]", border_style="green"))

def cmd_research(args: argparse.Namespace) -> None:
    """Orchestrates the Deep Research Documentary generation."""
    topic = args.topic
    generate_video = args.video
    silent = args.silent
    
    sanitized_topic = topic.replace(" ", "_").replace("/", "-")[:50]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = settings.output_base_dir / f"Research_{sanitized_topic}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not silent:
        console.print(Panel(f"[bold green]Starting Mirage: Research Documentary[/bold green]\nTopic: [cyan]{topic}[/cyan]\nOutput: [yellow]{output_dir}[/yellow]", title="Mirage"))

    context_file = output_dir / "research.md"
    podcast_file = output_dir / "podcast.mp3"
    music_file = output_dir / "music.mp3"
    image_file = output_dir / "background_art.png"
    video_file = output_dir / "background_video.mp4"
    html_file = output_dir / "index.html"

    with console.status(f"[bold green]Conducting deep research on: {topic}...[/bold green]", spinner="dots") as status:
        if not silent: status.update(f"[bold green]Conducting deep research on: {topic}...[/bold green]")
        
        run_command(f"{settings.deep_research_cmd} research \"{topic}\" --output \"{context_file}\"", quiet=silent)
        
        if not context_file.exists():
            console.print("[red]Deep Research failed to produce output.[/red]")
            return

        context_text = context_file.read_text(encoding="utf-8")

        if not silent: status.update("[bold blue]Scripting and recording documentary...[/bold blue]")
        tts_cmd = f"cat \"{context_file}\" | {settings.gen_tts_cmd} --podcast --no-play --audio-format MP3 --output-file \"{podcast_file}\""
        result = subprocess.run(tts_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[bold red]Error generating audio:[/bold red] {result.stderr}")
            if not podcast_file.exists(): return
        
        if not silent: console.print(result.stdout)
            
        full_output = result.stderr + "\n" + result.stdout
        script_display_text = context_text
        if "--- Generated Podcast Script ---" in full_output:
            try:
                raw_script = full_output.split("--- Generated Podcast Script ---")[1]
                clean_script = re.sub(r"^(Host|Guest|Speaker \w+):\s*", "", raw_script, flags=re.MULTILINE).strip()
                script_display_text = clean_script
            except Exception: pass

        if not silent: status.update("[bold yellow]Composing original score...[/bold yellow]")
        music_prompt = f"Ambient documentary background music, {topic}, cinematic score"
        run_command(f"{settings.gen_music_cmd} \"{music_prompt}\" --output \"{music_file}\" --format mp3 --duration 30", quiet=silent)

        if not silent: status.update("[bold magenta]Capturing visuals...[/bold magenta]")
        img_prompt = f"Editorial photography of {topic}, cinematic lighting, highly detailed, 8k"
        run_command(f"{settings.lumina_cmd} --prompt \"{img_prompt}\" --output-dir \"{output_dir}\" --filename background_art.png", quiet=silent)

        has_video = False
        if generate_video:
            if image_file.exists():
                if not silent: status.update("[bold cyan]Animating scene...[/bold cyan]")
                vid_prompt = f"Cinematic slow motion animation of {topic}, documentary style"
                run_command(f"{settings.vidius_cmd} \"{vid_prompt}\" -i \"{image_file}\" -o \"{video_file}\" -na", quiet=silent)
                has_video = video_file.exists()

        if not silent: status.update("[bold white]Publishing documentary...[/bold white]")
        env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
        template = env.get_template("research.html.j2")
        html_content = template.render(
            topic=topic, context_text=script_display_text, image_file=image_file.name,
            audio_file=podcast_file.name, music_file=music_file.name if music_file.exists() else None,
            video_file=video_file.name if has_video else None
        )
        html_file.write_text(html_content, encoding="utf-8")

    if not silent:
        console.print(Panel(f"[bold green]Documentary Ready![/bold green]\nOpen: [link=file://{html_file.absolute()}]{html_file}[/link]", border_style="green"))

def cmd_news_short(args: argparse.Namespace) -> None:
    """Generates a vertical YouTube Short News Report."""
    topic = args.topic
    silent = args.silent
    
    sanitized_topic = topic.replace(" ", "_").replace("/", "-")[:50]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = settings.output_base_dir / f"Short_{sanitized_topic}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not silent:
        console.print(Panel(f"[bold green]Starting Mirage: YouTube Short[/bold green]\nTopic: [cyan]{topic}[/cyan]\nOutput: [yellow]{output_dir}[/yellow]", title="Mirage"))

    podcast_file = output_dir / "voice.mp3"
    music_file = output_dir / "music.mp3"
    image_file = output_dir / "visual.png"
    video_file = output_dir / "visual.mp4"
    final_file = output_dir / f"Mirage_Short_{sanitized_topic}.mp4"

    with console.status(f"[bold green]Producing News Short for: {topic}...[/bold green]", spinner="dots") as status:
        
        # 1. Script & Voice
        if not silent: status.update("[bold blue]Writing and recording news brief...[/bold blue]")
        # Use pipe pattern with --mode news. Just pass the topic, let the mode handle framing.
        run_command(f"echo \"{topic}\" | {settings.gen_tts_cmd} --mode news --no-play --audio-format MP3 --output-file \"{podcast_file}\"", quiet=silent)

        if not podcast_file.exists():
            console.print("[red]Failed to generate voice track.[/red]")
            return

        # 2. Visuals (9:16)
        if not silent: status.update("[bold magenta]Capturing vertical visuals...[/bold magenta]")
        img_prompt = f"Vertical 9:16 cinematic b-roll shot of {topic}, atmospheric, hyper-realistic, 8k. No people, no text, no news anchor."
        run_command(f"{settings.lumina_cmd} --prompt \"{img_prompt}\" --aspect-ratio 9:16 --output-dir \"{output_dir}\" --filename visual.png", quiet=silent)

        if not image_file.exists():
            console.print("[yellow]Visual generation failed. creating placeholder.[/yellow]")
            run_command(f"{settings.convert_cmd} -size 1080x1920 xc:darkblue \"{image_file}\"", quiet=silent)

        # 3. Video Animation
        if not silent: status.update("[bold cyan]Animating background...[/bold cyan]")
        vid_prompt = f"Cinematic b-roll of {topic}, vertical 9:16, seamless loop, continuous motion"
        run_command(f"{settings.vidius_cmd} \"{vid_prompt}\" -i \"{image_file}\" -o \"{video_file}\" -ar 9:16 -na", quiet=silent)

        # 4. Music
        if not silent: status.update("[bold yellow]Composing background beat...[/bold yellow]")
        music_prompt = f"Breaking news intro music, high energy, electronic, background for {topic}"
        run_command(f"{settings.gen_music_cmd} \"{music_prompt}\" --output \"{music_file}\" --format mp3 --duration 60", quiet=silent)

        # 5. Assembly (FFmpeg)
        if not silent: status.update("[bold white]Assembling final video...[/bold white]")
        
        # Get duration of voice to know when to stop
        duration = get_audio_duration(podcast_file)
        
        # Complex filter:
        # 1. Loop video (stream_loop -1)
        # 2. Mix audio (voice + music at 0.2 vol)
        # 3. Cut to shortest stream (which should be voice if we limit music?) 
        # Actually simplest way: -t duration
        
        cmd_ffmpeg_safe = (
            f"{settings.ffmpeg_cmd} -y "
            f"-stream_loop -1 -i \"{video_file}\" "
            f"-i \"{podcast_file}\" "
            f"-stream_loop -1 -i \"{music_file}\" "
            f"-filter_complex \"[2:a]volume=0.2[music];[1:a][music]amix=inputs=2:duration=first[audio]\" "
            f"-map 0:v -map \"[audio]\" "
            f"-t {duration} "
            f"-c:v libx264 -pix_fmt yuv420p \"{final_file}\""
        )
        
        run_command(cmd_ffmpeg_safe, quiet=silent)

    if not silent:
        console.print(Panel(f"[bold green]News Short Ready![/bold green]\nFile: [link=file://{final_file.absolute()}]{final_file}[/link]", border_style="green"))

def cmd_character(args: argparse.Namespace) -> None:
    """Manages the Character Library."""
    action = args.action
    lib_dir = settings.character_library_dir
    lib_dir.mkdir(parents=True, exist_ok=True)

    if action == "list":
        chars = sorted(lib_dir.glob("*.png"))
        if not chars:
            console.print("[yellow]Library is empty.[/yellow]")
        else:
            console.print("[bold green]Character Library:[/bold green]")
            for c in chars:
                console.print(f"  - {c.stem}")

    elif action == "add":
        if not args.name or not args.image:
            console.print("[red]Error: --name and --image required for add.[/red]")
            return
        src = Path(args.image)
        if not src.exists():
            console.print(f"[red]Error: Image not found: {src}[/red]")
            return
        dest = lib_dir / f"{args.name}.png"
        shutil.copy(src, dest)
        console.print(f"[green]Added character '{args.name}' to library.[/green]")

    elif action == "remove":
        if not args.name:
            console.print("[red]Error: --name required for remove.[/red]")
            return
        dest = lib_dir / f"{args.name}.png"
        if dest.exists():
            dest.unlink()
            console.print(f"[green]Removed character '{args.name}'.[/green]")
        else:
            console.print(f"[yellow]Character '{args.name}' not found.[/yellow]")
    
    elif action == "create":
        if not args.name or not args.prompt:
            console.print("[red]Error: --name and --prompt required for create.[/red]")
            return
        
        dest = lib_dir / f"{args.name}.png"
        if dest.exists():
            console.print(f"[yellow]Character '{args.name}' already exists. Overwriting...[/yellow]")
        
        console.print(f"[magenta]Generating character '{args.name}' with Lumina...[/magenta]")
        lumina_prompt = f"Vertical 9:16 portrait of {args.prompt}, highly detailed, cinematic lighting, 8k"
        
        # Run lumina
        run_command(f"{settings.lumina_cmd} --prompt \"{lumina_prompt}\" --aspect-ratio 9:16 --output-dir \"{lib_dir}\" --filename \"{args.name}.png\"")
        
        if dest.exists():
            console.print(f"[green]Character '{args.name}' created successfully.[/green]")
        else:
            console.print("[red]Failed to create character.[/red]")

def cmd_story(args: argparse.Namespace) -> None:
    """Generates a Multi-Part Story Video for Shorts."""
    topic = args.topic
    character_desc = args.character
    silent = args.silent
    
    sanitized_topic = topic.replace(" ", "_").replace("/", "-")[:50]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = settings.output_base_dir / f"Story_{sanitized_topic}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not silent:
        console.print(Panel(f"[bold green]Starting Mirage: Story Mode[/bold green]\nTopic: [cyan]{topic}[/cyan]\nOutput: [yellow]{output_dir}[/yellow]", title="Mirage"))

    # Files
    script_file = output_dir / "script.txt"
    base_image = output_dir / "base_char.png"
    merged_video = output_dir / "Mirage_Story_Final.mp4"

    with console.status(f"[bold green]Weaving story for: {topic}...[/bold green]", spinner="dots") as status:
        
        # 1. Generate Script (3 Sentences)
        if not silent: status.update("[bold blue]Writing story script...[/bold blue]")
        prompt = f"Write a dramatic, 3-sentence story about {topic}. The sentences should be concise and evocative."
        
        script_gen_cmd = f"echo \"{prompt}\" | {settings.gen_tts_cmd} --mode storyteller --no-play --output-file /dev/null"
        result = subprocess.run(script_gen_cmd, shell=True, capture_output=True, text=True)
        
        # Parse script
        full_out = result.stderr + "\n" + result.stdout
        script_text = ""
        
        # Check for both Podcast and Storyteller headers
        if "--- Generated Podcast Script ---" in full_out: 
             try:
                 script_text = full_out.split("--- Generated Podcast Script ---")[1].strip()
                 script_text = re.sub(r"^(Narrator|Speaker):\s*", "", script_text, flags=re.MULTILINE).strip()
             except Exception: pass
        elif "--- Generated Storyteller Script ---" in full_out:
             try:
                 script_text = full_out.split("--- Generated Storyteller Script ---")[1].strip()
                 script_text = re.sub(r"^(Narrator|Speaker):\s*", "", script_text, flags=re.MULTILINE).strip()
             except Exception: pass
        
        if not script_text:
            # Fallback script if generation parsing failed
            script_text = f"This is the story of {topic}. It is a tale of wonder and mystery. Join us as we explore its secrets."
        
        script_file.write_text(script_text)
        
        # Split into 3 chunks
        sentences = re.split(r'(?<=[.!?])\s+', script_text)
        chunks: list[str] = []
        current_chunk = ""
        for s in sentences:
            if len(chunks) < 2:
                current_chunk += s + " "
                if len(current_chunk) > 50: # Rough length
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
            else:
                current_chunk += s + " "
        chunks.append(current_chunk.strip())
        
        # Ensure exactly 3 chunks (pad or trim)
        while len(chunks) < 3: chunks.append("...")
        chunks = chunks[:3]

        # 2. Base Character
        if not silent: status.update("[bold magenta]Casting character...[/bold magenta]")
        
        # Check library
        char_lib_path = settings.character_library_dir / f"{character_desc}.png"
        
        if character_desc and char_lib_path.exists():
             shutil.copy(char_lib_path, base_image)
             if not silent: console.print(f"[green]Using character from library: {character_desc}[/green]")
        else:
             char_prompt = f"Vertical 9:16 portrait of {character_desc if character_desc else topic}, highly detailed, cinematic lighting, 8k"
             run_command(f"{settings.lumina_cmd} --prompt \"{char_prompt}\" --aspect-ratio 9:16 --output-dir \"{output_dir}\" --filename base_char.png", quiet=silent)
        
        current_image = base_image
        video_parts = []

        # 3. Loop Generation (3 Parts with Native Audio)
        for i, chunk in enumerate(chunks):
            part_num = i + 1
            if not silent: status.update(f"[bold cyan]Animating Part {part_num}/3...[/bold cyan]")
            
            part_video = output_dir / f"part{part_num}.mp4"
            
            # Vidius Prompt - Sanitize quotes
            clean_chunk = chunk.replace("'", "").replace('"', "")
            
            # Construct prompt for speaking character
            speaker_desc = character_desc if character_desc else "The character"
            vid_prompt = f"{speaker_desc} speaking: '{clean_chunk}', vertical 9:16"
            
            # Generate video (with audio this time!)
            run_command(f"{settings.vidius_cmd} \"{vid_prompt}\" -i \"{current_image}\" -o \"{part_video}\" -ar 9:16", quiet=silent)
            video_parts.append(part_video)
            
            # Extract last frame for next iteration (if not last part)
            if i < 2:
                next_image = output_dir / f"frame{part_num}.png"
                run_command(f"{settings.ffmpeg_cmd} -y -sseof -1 -i \"{part_video}\" -vf unsharp=5:5:1.0:5:5:0.0 -vframes 1 \"{next_image}\"", quiet=silent)
                current_image = next_image

        # 4. Stitch Videos (XFade Filtergraph)
        if not silent: status.update("[bold white]Stitching video segments with crossfade...[/bold white]")
        
        # Probe durations
        durations = [get_duration(v) for v in video_parts]
        fade_duration = 0.5
        
        inputs = ""
        for v in video_parts:
            inputs += f"-i \"{v}\" "
        
        v_accum = "0:v"
        a_accum = "0:a"
        offset = 0.0
        
        video_filters = []
        audio_filters = []
        
        for i in range(1, len(video_parts)):
            prev_dur = durations[i-1]
            offset += prev_dur - fade_duration
            
            v_next = f"{i}:v"
            v_out = f"v{i}"
            video_filters.append(f"[{v_accum}][{v_next}]xfade=transition=fade:duration={fade_duration}:offset={offset}[{v_out}]")
            v_accum = v_out
            
            a_next = f"{i}:a"
            a_out = f"a{i}"
            audio_filters.append(f"[{a_accum}][{a_next}]acrossfade=d={fade_duration}:c1=tri:c2=tri[{a_out}]")
            a_accum = a_out
            
        filter_complex = ";".join(video_filters + audio_filters)
        
        # If single clip, no crossfade needed
        if len(video_parts) == 1:
            cmd_stitch = f"{settings.ffmpeg_cmd} -y -i \"{video_parts[0]}\" -c copy \"{merged_video}\""
        else:
            cmd_stitch = (
                f"{settings.ffmpeg_cmd} -y {inputs} "
                f"-filter_complex \"{filter_complex}\" "
                f"-map \"[{v_accum}]\" -map \"[{a_accum}]\" "
                f"-c:v libx264 -pix_fmt yuv420p \"{merged_video}\""
            )
        
        run_command(cmd_stitch, quiet=silent)

    if not silent:
        console.print(Panel(f"[bold green]Story Ready![/bold green]\nFile: [link=file://{merged_video.absolute()}]{merged_video}[/link]", border_style="green"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirage: AI Experience Generator")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- Weather ---
    weather = subparsers.add_parser("weather", help="Generate an Atmospheric Weather Experience")
    weather.add_argument("-l", "--location", default=settings.default_location, help="Location")
    weather.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    weather.add_argument("-v", "--video", action="store_true", help="Video background")
    weather.add_argument("-b", "--background", action="store_true", help="Background mode")
    weather.set_defaults(func=cmd_weather)

    # --- Research ---
    research = subparsers.add_parser("research", help="Generate a Deep Research Documentary")
    research.add_argument("topic", help="Topic")
    research.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    research.add_argument("-v", "--video", action="store_true", help="Video background")
    research.add_argument("-b", "--background", action="store_true", help="Background mode")
    research.set_defaults(func=cmd_research)

    # --- News Short ---
    news = subparsers.add_parser("news-short", help="Generate a YouTube Short News Report")
    news.add_argument("topic", help="News Topic")
    news.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    news.add_argument("-b", "--background", action="store_true", help="Background mode")
    news.set_defaults(func=cmd_news_short)

    # --- Story Mode ---
    story = subparsers.add_parser("story", help="Generate a 3-part seamless Story Short")
    story.add_argument("topic", help="Story Topic")
    story.add_argument("-c", "--character", help="Character Description (e.g. 'Cyberpunk Wizard')")
    story.add_argument("-s", "--silent", action="store_true", help="Silent mode")
    story.add_argument("-b", "--background", action="store_true", help="Background mode")
    story.set_defaults(func=cmd_story)

    # --- Character Library ---
    char_parser = subparsers.add_parser("character", help="Manage Character Library")
    char_parser.add_argument("action", choices=["list", "add", "remove", "create"], help="Action")
    char_parser.add_argument("name", nargs="?", help="Character Name") # Positional name for convenience
    char_parser.add_argument("-i", "--image", help="Path to existing image")
    char_parser.add_argument("-p", "--prompt", help="Prompt for creation")
    char_parser.set_defaults(func=cmd_character)

    args = parser.parse_args()

    # Handle Background Mode
    if hasattr(args, 'background') and args.background:
        clean_args = [arg for arg in sys.argv[1:] if arg not in ['-b', '--background']]
        cmd = [sys.argv[0]] + clean_args
        
        console.print("[yellow]Respawning in background...[/yellow]")
        console.print(f"Command: {' '.join(cmd)}")
        console.print(f"Logs will be appended to [bold]{settings.log_file}[/bold]")
        
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        with open(settings.log_file, "a") as log_file:
             subprocess.Popen(cmd, stdout=log_file, stderr=log_file, start_new_session=True, env=env)
             
        console.print("[green]Mirage is running in the background.[/green]")
        sys.exit(0)

    try:
        if hasattr(args, 'func'):
            args.func(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user.[/bold red]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Fatal Error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)

if __name__ == "__main__":
    main()