import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.web_research.firecrawl_metadata_service import firecrawl_metadata_service

async def test_wikipedia_parsing():
    """Test Wikipedia parsing with known examples"""
    
    test_cases = [
        {
            'name': 'Call of Duty 2',
            'category': 'games',
            'subcategory': 'video_games',
            'expected_url': 'https://en.wikipedia.org/wiki/Call_of_Duty_2',
            'expected_fields': ['description', 'group', 'item_year', 'image_url']
        },
        {
            'name': 'The Legend of Zelda: Breath of the Wild',
            'category': 'games',
            'subcategory': 'video_games',
            'expected_fields': ['description', 'group', 'item_year']
        },
        {
            'name': 'Dishonored',
            'category': 'games',
            'subcategory': 'video_games',
            'expected_fields': ['description', 'group', 'item_year']
        }
    ]
    
    print("🧪 Testing Wikipedia Infobox Parsing")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        print(f"Category: {test_case['category']}/{test_case['subcategory']}")
        
        try:
            result = await firecrawl_metadata_service.search_wikipedia_metadata(
                name=test_case['name'],
                category=test_case['category'],
                subcategory=test_case['subcategory']
            )
            
            if result.get('success', False):
                metadata = result.get('metadata', {})
                reference_url = result.get('reference_url')
                parsing_method = metadata.get('_parsing_method', 'unknown')
                
                print(f"✅ SUCCESS")
                print(f"   Reference URL: {reference_url}")
                print(f"   Parsing Method: {parsing_method}")
                print(f"   Fields Found: {list(metadata.keys())}")
                
                # Check expected fields
                missing_fields = []
                for field in test_case['expected_fields']:
                    if field in metadata and metadata[field]:
                        print(f"   ✓ {field}: {metadata[field]}")
                    else:
                        missing_fields.append(field)
                        print(f"   ✗ {field}: NOT FOUND")
                
                if missing_fields:
                    print(f"   ⚠️  Missing: {missing_fields}")
                
                # Show image URL if found
                if metadata.get('image_url'):
                    print(f"   🖼️  Image: {metadata['image_url']}")
                
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ FAILED: {error}")
                
        except Exception as e:
            print(f"💥 ERROR: {e}")
        
        print("-" * 40)
    
    print("\n🏁 Test completed!")

async def test_direct_url_scraping():
    """Test direct URL scraping with known Wikipedia page"""
    
    print("\n🔍 Testing Direct URL Scraping")
    print("=" * 40)
    
    test_url = "https://en.wikipedia.org/wiki/Call_of_Duty_2"
    
    try:
        from services.web_research.firecrawl_base_service import firecrawl_base_service
        
        print(f"Scraping: {test_url}")
        
        scrape_result = await firecrawl_base_service.scrape_url(
            test_url, 
            formats=['html', 'markdown']
        )
        
        if scrape_result.get('success', False):
            content = scrape_result.get('content', '')
            print(f"✅ Content scraped: {len(content)} characters")
            
            # Check for infobox presence
            if 'infobox' in content.lower():
                print("✅ Infobox found in content")
                
                # Count infobox occurrences
                infobox_count = content.lower().count('infobox')
                print(f"   Infobox mentions: {infobox_count}")
                
                # Check for specific game infobox classes
                if 'ib-video-game' in content:
                    print("✅ ib-video-game class found")
                if 'hproduct' in content:
                    print("✅ hproduct class found")
                
            else:
                print("❌ No infobox found in content")
            
            # Check for image
            if 'upload.wikimedia.org' in content:
                print("✅ Wikimedia images found")
                import re
                images = re.findall(r'https://upload\.wikimedia\.org/[^\s\]"]+\.(?:jpg|jpeg|png|gif)', content)
                print(f"   Images found: {len(images)}")
                if images:
                    print(f"   First image: {images[0]}")
            
        else:
            error = scrape_result.get('error', 'Unknown error')
            print(f"❌ Scraping failed: {error}")
            
    except Exception as e:
        print(f"💥 Direct scraping error: {e}")

async def main():
    """Run all tests"""
    if not firecrawl_metadata_service._service_available:
        print("❌ Firecrawl service not available - check FIRECRAWL_API_KEY")
        return
    
    await test_direct_url_scraping()
    await test_wikipedia_parsing()

if __name__ == "__main__":
    asyncio.run(main())