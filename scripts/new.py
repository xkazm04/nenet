import google.generativeai as genai
import os
import json
import argparse
import re
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from supabase import create_client, Client

## python scripts/new.py --name "Lionel Messi" --category "sports"  --subcategory "football"
## opravit subkategorii u fotbalu
## vytvořit si batch soubor

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing required Supabase environment variables")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

class WikiDBUpdater:
    """Enhanced wiki script that updates/creates items in Supabase database"""
    
    def __init__(self):
        self.setup_gemini()
        self.supabase = supabase
        
    def setup_gemini(self):
        """Initialize Gemini API"""
        try:
            api_key = os.environ['GOOGLE_API_KEY']
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
            print("✅ Gemini API configured successfully")
        except KeyError:
            print("🔴 ERROR: GOOGLE_API_KEY environment variable not set.")
            exit()
        except Exception as e:
            print(f"🔴 ERROR: Could not configure Gemini API: {e}")
            exit()
    
    def clean_json_response(self, text: str) -> str:
        """Clean JSON response by removing comments and markdown formatting"""
        # Remove markdown code block markers
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()
        
        # Remove // comments from JSON
        # This regex matches // comments but not URLs (which have //)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Find // that are not part of URLs
            # Look for // that are not preceded by http: or https:
            comment_match = re.search(r'(?<!:)//.*$', line)
            if comment_match:
                # Remove the comment part
                line = line[:comment_match.start()].rstrip()
                # Remove trailing comma if it exists after removing comment
                line = re.sub(r',\s*$', '', line)
            cleaned_lines.append(line)
        
        # Join lines back
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove any trailing commas before closing braces/brackets
        cleaned_text = re.sub(r',(\s*[}\]])', r'\1', cleaned_text)
        
        return cleaned_text.strip()
    
    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from Gemini response with improved error handling"""
        try:
            print(f"📄 Raw response preview: {response_text[:200]}...")
            
            # Clean the response
            cleaned_text = self.clean_json_response(response_text)
            print(f"🧹 Cleaned text preview: {cleaned_text[:200]}...")
            
            # Method 1: Try to parse the cleaned text directly
            try:
                data = json.loads(cleaned_text)
                print(f"✅ Successfully parsed JSON (direct method): {data}")
                return data
            except json.JSONDecodeError as e:
                print(f"⚠️ Direct parsing failed: {e}")
            
            # Method 2: Extract JSON blocks with better logic
            json_blocks = []
            brace_count = 0
            start_pos = -1
            
            for i, char in enumerate(cleaned_text):
                if char == '{':
                    if brace_count == 0:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos != -1:
                        json_block = cleaned_text[start_pos:i+1]
                        json_blocks.append(json_block)
                        start_pos = -1
            
            # Try to parse each JSON block
            for json_block in json_blocks:
                try:
                    # Additional cleaning for the specific block
                    json_block = re.sub(r',(\s*[}\]])', r'\1', json_block)  # Remove trailing commas
                    data = json.loads(json_block)
                    print(f"✅ Successfully parsed JSON (block method): {data}")
                    return data
                except json.JSONDecodeError as e:
                    print(f"⚠️ Block parsing failed: {e}")
                    print(f"Failed block: {json_block}")
                    continue
            
            # Method 3: Try to manually extract key-value pairs if JSON parsing fails
            print("⚠️ Attempting manual extraction...")
            return self.manual_json_extraction(cleaned_text)
            
        except Exception as e:
            print(f"🔴 Error in JSON extraction: {e}")
            return None
    
    def manual_json_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """Manually extract data from JSON-like text when parsing fails"""
        try:
            data = {}
            
            # Extract key patterns
            patterns = {
                'status': r'"status":\s*"([^"]*)"',
                'item_year': r'"item_year":\s*"([^"]*)"',
                'item_year_to': r'"item_year_to":\s*"([^"]*)"',
                'reference_url': r'"reference_url":\s*"([^"]*)"',
                'image_url': r'"image_url":\s*"([^"]*)"',
                'group': r'"group":\s*"([^"]*)"',
                'description': r'"description":\s*"([^"]*)"'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1)
            
            if data and 'status' in data:
                print(f"✅ Manual extraction successful: {data}")
                return data
            else:
                print("⚠️ Manual extraction failed - no status found")
                return None
                
        except Exception as e:
            print(f"🔴 Manual extraction error: {e}")
            return None
    
    def get_research_prompt(self, name: str, category: str, subcategory: str) -> str:
        """Get research prompt - UPDATED to discourage comments"""
        
        if category == 'sports':
            return f"""
