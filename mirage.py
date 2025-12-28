#!/usr/bin/env python3
import subprocess
import os
import glob
import time
import argparse
import datetime
import shutil
import sys

def run_command(command, shell=True, quiet=False):
    """Runs a shell command and raises an exception on failure."""
    try:
        if quiet:
            subprocess.run(command, shell=shell, check=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            subprocess.run(command, shell=shell, check=True, executable='/bin/bash')
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        if quiet:
            print("Captured Stderr:")
            print(e.stderr)
            print("Captured Stdout:")
            print(e.stdout)
        else:
            print(e)
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Generate an Atmospheric Experience.")
    parser.add_argument("-l", "--location", default="home", help="Location for the weather forecast (default: home)")
    parser.add_argument("-s", "--silent", action="store_true", help="Run in silent mode (suppress tool output)")
    parser.add_argument("-v", "--video", action="store_true", help="Generate a background video animation using Vidius")
    parser.add_argument("-b", "--background", action="store_true", help="Run in background mode (detach from terminal)")
    args = parser.parse_args()

    if args.background:
        # Construct the new command args, removing -b/--background
        clean_args = [arg for arg in sys.argv[1:] if arg not in ['-b', '--background']]
        # Use -u for unbuffered output so logs appear immediately
        cmd = [sys.executable, "-u", sys.argv[0]] + clean_args
        
        print(f"Respawning in background: {' '.join(cmd)}")
        print("Logs will be appended to mirage.log")
        
        with open("mirage.log", "a") as log_file:
             # start_new_session=True creates a new session, effectively detaching
             subprocess.Popen(cmd, stdout=log_file, stderr=log_file, start_new_session=True)
             
        print("Mirage is running in the background.")
        sys.exit(0)

    location = args.location
    silent = args.silent
    generate_video = args.video
    
    # Create Output Directory
    # Format: output/Location_YYYY-MM-DD_HH-MM-SS
    sanitized_loc = location.replace(" ", "_").replace("/", "-")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("output", f"{sanitized_loc}_{timestamp}")
    
    os.makedirs(output_dir, exist_ok=True)

    print("--- Starting Experience Generation ---")
    print(f"Target Location: {location}")
    print(f"Output Directory: {output_dir}")
    if generate_video:
        print("Video generation enabled.")

    # Define paths relative to output_dir
    context_file = os.path.join(output_dir, "context.txt")
    podcast_file = os.path.join(output_dir, "podcast.mp3")
    image_file = os.path.join(output_dir, "background_art.png")
    html_file = os.path.join(output_dir, "index.html")

    # 1. Gather Weather & Context Data
    print("1. Gathering atmospheric data...")
    cmd_gather = (
        f"atmos alert \"{location}\" > \"{context_file}\" && "
        f"atmos \"{location}\" >> \"{context_file}\" && "
        f"atmos stars \"{location}\" >> \"{context_file}\" && "
        f"atmos forecast \"{location}\" >> \"{context_file}\" && "
        f"atmos forecast \"{location}\" --hourly >> \"{context_file}\""
    )
    run_command(cmd_gather, quiet=silent)

    # Read the generated text
    with open(context_file, "r") as f:
        full_text = f.read()

    # 2. Generate Audio
    print("2. Generating podcast audio...")
    # Note: gen-tts might print to stdout, so we suppress if silent
    # Changed to pipe input to avoid gen-tts detecting 'piped input' conflict with --input-file when running in background
    run_command(f"cat \"{context_file}\" | gen-tts --podcast --no-play --audio-format MP3 --output-file \"{podcast_file}\"", quiet=silent)

    # 3. Generate Image
    print("3. Generating visual assets with Lumina...")
    run_command(f"cat \"{context_file}\" | lumina --opt --output-dir \"{output_dir}\" -f background_art.png", quiet=silent)
    
    # Check if generation was successful
    if os.path.exists(image_file):
        if not silent:
            print(f"   Found generated image: {image_file}")
    else:
        print("   Warning: No image detected from Lumina. Using placeholder.")
        run_command(f"convert -size 1024x1024 xc:black \"{image_file}\"", quiet=silent)

    # 4. Generate Video (Optional)
    video_html_block = ""
    video_js_block = ""
    
    if generate_video:
        print("4. Generating video animation with Vidius...")
        video_file = os.path.join(output_dir, "background_video.mp4")
        
        if os.path.exists(image_file):
            vid_prompt = f"Cinematic slow motion animation of {location}, realistic weather, highly detailed"
            run_command(f"vidius \"{vid_prompt}\" -i \"{image_file}\" -o \"{video_file}\" -na", quiet=silent)
            
            # HTML for Video
            video_html_block = f"""
    <div class="video-container" id="videoContainer">
        <video id="bgVideo" muted loop playsinline>
            <source src="background_video.mp4" type="video/mp4">
        </video>
    </div>
"""
            # JS for Video Transition
            video_js_block = """
        const bgVideo = document.getElementById('bgVideo');
        const videoContainer = document.getElementById('videoContainer');

        if (bgVideo) {
            bgVideo.addEventListener('loadeddata', () => {
                console.log("Video loaded, starting playback and fade-in...");
                bgVideo.play().then(() => {
                    setTimeout(() => {
                        videoContainer.style.opacity = '1';
                    }, 500);
                }).catch(e => console.error("Video playback failed:", e));
            });
        }
"""
        else:
            print("   Skipping video generation (no input image).")

    # 5. Generate HTML
    print("5. Constructing index.html...")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atmospheric Forecast: {location}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            background-color: #000;
            overflow: hidden;
            font-family: 'Courier New', Courier, monospace;
        }}
        
        /* Base Image Layer */
        .image-container {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url('background_art.png');
            background-size: cover;
            background-position: center;
            opacity: 0.8;
            z-index: 0;
        }}

        /* Video Layer (Fades in) */
        .video-container {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            opacity: 0; /* Start hidden */
            transition: opacity 3s ease-in-out;
            z-index: 1; /* On top of image */
            overflow: hidden;
        }}

        video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
            -webkit-mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
        }}

        /* Vignette Overlay */
        .vignette {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(circle at center, transparent 40%, black 100%);
            z-index: 2;
            pointer-events: none;
        }}

        /* Scrolling Text Container */
        .text-scroll-container {{
            position: absolute;
            right: 5%;
            top: 10%;
            bottom: 10%;
            width: 45%;
            overflow: hidden;
            z-index: 10;
            background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.5) 10%, rgba(0,0,0,0.5) 90%, transparent);
            display: flex;
            justify-content: flex-start;
        }}

        .scrolling-content {{
            color: #d1d5db; /* Light grayish white */
            font-size: 0.9rem;
            line-height: 1.2;
            white-space: pre;
            animation: scroll-up 60s linear infinite; /* Fallback animation */
        }}

        /* Audio Player */
        audio {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 50;
            opacity: 0.5;
            transition: opacity 0.3s;
        }}
        audio:hover {{
            opacity: 1;
        }}
    </style>
