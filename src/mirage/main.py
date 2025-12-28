#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse
import datetime
import shutil
import re
from pathlib import Path
from typing import Optional

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
            # When not quiet, we let it print to stdout/stderr naturally
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

def cmd_weather(args: argparse.Namespace) -> None:
    """
    Orchestrates the Weather Atmospheric Experience generation.
    """
    location = args.location
    generate_video = args.video
    silent = args.silent
    
    # Setup Output Directory
    sanitized_loc = location.replace(" ", "_").replace("/", "-")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Use configured base directory
    output_dir = settings.output_base_dir / f"Weather_{sanitized_loc}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not silent:
        console.print(Panel(f"[bold green]Starting Mirage: Weather[/bold green]\nLocation: [cyan]{location}[/cyan]\nOutput: [yellow]{output_dir}[/yellow]", title="Mirage"))

    # Define paths
    context_file = output_dir / "context.txt"
    podcast_file = output_dir / "podcast.mp3"
    image_file = output_dir / "background_art.png"
    video_file = output_dir / "background_video.mp4"
    html_file = output_dir / "index.html"

    with console.status(f"[bold green]Gathering atmospheric data for {location}...[/bold green]", spinner="earth") as status:
        # 1. Gather Data
        if not silent:
            status.update(f"[bold green]Gathering atmospheric data for {location}...[/bold green]")
        
        # We use the config settings for commands
        cmd_gather = (
            f"{settings.atmos_cmd} alert \"{location}\" > \"{context_file}\" && "
            f"{settings.atmos_cmd} \"{location}\" >> \"{context_file}\" && "
            f"{settings.atmos_cmd} stars \"{location}\" >> \"{context_file}\" && "
            f"{settings.atmos_cmd} forecast \"{location}\" >> \"{context_file}\" && "
            f"{settings.atmos_cmd} forecast \"{location}\" --hourly >> \"{context_file}""
        )
        run_command(cmd_gather, quiet=True) 

        # Read context
        context_text = context_file.read_text(encoding="utf-8")

        # 2. Generate Audio
        if not silent:
            status.update("[bold blue]Synthesizing immersive audio podcast...[/bold blue]")
        # Pipe input to avoid gen-tts stdin detection issues
        run_command(f"cat \"{context_file}\" | {settings.gen_tts_cmd} --podcast --no-play --audio-format MP3 --output-file \"{podcast_file}\"", quiet=silent)

        # 3. Generate Image
        if not silent:
            status.update("[bold magenta]Dreaming up background visual...[/bold magenta]")
        run_command(f"cat \"{context_file}\" | {settings.lumina_cmd} --opt --output-dir \"{output_dir}\" -f background_art.png", quiet=silent)

        if not image_file.exists():
            console.print("[yellow]Warning: Lumina failed to generate an image. Creating placeholder.[/yellow]")
            run_command(f"{settings.convert_cmd} -size 1024x1024 xc:black \"{image_file}\"", quiet=silent)
        
        # 4. Generate Video (Optional)
        has_video = False
        if generate_video:
            if image_file.exists():
                if not silent:
                    status.update("[bold cyan]Animating scene with Vidius (this may take a moment)...[/bold cyan]")
                vid_prompt = f"Cinematic slow motion animation of {location}, realistic weather, highly detailed"
                run_command(f"{settings.vidius_cmd} \"{vid_prompt}\" -i \"{image_file}\" -o \"{video_file}\" -na", quiet=silent)
                has_video = video_file.exists()
            else:
                console.print("[yellow]Skipping video generation: No source image.[/yellow]")

        # 5. Generate HTML
        if not silent:
            status.update("[bold white]Assembling final experience...[/bold white]")
        
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
    """
    Orchestrates the Deep Research Documentary generation.
    """
    topic = args.topic
    generate_video = args.video
    silent = args.silent
    
    # Setup Output Directory
    sanitized_topic = topic.replace(" ", "_").replace("/", "-")[:50] # Limit length
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = settings.output_base_dir / f"Research_{sanitized_topic}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not silent:
        console.print(Panel(f"[bold green]Starting Mirage: Research Documentary[/bold green]\nTopic: [cyan]{topic}[/cyan]\nOutput: [yellow]{output_dir}[/yellow]", title="Mirage"))

    # Define paths
    context_file = output_dir / "research.md"
    podcast_file = output_dir / "podcast.mp3"
    music_file = output_dir / "music.mp3"
    image_file = output_dir / "background_art.png"
    video_file = output_dir / "background_video.mp4"
    html_file = output_dir / "index.html"

    with console.status(f"[bold green]Conducting deep research on: {topic}...[/bold green]", spinner="dots") as status:
        
        # 1. Deep Research
        if not silent:
            status.update(f"[bold green]Conducting deep research on: {topic}...[/bold green]")
        
        run_command(f"{settings.deep_research_cmd} research \"{topic}\" --output \"{context_file}\"", quiet=silent)
        
        if not context_file.exists():
            console.print("[red]Deep Research failed to produce output.[/red]")
            return

        # Read context
        context_text = context_file.read_text(encoding="utf-8")

        # 2. Generate Audio (Podcast) & Capture Script
        if not silent:
            status.update("[bold blue]Scripting and recording documentary...[/bold blue]")
        
        # We need to capture the output to get the script, but run_command only captures if quiet=True
        # We'll use subprocess manually here to guarantee capture
        tts_cmd = f"cat \"{context_file}\" | {settings.gen_tts_cmd} --podcast --no-play --audio-format MP3 --output-file \"{podcast_file}\""
        
        result = subprocess.run(tts_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[bold red]Error generating audio:[/bold red] {result.stderr}")
            # Continue mostly, or fail? Let's fail hard if no audio
            if not podcast_file.exists():
                return
        
        # Print output if not silent (so user sees progress/script if desired)
        if not silent:
            console.print(result.stdout)
            
        # Parse Script from Output
        full_output = result.stdout
        script_display_text = context_text # Default to research notes if parsing fails
        
        if "--- Generated Podcast Script ---" in full_output:
            try:
                raw_script = full_output.split("--- Generated Podcast Script ---")[1]
                # Clean up: Remove Speaker labels (Host:, Guest:, etc)
                # Regex: Start of line, (Host|Guest|Speaker \w+):, space
                clean_script = re.sub(r"^(Host|Guest|Speaker \w+):\s*", "", raw_script, flags=re.MULTILINE).strip()
                script_display_text = clean_script
            except Exception as e:
                console.print(f"[yellow]Warning: Could not parse script from output ({e}). Using raw notes.[/yellow]")

        # 3. Generate Music (Score)
        if not silent:
            status.update("[bold yellow]Composing original score...[/bold yellow]")
        music_prompt = f"Ambient documentary background music, {topic}, cinematic score"
        run_command(f"{settings.gen_music_cmd} \"{music_prompt}\" --output \"{music_file}\" --format mp3 --duration 30", quiet=silent) # 30s loop?

        # 4. Generate Image
        if not silent:
            status.update("[bold magenta]Capturing visuals...[/bold magenta]")
        img_prompt = f"Editorial photography of {topic}, cinematic lighting, highly detailed, 8k"
        run_command(f"{settings.lumina_cmd} --prompt \"{img_prompt}\" --output-dir \"{output_dir}\" --filename background_art.png", quiet=silent)

        # 5. Generate Video (Optional)
        has_video = False
        if generate_video:
            if image_file.exists():
                if not silent:
                    status.update("[bold cyan]Animating scene...[/bold cyan]")
                vid_prompt = f"Cinematic slow motion animation of {topic}, documentary style"
                run_command(f"{settings.vidius_cmd} \"{vid_prompt}\" -i \"{image_file}\" -o \"{video_file}\" -na", quiet=silent)
                has_video = video_file.exists()

        # 6. Generate HTML
        if not silent:
            status.update("[bold white]Publishing documentary...[/bold white]")
        
        env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
        template = env.get_template("research.html.j2")
        
        html_content = template.render(
            topic=topic,
            context_text=script_display_text,
            image_file=image_file.name,
            audio_file=podcast_file.name,
            music_file=music_file.name if music_file.exists() else None,
            video_file=video_file.name if has_video else None
        )
        
        html_file.write_text(html_content, encoding="utf-8")

    if not silent:
        console.print(Panel(f"[bold green]Documentary Ready![/bold green]\nOpen: [link=file://{html_file.absolute()}]{html_file}[/link]", border_style="green"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirage: AI Experience Generator")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- Weather Subcommand ---
    weather_parser = subparsers.add_parser("weather", help="Generate an Atmospheric Weather Experience")
    weather_parser.add_argument("-l", "--location", default=settings.default_location, help=f"Location for the weather forecast (default: {settings.default_location})")
    weather_parser.add_argument("-s", "--silent", action="store_true", help="Run in silent mode (suppress tool output)")
    weather_parser.add_argument("-v", "--video", action="store_true", help="Generate a background video animation using Vidius")
    weather_parser.add_argument("-b", "--background", action="store_true", help="Run in background mode (detach from terminal)")
    weather_parser.set_defaults(func=cmd_weather)

    # --- Research Subcommand ---
    research_parser = subparsers.add_parser("research", help="Generate a Deep Research Documentary")
    research_parser.add_argument("topic", help="Topic to research")
    research_parser.add_argument("-s", "--silent", action="store_true", help="Run in silent mode")
    research_parser.add_argument("-v", "--video", action="store_true", help="Generate video background")
    research_parser.add_argument("-b", "--background", action="store_true", help="Run in background mode")
    research_parser.set_defaults(func=cmd_research)

    args = parser.parse_args()

    # Handle Background Mode (Global or Subcommand specific logic)
    if hasattr(args, 'background') and args.background:
        # Construct the new command args, removing -b/--background
        clean_args = [arg for arg in sys.argv[1:] if arg not in ['-b', '--background']]
        
        # Use sys.argv[0] which is the path to the 'mirage' executable shim
        cmd = [sys.argv[0]] + clean_args
        
        console.print("[yellow]Respawning in background...[/yellow]")
        console.print(f"Command: {' '.join(cmd)}")
        console.print(f"Logs will be appended to [bold]{settings.log_file}[/bold]")
        
        # Ensure log directory exists
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set unbuffered output via env var
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