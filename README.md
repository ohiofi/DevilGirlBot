# DevilGirlBot

[https://mastodon.social/@devilgirlbot@mastodon.social](https://mastodon.social/@devilgirlbot@mastodon.social)

A Mastodon bot that generates memes (more specifically, image macros) and replies to mentions

This bot is a series of Python scripts:

- scrape_toots_to_pool: finds valid sentences
- make_random_meme_posts: grabs a random sentance from the pool, generates an image macro meme, posts it
- reply_to_at_mentions: takes the at mention text, generates an image macro meme, posts it as a reply
- marsMadness: generates a random poll question
- monsterdon_census: counts toots, unique users, likes, boosts, etc
- devil_in_the_details: generates charts

Uses [snowclones](https://en.wikipedia.org/wiki/Snowclone) inspired by [Tracery](https://github.com/galaxykate/tracery)