</head>
<body>

    <div class="image-container" id="bgImage"></div>
    {video_html_block}
    <div class="vignette"></div>

    <div class="text-scroll-container">
        <div class="scrolling-content" id="textContent">
{full_text}
        </div>
    </div>

    <audio id="podcastAudio" controls autoplay>
        <source src="podcast.mp3" type="audio/mpeg">
        Your browser does not support the audio element.
    </audio>

    <script>
        const audio = document.getElementById('podcastAudio');
        const textContent = document.getElementById('textContent');
        const scrollContainer = document.querySelector('.text-scroll-container');
        
        {video_js_block}

        // Simple Sync Logic
        audio.addEventListener('timeupdate', () => {{
            if (audio.duration) {{
                const percentage = audio.currentTime / audio.duration;
                const maxScroll = textContent.scrollHeight - scrollContainer.clientHeight + 200; 
                const scrollPos = maxScroll * percentage;
                
                textContent.style.animation = 'none';
                textContent.style.transform = `translateY(-${{scrollPos}}px)`;
            }}
        }});

        // Autoplay handling
        window.addEventListener('load', () => {{
            audio.play().catch(e => {{
                console.log("Autoplay blocked, waiting for user interaction");
            }});
        }});
    </script>
</body>
</html>
"""

    with open(html_file, "w") as f:
        f.write(html_content)

    print("--- Generation Complete ---")
    print(f"Result available at: {html_file}")

if __name__ == "__main__":
    main()
