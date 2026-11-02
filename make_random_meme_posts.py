import os
import random
from mastodon import Mastodon
from dotenv import load_dotenv
from shared_utils import (
    load_sentences, 
    save_sentences, 
    update_history, 
    select_random_image,
    make_image, 
    build_alt_text
)

# 1. SETUP & CONFIGURATION
load_dotenv()

# Initialize Mastodon connection
# Using the same credentials as your previous main.py
mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social",
    request_timeout=40
)

def run_random_meme_post():
    """
    Selects a sentence from the local pool, creates a meme, 
    posts it, and logs the source/result to history.
    """
    
    # LOAD THE SENTENCE POOL
    # This reads the possible_sentences.json populated by your scraper
    pool = load_sentences()
    
    if not pool:
        print("DEBUG: The sentence pool is empty. Please run the scraper script.")
        return False

    # SELECT AND REMOVE A SENTENCE
    # We pick one at random to use for the post
    selection = random.choice(pool)
    sentence = selection['sentence']
    source_url = selection['url']
    
    # Remove it immediately so it isn't picked again by another process
    pool.remove(selection)
    save_sentences(pool)

    print(f"DEBUG: Selected sentence: {sentence[:50]}...")

    try:
        image_path = select_random_image()

        # Render the image passing the selected path and sentence
        png_path = make_image(
            image_path=image_path,
            user_text=sentence
        )

        # Build alt text (uses default DevilGirl subject description)
        alt_text = build_alt_text(sentence)

        # UPLOAD MEDIA & POST TO MASTODON
        print("DEBUG: Uploading media...")
        with open(png_path, "rb") as f:
            media = mastodon.media_post(
                f, 
                mime_type='image/png', 
                description=alt_text
            )
            media_id = media["id"]

        print("DEBUG: Sending status post...")
        response = mastodon.status_post(
            status=sentence,
            media_ids=[media_id],
            visibility="public"
        )
        
        meme_url = response.get("url") or response.get("uri")
        print(f"SUCCESS: Post live at {meme_url}")

        # LOG TO SHARED HISTORY
        # Stores the sentence, original toot URL, and your new meme URL
        update_history(
            text=sentence,
            source_url=source_url,
            meme_url=meme_url
        )
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: Failed to create or post random meme: {e}")
        # If the post failed, we don't put the sentence back in the pool 
        # to prevent broken sentences from looping, but you could 
        # choose to append it back if the error was just a network timeout.
        return False

if __name__ == "__main__":
    run_random_meme_post()