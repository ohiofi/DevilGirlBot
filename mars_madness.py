import time
from mastodon import Mastodon
from mastodon.errors import MastodonBadGatewayError, MastodonInternalServerError
from dotenv import load_dotenv
import os
import random
import re
import json
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import logging
from pathlib import Path
from enum import Enum


DEBUG_MODE = False
MOCK_DAY_IDX = 0
current_day_idx = MOCK_DAY_IDX

class BracketState(Enum):
    INTRO = 1
    CHARTQ1 = 2
    POLL_Q1 = 3
    CHARTQ2 = 4
    POLL_Q2 = 5
    CHARTQ3 = 6
    POLL_Q3 = 7
    CHARTQ4 = 8
    POLL_Q4 = 9
    CHARTS1 = 10
    POLL_S1 = 11
    CHARTS2 = 12
    POLL_S2 = 13
    CHARTFI = 14
    POLL_FI = 15
    WRAP_UP = 16

# Automatically detect the directory where mars_madness.py is actually stored
SCRIPT_DIR = Path(__file__).parent.resolve()

# Force all file targets to use exact, absolute paths
ENV_FILE = SCRIPT_DIR / ".env"
STATE_FILE = SCRIPT_DIR / "bracket_state.json"
GRAPHIC_FILE = SCRIPT_DIR / "bracket.png"
LOG_FILE = SCRIPT_DIR / "mars_madness_errors.log"

# Explicitly load the .env file from its exact absolute path
load_dotenv(dotenv_path=ENV_FILE)

# Update your logging setup to point to the exact log file path
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# Only initialize Mastodon if we are in production mode
if DEBUG_MODE:
    mastodon = None
    print(
        f"🤖 RUNNING IN DEBUG MODE: Simulating Day Index {current_day_idx} (No live API calls)"
    )
else:
    current_day_idx = datetime.now().weekday()
    load_dotenv()
    mastodon = Mastodon(
        client_id=os.getenv("client_key"),
        client_secret=os.getenv("client_secret"),
        access_token=os.getenv("access_token"),
        api_base_url="https://mastodon.social",
    )

movieList = [
    "End of the World (1977)",
    "In the Year 2889 (1969)",
    "Class of 1999 (1990)",
    "Seedpeople (1992)",
    "Terror in the Wax Museum (1973)",
    "Invasion: UFO (1980)",
    "Reptilian (1999)",
    "Silver Bullet (1985)",
    "Hercules in New York (1970)",
    "Communion (1989)",
    "Son of Dracula (1943)",
    "The Monster That Challenged The World (1957)",
    "Critters 4 (1992)",
    "The Golden Voyage of Sinbad (1973)",
    "Jason and the Argonauts (1963)",
    "The Adventures of Hercules (1985)",
    "Hercules (1983)",
]

