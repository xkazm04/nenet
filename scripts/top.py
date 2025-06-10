game_prompt ="""
Please research the following item metadata for a video game item:
Name: "The Elder Scrolls V: Skyrim"

Please provide exact metadata object with year, reference URL to wikipedia page, and image URL from wikipedia page if available.:
{
    "status": "success",
    "item_year": "2011",
    "group": "Action role-playing", # Genre
    "reference_url": "https://en.wikipedia.org/wiki/The_Elder_Scrolls_V:_Skyrim",
    "image_url": "https://upload.wikimedia.org/wikipedia/en/5/56/The_Elder_Scrolls_V_Skyrim_cover.png",
}

Enum with possible values for group:
- Shooter, cRPG, jRPG, Action, Sports, MOBA, Mech, RPG, Horro, Fighting, Royale, Strategy, Adventure, MMORPG, RTS, Hero Shooter, Metroidvania, Stealth, Puzzle, Sandbox, Rogue, Souls, Survival, Card


If no information can be found, return an empty object with the following structure:
{
    "status": "failed"
}
"""

player_prompt = """
Please research the following item metadata for a sports player:
Name: "Lionel Messi"
Category: sports - football

Please provide exact metadata object with year, reference URL to wikipedia page, and image URL from wikipedia page if available.:
{
    "status": "success",
    "item_year": "1997", # Start of the player's professional career
    "item_year_to": "2025", # Assuming current year for ongoing career
    "reference_url": "https://en.wikipedia.org/wiki/Lionel_Messi",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Lionel_Messi_20180626.jpg",
    "group": "FC Barcelona", # Current or most notable team
}

If no information can be found, return an empty object with the following structure:
{
    "status": "failed"
}
"""