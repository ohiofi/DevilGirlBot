import os
import json
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# 1. Setup paths matching your main script configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE = SCRIPT_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

MOVIE_LIST_PATH_ENV = os.getenv("MOVIE_LIST_PATH")
if MOVIE_LIST_PATH_ENV:
    MOVIE_LIST_FILE = Path(MOVIE_LIST_PATH_ENV)
else:
    MOVIE_LIST_FILE = SCRIPT_DIR / "mars_madness_movie_list.txt"

# 2. Load the movie dictionaries to find poster paths from titles
movie_list = []
if MOVIE_LIST_FILE.exists():
    try:
        with open(MOVIE_LIST_FILE, "r", encoding="utf-8") as f:
            movie_list = json.load(f)
    except Exception as e:
        print(f"Error loading movie file: {e}")

def get_poster_path(movie_title):
    """Looks up the image file path from the loaded dictionary list."""
    for movie in movie_list:
        if isinstance(movie, dict) and movie.get("title") == movie_title:
            # Resolve relative to script directory
            return SCRIPT_DIR / movie.get("image")
    return None

def generate_matchup_graphic(match_label, left_title, right_title):
    """
    Creates a 1200x800 canvas with left and right movie posters side-by-side.
    Guaranteed not to crash if either poster is missing, deleted, or corrupted.
    """
    canvas_w, canvas_h = 1200, 800
    top_margin = 4
    side_margin = 4
    spacing = 2
    
    # Calculate target dimensions for each side lane
    poster_w = (canvas_w - (side_margin * 2) - spacing) // 2
    poster_h = canvas_h - top_margin - side_margin

    # 1. Initialize canvas background frame
    img = Image.new("RGB", (canvas_w, canvas_h), color="#1e1f29")
    draw = ImageDraw.Draw(img)

    # 2. Load fonts
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", size=50)
        fallback_font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", size=30)
    except Exception:
        font = ImageFont.load_default()
        fallback_font = ImageFont.load_default()

    # 3. Process Left Side Poster Safely
    left_path = get_poster_path(left_title)
    left_loaded = False
    
    if left_path and left_path.exists():
        try:
            with Image.open(left_path) as left_img:
                left_img.thumbnail((poster_w, poster_h))
                x_pos = side_margin + (poster_w - left_img.width) // 2
                y_pos = top_margin + (poster_h - left_img.height) // 2
                img.paste(left_img, (x_pos, y_pos))
                left_loaded = True
        except Exception as img_err:
            print(f"⚠️ Warning: Left poster '{left_title}' exists but failed to open (corrupted file?): {img_err}")

    if not left_loaded:
        # Visual fallback block displaying the specific movie title instead of crashing
        draw.rectangle([side_margin, top_margin, side_margin + poster_w, top_margin + poster_h], outline="#ff5555", width=4)
        error_msg = f"[missing poster for\n{left_title}]"
        draw.text((side_margin + poster_w // 2, top_margin + poster_h // 2), error_msg, fill="#ff5555", font=fallback_font, anchor="mm", align="center")

    # 4. Process Right Side Poster Safely
    right_path = get_poster_path(right_title)
    right_loaded = False
    
    if right_path and right_path.exists():
        try:
            with Image.open(right_path) as right_img:
                right_img.thumbnail((poster_w, poster_h))
                x_pos = side_margin + poster_w + spacing + (poster_w - right_img.width) // 2
                y_pos = top_margin + (poster_h - right_img.height) // 2
                img.paste(right_img, (x_pos, y_pos))
                right_loaded = True
        except Exception as img_err:
            print(f"⚠️ Warning: Right poster '{right_title}' exists but failed to open (corrupted file?): {img_err}")

    if not right_loaded:
        # Visual fallback block displaying the specific movie title instead of crashing
        x_start = side_margin + poster_w + spacing
        draw.rectangle([x_start, top_margin, x_start + poster_w, top_margin + poster_h], outline="#ff5555", width=4)
        error_msg = f"[missing poster for\n{right_title}]"
        draw.text((x_start + poster_w // 2, top_margin + poster_h // 2), error_msg, fill="#ff5555", font=fallback_font, anchor="mm", align="center")

    # 5. Centered text
    draw.text(
        (canvas_w // 2 + 3, canvas_h // 2), 
        f"{match_label.upper()}\n\n{left_title}\nversus\n{right_title}", 
        fill="#000000", 
        font=font, 
        anchor="mm",
        align="center",
        stroke_width=15,       # Thickness of the outline
        stroke_fill="#000000" # Color of the outline
    )
    draw.text(
        (canvas_w // 2 - 3, canvas_h // 2), 
        f"{match_label.upper()}\n\n{left_title}\nversus\n{right_title}", 
        fill="#000000", 
        font=font, 
        anchor="mm",
        align="center",
        stroke_width=15,       # Thickness of the outline
        stroke_fill="#000000" # Color of the outline
    )
    draw.text(
        (canvas_w // 2, canvas_h // 2), 
        f"{match_label.upper()}\n\n{left_title}\nversus\n{right_title}", 
        fill="#ffeeff", 
        font=font, 
        anchor="mm",
        align="center",
        stroke_width=15,       # Thickness of the outline
        stroke_fill="#000000" # Color of the outline
    )

    # 6. Save out the final compilation image asset
    output_path = SCRIPT_DIR / "matchup_test.png"
    try:
        img.save(output_path)
        print(f"🎉 Matchup graphic successfully saved to: {output_path}")
    except Exception as save_err:
        print(f"❌ Critical error saving compilation image to disk: {save_err}")

# --- TEST EXECUTION LOOP ---
if __name__ == "__main__":
    # Test execution data utilizing your active bracket match selections
    print("Testing matchup generation function...")
    generate_matchup_graphic(
        match_label="Semifinal 2",
        left_title="Earth vs the Spider (1958)",
        right_title="Zarkorr! the Invader (1996)"
    )