movieCriteria = [
    ["feels the ", "MOST", "LEAST", " likely to pass the Bechdel test"],
    ["feels the ", "MOST", "LEAST", " like a cash grab"],
    ["feels the ", "MOST", "LEAST", " like a ripoff of a better film"],
    ["feels the ", "MOST", "LEAST", " made-for-tv"],
    ["feels the ", "MOST", "LEAST", " outdated"],
    ["had the ", "MOST", "LEAST", " wasted potential"],
    ["has the ", "BIGGEST", "SMALLEST", " baddie"],
    ["has the ", "MOST EXPENSIVE", "CHEAPEST", " looking sets"],
    ["has the ", "MOST", "FEWEST", " deaths"],
    ["has the ", "MOST", "FEWEST", " famous actors"],
    ["has the ", "MOST", "FEWEST", " frogs"],
    ["has the ", "MOST", "FEWEST", " little guys"],
    ["has the ", "MOST", "FEWEST", " vegetarians"],
    ["has the ", "MOST", "LEAST", " B.D.E."],
    ["has the ", "MOST", "LEAST", " big dinosaur energy"],
    ["has the ", "MOST", "LEAST", " 'David Bowie' energy"],
    ["has the ", "MOST", "LEAST", " 'Vincent Price' energy"],
    ["has the ", "MOST", "LEAST", " 'castle' energy"],
    ["has the ", "MOST", "LEAST", " 'industrial' energy"],
    ["has the ", "MOST", "LEAST", " action"],
    ["has the ", "MOST", "LEAST", " amount of effort"],
    ["has the ", "MOST", "LEAST", " blood"],
    ["has the ", "MOST", "LEAST", " cheese"],
    ["has the ", "MOST", "LEAST", " coffee served"],
    ["has the ", "MOST", "LEAST", " competent hero"],
    ["has the ", "MOST", "LEAST", " consistent monster size"],
    ["has the ", "MOST", "LEAST", " conventional weapon"],
    ["has the ", "MOST", "LEAST", " convincing-looking monster"],
    ["has the ", "MOST", "LEAST", " dangerous monster"],
    ["has the ", "MOST", "LEAST", " destruction"],
    ["has the ", "MOST", "LEAST", " effective military or police"],
    ["has the ", "MOST", "LEAST", " fur"],
    ["has the ", "MOST", "LEAST", " growth"],
    ["has the ", "MOST", "LEAST", " monster screen time"],
    ["has the ", "MOST", "LEAST", " 'bird' energy"],
    ["has the ", "MOST", "LEAST", " 'bug' energy"],
    ["has the ", "MOST", "LEAST", " 'college' energy"],
    ["has the ", "MOST", "LEAST", " 'colonial' energy"],
    ["has the ", "MOST", "LEAST", " 'dad' energy"],
    ["has the ", "MOST", "LEAST", " 'Damsel in Distress' energy"],
    ["has the ", "MOST", "LEAST", " 'dragon' energy"],
    ["has the ", "MOST", "LEAST", " 'Earth' energy"],
    ["has the ", "MOST", "LEAST", " 'Florida' energy"],
    ["has the ", "MOST", "LEAST", " 'fish' energy"],
    ["has the ", "MOST", "LEAST", " 'flying' energy"],
    ["has the ", "MOST", "LEAST", " 'horse girl' energy "],
    ["has the ", "MOST", "LEAST", " 'Mad Scientist' energy"],
    ["has the ", "MOST", "LEAST", " 'plant' energy"],
    ["has the ", "MOST", "LEAST", " 'psychic' energy"],
    ["has the ", "MOST", "LEAST", " 'reptile' energy"],
    ["has the ", "MOST", "LEAST", " 'soccer mom' energy"],
    ["has the ", "MOST", "LEAST", " 'water' energy"],
    ["has the ", "MOST", "LEAST", " 'wind' energy"],
    ["has the ", "MOST", "LEAST", " abrupt ending"],
    ["has the ", "MOST", "LEAST", " aggressive Male Gaze"],
    ["has the ", "MOST", "LEAST", " annoying dialogue"],
    ["has the ", "MOST", "LEAST", " awkwardly-moving monster"],
    ["has the ", "MOST", "LEAST", " beach vibes"],
    ["has the ", "MOST", "LEAST", " boring filler scenes"],
    ["has the ", "MOST", "LEAST", " cartoonish-looking monster"],
    ["has the ", "MOST", "LEAST", " chewed scenery"],
    ["has the ", "MOST", "LEAST", " confusing geography"],
    ["has the ", "MOST", "LEAST", " confusing monster rules"],
    ["has the ", "MOST", "LEAST", " confusing plot"],
    ["has the ", "MOST", "LEAST", " crashes"],
    ["has the ", "MOST", "LEAST", " fake rocks"],
    ["has the ", "MOST", "LEAST", " fighting"],
    ["has the ", "MOST", "LEAST", " fire"],
    ["has the ", "MOST", "LEAST", " growth"],
    ["has the ", "MOST", "LEAST", " heart"],
    ["has the ", "MOST", "LEAST", " main character energy"],
    ["has the ", "MOST", "LEAST", " main character plot armor"],
    ["has the ", "MOST", "LEAST", " NASCAR energy"],
    ["has the ", "MOST", "LEAST", " nonsensical science"],
    ["has the ", "MOST", "LEAST", " plot holes"],
    ["has the ", "MOST", "LEAST", " rizz"],
    ["has the ", "MOST", "LEAST", " sandals"],
    ["has the ", "MOST", "LEAST", " toxic masculinity"],
    ["has the ", "MOST", "LEAST", " toxic vibe"],
    ["has the ", "MOST", "LEAST", " unnecessary scenes"],
    ["has the ", "MOST", "LEAST", " unnecessary slow-motion"],
    ["has the ", "MOST", "LEAST", " wood"],
    ["has the ", "FASTEST", "SLOWEST", " monster"],
    ["has the ", "BIGGEST", "SMALLEST", " baddie"],
    ["has the ", "STURDIEST", "FLIMSIEST", " looking sets"],
    ["has the ", "BEST", "WORST", " acting"],
    ["has the ", "BEST", "WORST", " characters"],
    ["has the ", "BEST", "WORST", " cinematography"],
    ["has the ", "BEST", "WORST", " costume and production design"],
    ["has the ", "BEST", "WORST", " ending"],
    ["has the ", "BEST", "WORST", " hero"],
    ["has the ", "BEST", "WORST", " monster/creature design"],
    ["has the ", "BEST", "WORST", " music and sound design"],
    ["has the ", "BEST", "WORST", " night scenes"],
    ["has the ", "BEST", "WORST", " plot twist"],
    ["has the ", "BEST", "WORST", " smell"],
    ["has the ", "BEST", "WORST", " story/script"],
    ["has the ", "BEST", "WORST", " tech"],
    ["has the ", "BEST", "WORST", " title"],
    ["has the ", "BEST", "WORST", " visual effects/CGI"],
    ["has the ", "BEST", "WORST", " weapons"],
    ["is the ", "BIGGEST", "SMALLEST", " disaster"],
    ["is the ", "MOST", "LEAST", " beefy"],
    ["is the ", "MOST", "LEAST", " chill"],
    ["is the ", "MOST", "LEAST", " complex"],
    ["is the ", "MOST", "LEAST", " dark"],
    ["is the ", "MOST", "LEAST", " David Lynch-esque"],
    ["is the ", "MOST", "LEAST", " Devil Girl From Mars-esque"],
    ["is the ", "MOST", "LEAST", " Dracula-esque"],
    ["is the ", "MOST", "LEAST", " dramatic"],
    ["is the ", "MOST", "LEAST", " epic"],
    ["is the ", "MOST", "LEAST", " erotic"],
    ["is the ", "MOST", "LEAST", " experimental"],
    ["is the ", "MOST", "LEAST", " Frankenstein-esque"],
    ["is the ", "MOST", "LEAST", " fun"],
    ["is the ", "MOST", "LEAST", " funky"],
    ["is the ", "MOST", "LEAST", " funny"],
    ["is the ", "MOST", "LEAST", " Godzilla-esque"],
    ["is the ", "MOST", "LEAST", " interesting"],
    ["is the ", "MOST", "LEAST", " kaiju-esque"],
    ["is the ", "MOST", "LEAST", " likely to become a cult classic"],
    ["is the ", "MOST", "LEAST", " memorable"],
    ["is the ", "MOST", "LEAST", " original"],
    ["is the ", "MOST", "LEAST", " patriotic"],
    ["is the ", "MOST", "LEAST", " powerful"],
    ["is the ", "MOST", "LEAST", " professional"],
    ["is the ", "MOST", "LEAST", " raucous"],
    ["is the ", "MOST", "LEAST", " rewatchable"],
    ["is the ", "MOST", "LEAST", " Roger Corman-esque"],
    ["is the ", "MOST", "LEAST", " scary"],
    ["is the ", "MOST", "LEAST", " serious"],
    ["is the ", "MOST", "LEAST", " Star Trek-esque"],
    ["is the ", "MOST", "LEAST", " Star Wars-esque"],
    ["is the ", "MOST", "LEAST", " thought-provoking"],
    ["is the ", "MOST", "LEAST", " Titanic-esque"],
    ["is the ", "MOST", "LEAST", " Twilight Zone-esque"],
    ["is the ", "MOST", "LEAST", " violent"],
    ["is the ", "MOST", "LEAST", " acidic"],
    ["is the ", "MOST", "LEAST", " adult"],
    ["is the ", "MOST", "LEAST", " American"],
    ["is the ", "MOST", "LEAST", " angsty"],
    ["is the ", "MOST", "LEAST", " annoying"],
    ["is the ", "MOST", "LEAST", " athletic"],
    ["is the ", "MOST", "LEAST", " camp"],
    ["is the ", "MOST", "LEAST", " cat-like"],
    ["is the ", "MOST", "LEAST", " cheap"],
    ["is the ", "MOST", "LEAST", " cheesy"],
    ["is the ", "MOST", "LEAST", " childish"],
    ["is the ", "MOST", "LEAST", " conservative"],
    ["is the ", "MOST", "LEAST", " cringe"],
    ["is the ", "MOST", "LEAST", " cryptic"],
    ["is the ", "MOST", "LEAST", " cursed"],
    ["is the ", "MOST", "LEAST", " destructive"],
    ["is the ", "MOST", "LEAST", " dim"],
    ["is the ", "MOST", "LEAST", " disappointing"],
    ["is the ", "MOST", "LEAST", " dreamlike"],
    ["is the ", "MOST", "LEAST", " dry"],
    ["is the ", "MOST", "LEAST", " dusty"],
    ["is the ", "MOST", "LEAST", " dystopian"],
    ["is the ", "MOST", "LEAST", " electric"],
    ["is the ", "MOST", "LEAST", " embarrassing"],
    ["is the ", "MOST", "LEAST", " fake"],
    ["is the ", "MOST", "LEAST", " fictional"],
    ["is the ", "MOST", "LEAST", " forbidden"],
    ["is the ", "MOST", "LEAST", " futuristic"],
    ["is the ", "MOST", "LEAST", " gothic"],
    ["is the ", "MOST", "LEAST", " graphic"],
    ["is the ", "MOST", "LEAST", " greasy"],
    ["is the ", "MOST", "LEAST", " hairy"],
    ["is the ", "MOST", "LEAST", " haunted"],
    ["is the ", "MOST", "LEAST", " hideous"],
    ["is the ", "MOST", "LEAST", " icy"],
    ["is the ", "MOST", "LEAST", " inspiring"],
    ["is the ", "MOST", "LEAST", " Jaws-esque"],
    ["is the ", "MOST", "LEAST", " juicy"],
    ["is the ", "MOST", "LEAST", " lazy"],
    ["is the ", "MOST", "LEAST", " liberal"],
    ["is the ", "MOST", "LEAST", " minimalist"],
    ["is the ", "MOST", "LEAST", " moist"],
    ["is the ", "MOST", "LEAST", " monsterous"],
    ["is the ", "MOST", "LEAST", " mouth-watering"],
    ["is the ", "MOST", "LEAST", " muscular"],
    ["is the ", "MOST", "LEAST", " nerdy"],
    ["is the ", "MOST", "LEAST", " noisy"],
    ["is the ", "MOST", "LEAST", " offensive"],
    ["is the ", "MOST", "LEAST", " pointless"],
    ["is the ", "MOST", "LEAST", " poisonous"],
    ["is the ", "MOST", "LEAST", " predictable"],
    ["is the ", "MOST", "LEAST", " pretentious"],
    ["is the ", "MOST", "LEAST", " psychedelic"],
    ["is the ", "MOST", "LEAST", " radioactive"],
    ["is the ", "MOST", "LEAST", " religious"],
    ["is the ", "MOST", "LEAST", " salty"],
    ["is the ", "MOST", "LEAST", " Satanic"],
    ["is the ", "MOST", "LEAST", " sharp"],
    ["is the ", "MOST", "LEAST", " sleazy"],
    ["is the ", "MOST", "LEAST", " slimy"],
    ["is the ", "MOST", "LEAST", " small"],
    ["is the ", "MOST", "LEAST", " spacey"],
    ["is the ", "MOST", "LEAST", " spicy"],
    ["is the ", "MOST", "LEAST", " sticky"],
    ["is the ", "MOST", "LEAST", " stiff"],
    ["is the ", "MOST", "LEAST", " swampy"],
    ["is the ", "MOST", "LEAST", " teen"],
    ["is the ", "MOST", "LEAST", " thirsty"],
    ["is the ", "MOST", "LEAST", " tone deaf"],
    ["is the ", "MOST", "LEAST", " tough"],
    ["is the ", "MOST", "LEAST", " transparent"],
    ["is the ", "MOST", "LEAST", " trashy"],
    ["is the ", "MOST", "LEAST", " tropical"],
    ["is the ", "MOST", "LEAST", " urban"],
    ["is the ", "MOST", "LEAST", " suburban"],
    ["is the ", "MOST", "LEAST", " punk"],
    ["is the ", "MOST", "LEAST", " jazzy"],
    ["is the ", "MOST", "LEAST", " rural"],
    ["is the ", "MOST", "LEAST", " underground"],
    ["is the ", "MOST", "LEAST", " unnecessary"],
    ["is the ", "MOST", "LEAST", " wacky"],
    ["is the ", "MOST", "LEAST", " wrong"],
    ["is the ", "MOST", "LEAST", " rhythmic"],
    ["is the ", "MOST", "LEAST", " dynamic"],
    ["is the ", "MOST", "LEAST", " energetic"],
    ["would make the ", "BEST", "WORST", " video game"],
    ["is the ", "MOST", "LEAST", " likely to get big-budget remake"],
    ["would be the ", "MOST", "LEAST", " fun to watch on a first date"],
    ["would be the ", "MOST", "LEAST", " awkward to watch with your parents"],
    ["would be the ", "MOST", "LEAST", " likely to give a child nightmares"],
    ["would be the ", "MOST", "LEAST", " fun to watch while intoxicated"],
    ["would be the ", "MOST", "LEAST", " appropriate to play at a wedding"],
    ["would be the ", "MOST", "LEAST", " appropriate to play at a funeral"],
    ["would be the ", "MOST", "LEAST", " stressful to live through in real life"],
    ["is the ", "MOST", "LEAST", " likely to be shown in a science class"],
    ["would have the ", "BEST", "WORST", " themed restaurant"],
    ["would have the ", "BEST", "WORST", " escape room theme"],
    ["would have the ", "BEST", "WORST", " fan fiction"],
    ["would have the ", "BEST", "WORST", " action figures"],
    ["would make the ", "BEST", "WORST", " Saturday morning cartoon"],
    ["would make the ", "BEST", "WORST", " Broadway musical"],
    ["would make the ", "BEST", "WORST", " roller coaster"],
    ["would make the ", "BEST", "WORST", " children's bedtime story"],
    ["would have the ", "BEST", "WORST", " breakfast cereal"],
    ["would be the ", "BEST", "WORST", " to have as a lower-back tattoo"],
    ["would be the ", "BEST", "WORST", " to have as a permanent nickname"],
    ["would be the ", "BEST", "WORST", " to be trapped inside for 24 hours"],
    ["has the ", "MOST", "LEAST", " product placement"],
    ["is the ", "MOST", "LEAST", " likely to make someone quezy"],
    ["is the ", "MOST", "LEAST", " likely to make someone cry"],
    ["is the ", "MOST", "LEAST", " likely to contain a subliminal message"],
    ["is the ", "MOST", "LEAST", " likely to be a front for a CIA experiment"],
    ["is the ", "MOST", "LEAST", " likely to be the leader of a high school club"],
    ["is the ", "MOST", "LEAST", " likely to have a theme song that actually slaps"],
    ["is the ", "MOST", "LEAST", " likely to steal your wallet"],
    ["is the ", "MOST", "LEAST", " likely to ghost you after the first date"],
    ["is the ", "MOST", "LEAST", " likely to be a pyramid scheme"],
    ["is the ", "MOST", "LEAST", " likely to be banned from a public library"],
    ["is the ", "MOST", "LEAST", " likely to become a cult classic"],
    ["is the ", "MOST", "LEAST", " likely to feature a Yeti's nipple"],
    ["is the ", "MOST", "LEAST", " likely to feature a stop motion creature"],
    ["is the ", "MOST", "LEAST", " likely to use the term 'glaive' incorrectly"],
    ["has the ", "MOST", "LEAST", " 'Dungeons and Dragons' energy"],
    ["has the ", "MOST", "LEAST", " mountain energy"],
    ["is the ", "MOST", "LEAST", " beastly"],
    ["is the ", "MOST", "LEAST", " green"],
    ["is the ", "MOST", "LEAST", " organic"],
    ["is the ", "MOST", "LEAST", " capitalist"],
    ["is the ", "MOST", "LEAST", " angry"],
    ["is the ", "MOST", "LEAST", " hungry"],
    ["is the ", "MOST", "LEAST", " godly"],
    ["is the ", "MOST", "LEAST", " manly"],
    ["has the ", "MOST", "LEAST", " midnight energy"],
    ["has the ", "MOST", "LEAST", " farm-to-table energy"],
    ["has the ", "MOST", "LEAST", " accurate title"],
    ["has the ", "MOST", "LEAST", " moth energy"],
    ["has the ", "MOST", "LEAST", " bear energy"],
    ["has the ", "MOST", "LEAST", " bat energy"],
    ["has the ", "MOST", "LEAST", " wolf energy"],
    ["is the ", "MOST", "LEAST", " goblin mode"],
    ["has the ", "MOST", "LEAST", " stars"],
    ["has the ", "MOST", "LEAST", " athletic cast"],
    ["has the ", "MOST", "LEAST", " lazer energy? pew pew"],
    ["is ", "MOST", "LEAST", " memeable"],
    ["is the ", "MOST", "LEAST", " robotic"],
    ["is the ", "MOST", "LEAST", " down-to-Earth"],
    ["has the ", "MOST", "LEAST", " creatures"],
    ["has the ", "MOST", "LEAST", " lunar energy"],
    ["is the ", "MOST", "LEAST", " family-friendly"],
    ["has the ", "MOST", "LEAST", " exotic locations"],
    ["is the ", "MOST", "LEAST", " aquatic"],
    ["has the ", "MOST", "LEAST", " mall-walker energy"],
    ["has the ", "MOST", "LEAST", " gas"],
    ["is the ", "MOST", "LEAST", " heavy metal"],
    ["is the ", "MOST", "LEAST", " hip-hop"],
    ["is the ", "MOST", "LEAST", " electronic"],
    ["has the ", "MOST", "LEAST", " folk energy"],
    ["is the ", "MOST", "LEAST", " classical"],
    ["is the ", "MOST", "LEAST", " British"],
    ["is the ", "MOST", "LEAST", " grunge"],
    ["is the ", "MOST", "LEAST", " brainy"],
    ["is the ", "MOST", "LEAST", " ballet-like"],
    ["is the ", "MOST", "LEAST", " operatic"],
    ["is the ", "MOST", "LEAST", " orchestral"],
    ["has the ", "MOST", "LEAST", " Disney energy"],
    ["has the ", "MOST", "LEAST", " epic quest"],
    ["is the ", "MOST", "LEAST", " likely to be name-dropped in a rap"],
]


