"""
Configuration for Firecrawl service with Wikipedia-specific settings
"""

# Firecrawl scraping options for Wikipedia
WIKIPEDIA_SCRAPE_OPTIONS = {
    'formats': ['html', 'markdown'],
    'onlyMainContent': True,  # Focus on main content
    'includeHtml': True,      # Include HTML for infobox parsing
    'includeRawHtml': True,   # Include raw HTML structure
    'waitFor': 1000,          # Wait for page to load
    'headers': {
        'User-Agent': 'Mozilla/5.0 (compatible; ItemResearchBot/1.0)'
    }
}

# Search options for Wikipedia
WIKIPEDIA_SEARCH_OPTIONS = {
    'limit': 5,
    'includeDomains': ['wikipedia.org'],
    'excludeDomains': ['wiktionary.org', 'wikiquote.org']
}

# Infobox parsing configuration
INFOBOX_CONFIG = {
    'games': {
        'target_classes': [
            'infobox ib-video-game hproduct',
            'infobox ib-video-game',
            'infobox hproduct',
            'infobox-video-game',
            'infobox videogame'
        ],
        'key_fields': {
            'developer': ['developer', 'developed by', 'studio'],
            'genre': ['genre', 'type'],
            'release': ['release', 'published', 'date'],
            'platform': ['platform', 'system'],
            'publisher': ['publisher']
        }
    },
    'sports': {
        'target_classes': [
            'infobox biography vcard',
            'infobox football biography',
            'infobox basketball biography'
        ],
        'key_fields': {
            'born': ['born', 'birth date'],
            'team': ['current team', 'club', 'team'],
            'position': ['position', 'playing position'],
            'career': ['career', 'active years']
        }
    },
    'music': {
        'target_classes': [
            'infobox musical artist',
            'infobox album',
            'infobox single'
        ],
        'key_fields': {
            'genre': ['genre', 'genres', 'style'],
            'formed': ['formed', 'active', 'career'],
            'label': ['label', 'record label'],
            'origin': ['origin', 'location']
        }
    }
}