Please research the following item metadata for a sports player:
Name: "{name}"
Category: {category} - {subcategory}

Please provide ONLY a clean JSON object with no comments or additional text:

{{
    "status": "success",
    "item_year": "1997",
    "item_year_to": "2025",
    "reference_url": "https://en.wikipedia.org/wiki/Lionel_Messi",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Lionel_Messi_20180626.jpg",
    "group": "FC Barcelona",
    "description": "Argentine professional footballer"
}}

IMPORTANT: Return ONLY valid JSON without any comments, explanations, or markdown formatting.

If no information can be found, return:
{{
    "status": "failed"
}}
"""
        
        elif category == 'games':
            return f"""
Please research the following item metadata for a video game:
Name: "{name}"
Category: {category} - {subcategory}

Please provide ONLY a clean JSON object with no comments or additional text:

{{
    "status": "success",
    "item_year": "2011",
    "reference_url": "https://en.wikipedia.org/wiki/The_Elder_Scrolls_V:_Skyrim",
    "image_url": "https://upload.wikimedia.org/wikipedia/en/5/56/The_Elder_Scrolls_V_Skyrim_cover.png",
    "group": "Action role-playing",
    "description": "Action role-playing video game"
}}

Possible values for group: Shooter, cRPG, jRPG, Action, Sports, MOBA, Mech, RPG, Horror, Fighting, Royale, Strategy, Adventure, MMORPG, RTS, Hero Shooter, Metroidvania, Stealth, Puzzle, Sandbox, Rogue, Souls, Survival, Card

IMPORTANT: Return ONLY valid JSON without any comments, explanations, or markdown formatting.

If no information can be found, return:
{{
    "status": "failed"
}}
"""
        
        elif category == 'music':
            return f"""
Please research the following item metadata for a music artist/band:
Name: "{name}"
Category: {category} - {subcategory}

Please provide ONLY a clean JSON object with no comments or additional text:

{{
    "status": "success",
    "item_year": "1975",
    "item_year_to": "2023",
    "reference_url": "https://en.wikipedia.org/wiki/Queen_(band)",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Queen_-_example.jpg/256px-example.jpg",
    "group": "Rock",
    "description": "British rock band formed in London in 1970"
}}

Possible values for group: Rock, Pop, Hip Hop, Jazz, Classical, Electronic, Country, Blues, R&B, Folk, Reggae, Punk, Metal, Alternative, Indie, Soul, Funk, Disco, House, Techno

IMPORTANT: Return ONLY valid JSON without any comments, explanations, or markdown formatting.

If no information can be found, return:
{{
    "status": "failed"
}}
"""
        
        else:
            return f"""
Please research the following item metadata:
Name: "{name}"
Category: {category} - {subcategory}

Please provide ONLY a clean JSON object with no comments or additional text:

{{
    "status": "success",
    "item_year": "2000",
    "item_year_to": "2023",
    "reference_url": "https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/example.jpg",
    "group": "General",
    "description": "Description of the item"
}}

IMPORTANT: Return ONLY valid JSON without any comments, explanations, or markdown formatting.