def advance_state(current_state):
    """Calculates the next chronological step in the state pattern."""
    try:
        return BracketState(current_state.value + 1)
    except ValueError:
        return BracketState.INTRO

def draw_bracket_text_node(
    drawing_object,
    x,
    y,
    text,
    font,
    font_size,
    node_line_length,
    track_color,
    track_width,
    track_offset,
    title_text="???",
):
    display_text = addEllipsisIfTooLong(text or title_text, max_len=31)

    # LIGHT MODE TEXT: Dark slate for populated items, muted gray for empty slots
    color = "#111111" if text else "#888888"

    # Adjust Y offset dynamically based on font size so it sits neatly above the line
    drawing_object.line(
        [(x, y + track_offset), (x + node_line_length), (y + track_offset)],
        fill=track_color,
        width=track_width,
    )
    drawing_object.text(
        (x, y - (font_size // 2) - 4), display_text, fill=color, font=font
    )

def generate_bracket_graphic(state):
    width, height = 1200, 800

    # LIGHT MODE: Crisp cream/off-white canvas color
    img = Image.new("RGB", (width, height), color="#f4f4f0")
    draw = ImageDraw.Draw(img)

    # Font sizing control variable
    font_size = 30

    try:
        # Modern pillow syntax supporting custom default font sizes
        my_font = ImageFont.load_default(size=font_size)
    except Exception:
        # Fallback to base default font if using an older library build
        my_font = ImageFont.load_default()

    # Increased line length from 180 to 260 to give titles room and spread the layout
    node_line_length = 260
    track_color = "#ffddff"
    track_width = 20
    track_offset = 22

    match_list = state["matches"]

    # BORDER BOX
    border_track_width = track_width * 2
    # north border
    draw.line([(0, 0), (1200, 0)], fill=track_color, width=border_track_width)
    # east border
    draw.line([(1200, 0), (1200, 800) ],fill=track_color,width=border_track_width)
    # south border
    draw.line([(0, 800), (1200, 800)],fill=track_color,width=border_track_width)
    # west border
    draw.line([(0, 0), (0, 800)],fill=track_color,width=border_track_width)

    # CONNECTING LINES (Recalculated paths to bridge the new node coordinates seamlessly)
   
    # Q1 & Q2 -> S1 Lines (From end of Col 1 line [60 + 260 = 320] to start of Col 2 [450])
    # draw.line(
    #     [(320, 110), (385, 110), (385, 190), (450, 190)], fill=track_color, width=track_width
    # )
    draw.line([(60 + 260, height * 3/17 + track_offset), (60 + 260 + 60, height * 4/17 + track_offset)], fill=track_color, width=track_width)
    # draw.line(
    #     [(320, 330), (385, 330), (385, 250), (450, 250)], fill=track_color, width=track_width
    # )
    draw.line([(60 + 260 , height * 6/17 + track_offset), (60 + 260 + 60, height * 5/17 + track_offset)], fill=track_color, width=track_width)

    # Q3 & Q4 -> S2 Lines (From end of Col 1 line [320] to start of Col 2 [450])
    # draw.line(
    #     [(320, 470), (385, 470), (385, 550), (450, 550)], fill=track_color, width=track_width
    # )
    draw.line([(60 + 260 , height * 11/17 + track_offset), (60 + 260 + 60, height * 12/17 + track_offset)], fill=track_color, width=track_width)
    # draw.line(
    #     [(320, 690), (385, 690), (385, 610), (450, 610)], fill=track_color, width=track_width
    # )
    draw.line([(60 + 260 , height * 14/17 + track_offset), (60 + 260 + 60, height * 13/17 + track_offset)], fill=track_color, width=track_width)

    # S1 & S2 -> Finals Lines (From end of Col 2 line [450 + 260 = 710] to start of Col 3 [840])
    # draw.line(
    #     [(710, 190), (775, 190), (775, 370), (840, 370)], fill=track_color, width=track_width
    # )
    draw.line([(60 + 260 + 60 + 260 , height * 5/17 + track_offset), (60 + 260 + 60 + 260 + 60, height * 8/17 + track_offset)], fill=track_color, width=track_width)
    # draw.line(
    #     [(710, 610), (775, 610), (775, 430), (840, 430)], fill=track_color, width=track_width
    # )
    draw.line([(60 + 260 + 60 + 260 , height * 12/17 + track_offset), (60 + 260 + 60 + 260 + 60, height * 9/17 + track_offset)], fill=track_color, width=track_width)

    # --- ADJUSTED HORIZONTAL SPACING MAP ---
    # Col 1 (Quarterfinals) X = 60
    # Col 2 (Semifinals)    X = 450  (60 + 260 line length + 130 connector gap)
    # Col 3 (Finals)        X = 840  (450 + 260 line length + 130 connector gap)
    # Right-most edge ends cleanly near X = 1100 (leaving a nice 100px right margin)

    text_nodes = [
        # QUARTERFINALS (Col 1: X = 60)
        {"x": 60, "y": height *  2/17, "text": match_list["0"]["home"], "title_text": "Seed 1"},
        {"x": 60, "y": height *  3/17, "text": match_list["0"]["away"], "title_text": "Seed 8"},
        {"x": 60, "y": height *  6/17, "text": match_list["1"]["home"], "title_text": "Seed 4"},
        {"x": 60, "y": height *  7/17, "text": match_list["1"]["away"], "title_text": "Seed 5"},
        {"x": 60, "y": height * 10/17, "text": match_list["2"]["home"], "title_text": "Seed 2"},
        {"x": 60, "y": height * 11/17, "text": match_list["2"]["away"], "title_text": "Seed 7"},
        {"x": 60, "y": height * 14/17, "text": match_list["3"]["home"], "title_text": "Seed 3"},
        {"x": 60, "y": height * 15/17, "text": match_list["3"]["away"], "title_text": "Seed 6"},
        # SEMIFINALS (Col 2: X = 450)
        {
            "x": 60 + 260 + 60,
            "y": height * 4/17,
            "text": match_list["4"]["home"],
            "title_text": "Winner Q1",
        },
        {
            "x": 60 + 260 + 60,
            "y": height * 5/17,
            "text": match_list["4"]["away"],
            "title_text": "Winner Q2",
        },
        {
            "x": 60 + 260 + 60,
            "y": height * 12/17,
            "text": match_list["5"]["home"],
            "title_text": "Winner Q3",
        },
        {
            "x": 60 + 260 + 60,
            "y": height * 13/17,
            "text": match_list["5"]["away"],
            "title_text": "Winner Q4",
        },
        # FINALS (Col 3: X = 840)
        {
            "x": 60 + 260 + 60 + 260 + 60,
            "y": height * 8/17,
            "text": match_list["6"]["home"],
            "title_text": "Winner S1",
        },
        {
            "x": 60 + 260 + 60 + 260 + 60,
            "y": height * 9/17,
            "text": match_list["6"]["away"],
            "title_text": "Winner S2",
        },
    ]

    for each in text_nodes:
        # draw_bracket_text_node(drawing_object, x, y, text, font, font_size, node_line_length, track_color, track_width, title_text="???")
        draw_bracket_text_node(
            draw,
            each["x"],
            each["y"],
            each["text"],
            my_font,
            font_size,
            node_line_length,
            track_color,
            track_width,
            track_offset,
            each["title_text"],
        )

    # Darker Midnight Blue Header text for striking contrast
    draw.text(
        (1200 - 40, height * 1/17),
        f"MARS MADNESS BRACKET: WEEK OF {state['week_start']}",
        fill="black",
        font=my_font,
        anchor="rm",
    )

    img.save(GRAPHIC_FILE)

    # DYNAMIC ALT TEXT GENERATION
    alt_text = (
        f"Mars Madness Tournament Bracket Chart for the week of {state['week_start']}. "
    )
    alt_text += f"Quarterfinals: 1) {match_list['0']['home'] or 'Seed 1'} vs {match_list['0']['away'] or 'Seed 8'}. "
    alt_text += f"2) {match_list['1']['home'] or 'Seed 4'} vs {match_list['1']['away'] or 'Seed 5'}. "
    alt_text += f"3) {match_list['2']['home'] or 'Seed 2'} vs {match_list['2']['away'] or 'Seed 7'}. "
    alt_text += f"4) {match_list['3']['home'] or 'Seed 3'} vs {match_list['3']['away'] or 'Seed 6'}. "
    alt_text += f"Semifinals: Match 1 has {match_list['4']['home'] or 'Winner Q1'} vs {match_list['4']['away'] or 'Winner Q2'}. "
    alt_text += f"Match 2 has {match_list['5']['home'] or 'Winner Q3'} vs {match_list['5']['away'] or 'Winner Q4'}. "
    alt_text += f"Finals: {match_list['6']['home'] or 'Winner S1'} vs {match_list['6']['away'] or 'Winner S2'}."

    return alt_text


def get_random_question():
    template = random.choice(movieCriteria)
    polarity = random.choice([template[1], template[2]])
    return f"Which movie {template[0]}{polarity}{template[3]}?"


def getMovieHashtag(titleParenthesesDate):
    clean_title = re.sub(r"[^a-zA-Z0-9]", "", titleParenthesesDate)
    return f"#{clean_title}"


def addEllipsisIfTooLong(word, max_len=50):
    if len(word) > max_len:
        word = word[: max_len - 1] + "…"
    return word


def get_poll_winner(poll_id, match_details):
    if DEBUG_MODE:
        simulated_winner = random.choice([match_details["home"], match_details["away"]])
        print(f"🔮 [DEBUG] Simulating winner for poll {poll_id}: {simulated_winner}")
        return simulated_winner

    try:
        status = mastodon.status(poll_id)
        poll = status.get("poll")
        if not poll:
            return None

        # 🚨 SAFETY CHECK: If the poll is still active, do NOT tally the votes yet!
        if not poll.get("expired", False):
            print(f"⚠️ Warning: Poll {poll_id} is still open. Waiting until it closes.")
            return None

        options = poll["options"]
        if options[0]["votes_count"] >= options[1]["votes_count"]:
            return options[0]["title"]
        else:
            return options[1]["title"]
    except Exception as e:
        print(f"Error fetching poll winner: {e}")
        return None


def initialize_new_bracket():
    """Initializes a new bracket layout on Monday using the last 8 unique movies."""
    # "Last 8 films in chronological order with the most recent being the 1 seed"
    # Assuming your movieList is already ordered chronologically (oldest to newest),
    # the last 8 items represent the most recent. We reverse it so index 0 is the 1 seed.
    recent_movies = list(movieList[:8])

    # Standard 8-team bracket seed matching: 1v8, 4v5, 2v7, 3v6
    state = {
        "current_state": BracketState.INTRO.name,
        "previous_status_id": None,
        "week_start": datetime.now().strftime("%Y-%m-%d"),
        "matches": {
            "0": {
                "home": recent_movies[0],
                "away": recent_movies[7],
                "poll_id": None,
                "winner": None,
                "label": "Quarterfinal 1",
            },  # Monday
            "1": {
                "home": recent_movies[3],
                "away": recent_movies[4],
                "poll_id": None,
                "winner": None,
                "label": "Quarterfinal 2",
            },  # Tuesday
            "2": {
                "home": recent_movies[1],
                "away": recent_movies[6],
                "poll_id": None,
                "winner": None,
                "label": "Quarterfinal 3",
            },  # Wednesday
            "3": {
                "home": recent_movies[2],
                "away": recent_movies[5],
                "poll_id": None,
                "winner": None,
                "label": "Quarterfinal 4",
            },  # Thursday
            "4": {
                "home": None,
                "away": None,
                "poll_id": None,
                "winner": None,
                "label": "Semifinal 1",
            },  # Friday (Winner Q1 vs Winner Q2)
            "5": {
                "home": None,
                "away": None,
                "poll_id": None,
                "winner": None,
                "label": "Semifinal 2",
            },  # Saturday (Winner Q3 vs Winner Q4)
            "6": {
                "home": None,
                "away": None,
                "poll_id": None,
                "winner": None,
                "label": "Finals",
            },  # Sunday (Winner S1 vs Winner S2)
        },
    }
    return state


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None

def post_monday_wrapup(state):
    print("Processing Monday wrap-up before resetting the tournament slate...")
    final_match = state["matches"].get("6")

    if final_match and final_match.get("poll_id"):
        champion = final_match.get("winner")
        if not champion:
            champion = get_poll_winner(final_match["poll_id"], final_match)

        if champion:
            week_label = state.get("week_start", "Current Week")
            announcement_text = f"🏆🥇 MARS MADNESS CHAMPION 🥇🏆\nfor the week of {week_label} is...\n{champion}\nThanks for voting!\n\n#MarsMadness"

            try:
                print(f"Replying to the last post with championship announcement...")
                if not DEBUG_MODE:
                    mastodon.status_post(
                        status=announcement_text,
                        in_reply_to_id=state.get("previous_status_id") or final_match["poll_id"], 
                        visibility="public",
                    )
            except Exception as api_err:
                logging.error(f"Failed to post championship announcement reply: {api_err}", exc_info=True)

def process_chart_stage(state, match_key):
    """Generates the bracket update image and replies directly to the immediate previous post."""
    match = state["matches"][match_key]
    match_label = match["label"].upper()
    week_label = state.get("week_start", "Current Week")

    try:
        generated_alt_text = generate_bracket_graphic(state)
    except Exception as e:
        logging.error(f"Failed to generate bracket image asset: {e}", exc_info=True)
        generated_alt_text = "Mars Madness tournament bracket update."

    reply_text = f"😈✨ MARS MADNESS BRACKET ✨😈\nfor {match_label}\nweek of {week_label}"

    if DEBUG_MODE:
        print(f"[DEBUG] Simulated Chronological Chart Post for {match_label}")
        return True

    for attempt in range(3):
        try:
            media_dict = mastodon.media_post(
                media_file=GRAPHIC_FILE,
                mime_type="image/png",
                description=generated_alt_text,
            )
            
            # Linear chaining rule: Always reply to the immediate past piece of content
            target_reply_id = state.get("previous_status_id")

            status_response = mastodon.status_post(
                status=reply_text,
                in_reply_to_id=target_reply_id, 
                media_ids=[media_dict["id"]],
                visibility="public",
            )
            
            # Update the rolling position placeholder
            state["previous_status_id"] = status_response["id"]
            return True
        except (MastodonBadGatewayError, MastodonInternalServerError) as server_err:
            print(f"⚠️ Gateway Error ({server_err.status_code}) on graphic. Retrying in 10s...")
            time.sleep(10)
        except Exception as e:
            logging.error(f"Fatal exception during chart attachment step: {e}", exc_info=True)
            break
    return False

def process_poll_stage(state, match_key, expires_in_seconds, emojis):
    """Calculates dependencies, parses titles, and publishes the voting poll card."""
    match = state["matches"][match_key]
    
    # Run dynamic missing candidate resolution fallbacks
    if not match["home"] or not match["away"]:
        fallback_movies = random.sample(movieList, 2)
        if not match["home"]: match["home"] = fallback_movies[0]
        if not match["away"]: match["away"] = fallback_movies[1]

    movie1 = addEllipsisIfTooLong(match["home"])
    movie2 = addEllipsisIfTooLong(match["away"])

    e1, e2 = random.sample(emojis, 2)
    match_label = match["label"].upper()

    post_text = (
        f"{e1}{e2} MARS MADNESS POLL {e2}{e1}\n{match_label}\n"
        f"{get_random_question()}\n\n"
        f"#monsterdon #MarsMadness {getMovieHashtag(movie1)} {getMovieHashtag(movie2)}"
    )

    if DEBUG_MODE:
        print(f"[DEBUG] Simulated Poll Post Deployment:\n{post_text}")
        match["poll_id"] = random.randint(100000, 999999)
        return True

    for attempt in range(3):
        try:
            poll = mastodon.make_poll(options=[movie1, movie2], expires_in=expires_in_seconds, multiple=False)
            
            # Linear chaining rule: Always reply to the immediate past piece of content
            target_reply_id = state.get("previous_status_id")

            status_response = mastodon.status_post(
                status=post_text, 
                poll=poll, 
                in_reply_to_id=target_reply_id, 
                visibility="public"
            )
            
            match["poll_id"] = status_response["id"]
            
            # Update the rolling position placeholder
            state["previous_status_id"] = status_response["id"]
            return True
        except (MastodonBadGatewayError, MastodonInternalServerError) as server_err:
            print(f"⚠️ Gateway Error ({server_err.status_code}) on poll. Retrying in 10s...")
            time.sleep(10)
        except Exception as e:
            logging.error(f"Fatal error deploying poll entity: {e}", exc_info=True)
            break
    return False

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)






def main():
    emojis = ["🚨", "🧟", "👾", "👺", "☢️", "💀", "🦇", "🏚️", "🧪", "🎥", "🔥", "🎬", "🎞️", "🍿", "🧛", "🛸", "🤢", "🩸", "😱", "👻", "👽", "🎃", "👹"]

    # 1. Load context state
    try:
        state = load_state()
        if state is None:
            state = initialize_new_bracket()
        
        current_state = BracketState[state.get("current_state", BracketState.INTRO.name)]
    except Exception as e:
        logging.error(f"FSM Context Resolution Lifecycle Error: {e}", exc_info=True)
        return

    # 2. Automatically check and populate tournament results from previous days
    for m_id, match in state["matches"].items():
        if match["poll_id"] and not match["winner"]:
            winner = get_poll_winner(match["poll_id"], match)
            if winner:
                match["winner"] = winner
                print(f"Resolved {match['label']}: Winner is {winner}")

    if state["matches"]["0"]["winner"]: state["matches"]["4"]["home"] = state["matches"]["0"]["winner"]
    if state["matches"]["1"]["winner"]: state["matches"]["4"]["away"] = state["matches"]["1"]["winner"]
    if state["matches"]["2"]["winner"]: state["matches"]["5"]["home"] = state["matches"]["2"]["winner"]
    if state["matches"]["3"]["winner"]: state["matches"]["5"]["away"] = state["matches"]["3"]["winner"]
    if state["matches"]["4"]["winner"]: state["matches"]["6"]["home"] = state["matches"]["4"]["winner"]
    if state["matches"]["5"]["winner"]: state["matches"]["6"]["away"] = state["matches"]["5"]["winner"]

    # 3. Dynamic target time math (Closes at 17:59:50 tomorrow minus now)
    now = datetime.now()
    target_today = now.replace(hour=17, minute=59, second=50, microsecond=0)
    target_time = target_today + timedelta(days=1)
    expires_in_seconds = max(1, int((target_time - now).total_seconds()))

    # 4. Map the days of the week to their allowed execution states
    weekday = datetime.now().weekday()  # Monday = 0, Tuesday = 1, etc.
    
    # Define which states are allowed to run on which days
    day_schedules = {
        0: [BracketState.WRAP_UP, BracketState.INTRO, BracketState.CHARTQ1, BracketState.POLL_Q1], # Monday
        1: [BracketState.CHARTQ2, BracketState.POLL_Q2],                                          # Tuesday
        2: [BracketState.CHARTQ3, BracketState.POLL_Q3],                                          # Wednesday
        3: [BracketState.CHARTQ4, BracketState.POLL_Q4],                                          # Thursday
        4: [BracketState.CHARTS1, BracketState.POLL_S1],                                          # Friday
        5: [BracketState.CHARTS2, BracketState.POLL_S2],                                          # Saturday
        6: [BracketState.CHARTFI, BracketState.POLL_FI]                                           # Sunday
    }
    
    allowed_states = day_schedules.get(weekday, [])

    print(f"--- Running FSM Loop for Weekday {weekday} ---")
    
    # 5. Continuous Loop: Run through states sequentially if they belong to today's schedule
    while current_state in allowed_states:
        print(f"Processing State: {current_state.name} ({current_state.value})")
        success = False

        if current_state == BracketState.INTRO:
            # Intro is a structural pass-through state; it clears/sets up variables and passes
            success = True

        # --- QUARTERFINALS MATCH STAGES ---
        elif current_state == BracketState.CHARTQ1: success = process_chart_stage(state, "0")
        elif current_state == BracketState.POLL_Q1:  success = process_poll_stage(state, "0", expires_in_seconds, emojis)
        elif current_state == BracketState.CHARTQ2: success = process_chart_stage(state, "1")
        elif current_state == BracketState.POLL_Q2:  success = process_poll_stage(state, "1", expires_in_seconds, emojis)
        elif current_state == BracketState.CHARTQ3: success = process_chart_stage(state, "2")
        elif current_state == BracketState.POLL_Q3:  success = process_poll_stage(state, "2", expires_in_seconds, emojis)
        elif current_state == BracketState.CHARTQ4: success = process_chart_stage(state, "3")
        elif current_state == BracketState.POLL_Q4:  success = process_poll_stage(state, "3", expires_in_seconds, emojis)

        # --- SEMIFINALS STAGES ---
        elif current_state == BracketState.CHARTS1: success = process_chart_stage(state, "4")
        elif current_state == BracketState.POLL_S1:  success = process_poll_stage(state, "4", expires_in_seconds, emojis)
        elif current_state == BracketState.CHARTS2: success = process_chart_stage(state, "5")
        elif current_state == BracketState.POLL_S2:  success = process_poll_stage(state, "5", expires_in_seconds, emojis)

        # --- CHAMPIONSHIP FINALS STAGES ---
        elif current_state == BracketState.CHARTFI: success = process_chart_stage(state, "6")
        elif current_state == BracketState.POLL_FI:  success = process_poll_stage(state, "6", expires_in_seconds, emojis)
        
        # --- WRAP UP / RESET ---
        elif current_state == BracketState.WRAP_UP:
            post_monday_wrapup(state)
            print("Resetting bracket records completely for the new week...")
            
            # Wipes variables and returns a fresh slate dictionary
            new_state = initialize_new_bracket()
            state.clear()
            state.update(new_state)
            
            # Manually step to INTRO to let the loop continue processing Monday states
            current_state = BracketState.INTRO
            state["current_state"] = current_state.name
            save_state(state)
            continue  # Re-evaluate loop with INTRO state

        # If a state action finishes successfully, advance the state machine immediately
        if success:
            next_state = advance_state(current_state)
            print(f"State {current_state.name} completed. Advancing to: {next_state.name}")
            
            # Update pointers
            current_state = next_state
            state["current_state"] = current_state.name
            
            # Save progress mid-run in case a subsequent network call fails
            try:
                save_state(state)
            except Exception as e:
                logging.error(f"Failed mid-loop state file write: {e}", exc_info=True)
                break
        else:
            print(f"❌ State execution failed or paused at {current_state.name}. Breaking sequence loop.")
            break

    print(f"Finished schedule loop for today. Current retained machine state: {current_state.name}")

if __name__ == "__main__":
    main()
    # generate_bracket_graphic(load_state())
