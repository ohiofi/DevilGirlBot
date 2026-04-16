# devil girl bot logic explained

## reply to at-mentions

load_dotenv()
connect to mastodon

load_last_seen_id()
process_mentions(last_seen_id)

if not mentions:
    - return last_seen_id

if mentions:
    - Process oldest mention first
    - skip if user is banned
    - skip if post contains banned words
    - 1% chance to randomly skip 
    - if mention contains a keyword
    - if not mention contains keyword
        - extract clean text
        - remove all at mentions
        - skip if length > 255
        - makeReply
        - save_last_seen_id(last_seen_id)

## make random meme posts

load_dotenv()
connect to mastodon

getText()

makePost()


## previous posts format

[
  {
    "text": "The real horror is the friends we made along the way",
    "source_url": "https://mastodon.social/@user/11223344",
    "meme_post_url": "https://mastodon.social/@DevilGirlBot/99887766"
  }
]