If no information can be found, return:
{{
    "status": "failed"
}}
"""
    
    def check_item_exists(self, name: str, category: str, subcategory: str) -> Optional[Dict[str, Any]]:
        """Check if item already exists in database"""
        try:
            response = self.supabase.table('items').select('*').eq('name', name).eq('category', category).eq('subcategory', subcategory).execute()
            
            if response.data and len(response.data) > 0:
                print(f"✅ Found existing item: {name}")
                return response.data[0]
            else:
                print(f"📝 Item not found in database: {name}")
                return None
                
        except Exception as e:
            print(f"🔴 Error checking item existence: {e}")
            return None
    
    def get_research_data(self, name: str, category: str, subcategory: str) -> Optional[Dict[str, Any]]:
        """Get research data from Gemini API with improved JSON handling"""
        try:
            # Get the complete prompt
            prompt = self.get_research_prompt(name, category, subcategory)
            
            print(f"🔍 Researching {name} ({category}/{subcategory})...")
            
            # Generate content
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                print(f"✅ Received response from Gemini")
                
                # Use improved JSON extraction
                data = self.extract_json_from_response(response.text)
                
                if data:
                    return data
                else:
                    print(f"⚠️ Could not extract valid JSON from response")
                    print(f"Full response: {response.text}")
                    return None
            else:
                print("⚠️ Empty response from Gemini")
                return None
                
        except Exception as e:
            print(f"🔴 Error getting research data: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None
    
    # ... (keep all other methods the same - get_columns_to_update, update_existing_item, create_new_item, process_item, process_batch, main)
    
    def get_columns_to_update(self, existing_item: Dict[str, Any], research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine which columns need to be updated"""
        updates = {}
        
        # Define mappings between research data and database columns
        field_mappings = {
            'item_year': 'item_year',
            'item_year_to': 'item_year_to',
            'reference_url': 'reference_url',
            'image_url': 'image_url',
            'group': 'group',
            'description': 'description'
        }
        
        for research_field, db_field in field_mappings.items():
            if research_field in research_data and research_data[research_field]:
                # Update if database field is null or empty
                existing_value = existing_item.get(db_field)
                if not existing_value or existing_value == '' or existing_value is None:
                    updates[db_field] = research_data[research_field]
                    print(f"📝 Will update {db_field}: {research_data[research_field]}")
                else:
                    print(f"ℹ️ Skipping {db_field} - already has value: {existing_value}")
        
        return updates
    
    def update_existing_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing item in database"""
        try:
            if not updates:
                print("ℹ️ No updates needed for existing item")
                return True
            
            print(f"🔄 Updating item {item_id} with: {updates}")
            
            response = self.supabase.table('items').update(updates).eq('id', item_id).execute()
            
            if response.data:
                print(f"✅ Successfully updated item with {len(updates)} fields")
                return True
            else:
                print(f"🔴 Failed to update item - no data returned")
                return False
                
        except Exception as e:
            print(f"🔴 Error updating item: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    def create_new_item(self, name: str, category: str, subcategory: str, research_data: Dict[str, Any]) -> bool:
        """Create new item in database"""
        try:
            # Prepare item data
            item_data = {
                'name': name,
                'category': category,
                'subcategory': subcategory,
                'description': research_data.get('description', ''),
                'item_year': research_data.get('item_year'),
                'item_year_to': research_data.get('item_year_to'),
                'reference_url': research_data.get('reference_url'),
                'image_url': research_data.get('image_url'),
                'group': research_data.get('group'),
                'view_count': 0,
                'selection_count': 0
            }
            
            # Remove None values
            item_data = {k: v for k, v in item_data.items() if v is not None and v != ''}
            
            print(f"🆕 Creating new item: {item_data}")
            
            response = self.supabase.table('items').insert(item_data).execute()
            
            if response.data:
                print(f"✅ Successfully created new item: {name}")
                return True
            else:
                print(f"🔴 Failed to create item - no data returned")
                return False
                
        except Exception as e:
            print(f"🔴 Error creating item: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    def process_item(self, name: str, category: str, subcategory: str = '') -> bool:
        """Process a single item - update or create"""
        print(f"\n{'='*60}")
        print(f"Processing: {name} ({category}/{subcategory})")
        print(f"{'='*60}")
        
        # Step 1: Check if item exists
        existing_item = self.check_item_exists(name, category, subcategory)
        
        # Step 2: Get research data
        research_data = self.get_research_data(name, category, subcategory)
        
        if not research_data or research_data.get('status') == 'failed':
            print(f"⚠️ No research data found for {name}")
            return False
        
        print(f"📊 Research data: {json.dumps(research_data, indent=2)}")
        
        # Step 3: Update or create
        if existing_item:
            # Update existing item
            updates = self.get_columns_to_update(existing_item, research_data)
            return self.update_existing_item(existing_item['id'], updates)
        else:
            # Create new item
            return self.create_new_item(name, category, subcategory, research_data)
    
    def process_batch(self, items: List[Dict[str, str]]) -> None:
        """Process a batch of items"""
        print(f"🚀 Starting batch processing of {len(items)} items...")
        
        success_count = 0
        fail_count = 0
        
        for i, item in enumerate(items, 1):
            try:
                print(f"\n[{i}/{len(items)}] Processing next item...")
                
                name = item['name']
                category = item['category']
                subcategory = item.get('subcategory', '')
                
                success = self.process_item(name, category, subcategory)
                
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                print(f"🔴 Error processing item {item}: {e}")
                fail_count += 1
        
        print(f"\n{'='*60}")
        print(f"📊 Batch Processing Complete!")
        print(f"✅ Successful: {success_count}")
        print(f"🔴 Failed: {fail_count}")
        if success_count + fail_count > 0:
            print(f"📈 Success Rate: {success_count/(success_count + fail_count)*100:.1f}%")
        print(f"{'='*60}")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Update/Create items in Supabase database using Gemini research')
    
    # Single item mode
    parser.add_argument('--name', type=str, help='Item name')
    parser.add_argument('--category', type=str, choices=['music', 'sports', 'games'], help='Item category')
    parser.add_argument('--subcategory', type=str, default='', help='Item subcategory')
    
    # Batch mode
    parser.add_argument('--batch-file', type=str, help='JSON file with batch of items to process')
    
    # Sample data mode
    parser.add_argument('--sample', action='store_true', help='Process sample data')
    
    # Test mode
    parser.add_argument('--test', action='store_true', help='Test with Lionel Messi')
    
    args = parser.parse_args()
    
    updater = WikiDBUpdater()
    
    if args.test:
        # Test with Lionel Messi
        updater.process_item("Lionel Messi", "sports", "football")
        
    elif args.sample:
        # Process sample data
        sample_items = [
            {'name': 'Michael Jordan', 'category': 'sports', 'subcategory': 'basketball'},
            {'name': 'LeBron James', 'category': 'sports', 'subcategory': 'basketball'},
            {'name': 'The Legend of Zelda: Breath of the Wild', 'category': 'games', 'subcategory': 'action'},
            {'name': 'Red Dead Redemption 2', 'category': 'games', 'subcategory': 'action'},
            {'name': 'The Beatles', 'category': 'music', 'subcategory': 'rock'},
            {'name': 'Queen', 'category': 'music', 'subcategory': 'rock'}
        ]
        
        updater.process_batch(sample_items)
        
    elif args.batch_file:
        # Process batch file
        try:
            with open(args.batch_file, 'r') as f:
                items = json.load(f)
            updater.process_batch(items)
        except Exception as e:
            print(f"🔴 Error reading batch file: {e}")
            
    elif args.name and args.category:
        # Process single item
        subcategory = args.subcategory or ''
        updater.process_item(args.name, args.category, subcategory)
        
    else:
        print("🔴 Please provide either --name and --category, --batch-file, --sample, or --test")
        parser.print_help()


if __name__ == "__main__":
    main()