import csv
import asyncio
import sys
import os
import re
from typing import List, Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database_top import supabase

class GameDataProcessor:
    """Process and import games data with proper accolade handling"""
    
    @staticmethod
    def parse_metacritic_score(score_str: str) -> Optional[int]:
        """Parse metacritic score, handling empty values"""
        if not score_str or score_str.strip() == '':
            return None
        
        try:
            score = float(score_str)
            # Convert user scores (0-10) to 0-100 scale
            if score <= 10:
                return int(score * 10)
            # Critics scores are already 0-100
            return int(score)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def clean_game_name(name: str) -> str:
        """Clean game name for consistency"""
        # Remove extra quotes and normalize spacing
        return name.strip().replace('""', '"')
    
    @staticmethod
    def normalize_developer(developer: str) -> str:
        """Normalize developer names"""
        if not developer:
            return "Unknown Developer"
        return developer.strip()

async def create_game_with_accolades(
    name: str,
    item_year: int,
    group: str,
    description: str,
    meta_users: Optional[str],
    meta_critics: Optional[str],
    goty: Optional[str]
) -> bool:
    """Create a game item with its accolades"""
    
    try:
        # Clean and prepare data
        clean_name = GameDataProcessor.clean_game_name(name)
        clean_group = GameDataProcessor.normalize_developer(group)
        
        # Create the game item
        item_response = supabase.table("items").insert({
            "name": clean_name,
            "category": "games",
            "subcategory": "video_games",
            "group": clean_group,
            "description": description,
            "item_year": item_year
        }).execute()
        
        if not item_response.data:
            print(f"✗ Failed to create game: {clean_name}")
            return False
        
        item = item_response.data[0]
        item_id = item['id']
        accolades_created = 0
        
        # Create Metacritic Users accolade
        users_score = GameDataProcessor.parse_metacritic_score(meta_users)
        if users_score is not None:
            users_response = supabase.table("accolades").insert({
                "item_id": item_id,
                "type": "metacritic_users",
                "name": "Metacritic Users",
                "value": str(users_score)
            }).execute()
            
            if users_response.data:
                accolades_created += 1
        
        # Create Metacritic Critics accolade
        critics_score = GameDataProcessor.parse_metacritic_score(meta_critics)
        if critics_score is not None:
            critics_response = supabase.table("accolades").insert({
                "item_id": item_id,
                "type": "metacritic_critics", 
                "name": "Metacritic Critics",
                "value": str(critics_score)
            }).execute()
            
            if critics_response.data:
                accolades_created += 1
        
        # Create Game of the Year accolade
        if goty and goty.strip().lower() == "winner":
            goty_response = supabase.table("accolades").insert({
                "item_id": item_id,
                "type": "goty",
                "name": "Game of the Year",
                "value": "Winner"
            }).execute()
            
            if goty_response.data:
                accolades_created += 1
        
        print(f"✓ Created game: {clean_name} ({clean_group}, {item_year}) with {accolades_created} accolades")
        return True
        
    except Exception as e:
        print(f"✗ Error creating game {name}: {e}")
        return False

async def create_games_predefined_list(games: List[Dict]) -> bool:
    """Create predefined list for games"""
    
    try:
        # Create the list
        list_response = supabase.table("lists").insert({
            "title": "Greatest Video Games of All Time",
            "category": "games",
            "subcategory": "video_games",
            "predefined": True,
            "size": len(games)
        }).execute()
        
        if not list_response.data:
            print("✗ Failed to create games list")
            return False
        
        list_obj = list_response.data[0]
        list_id = list_obj['id']
        
        # Get created game items
        games_response = supabase.table("items").select("*").eq("category", "games").execute()
        
        if not games_response.data:
            print("✗ No games found to add to list")
            return False
        
        # Sort games by a combination of critic score and user score for ranking
        def get_game_score(game_data):
            """Calculate composite score for ranking"""
            try:
                # Get accolades for this game
                accolades_response = supabase.table("accolades").select("*").eq("item_id", game_data['id']).execute()
                
                critics_score = 0
                users_score = 0
                goty_bonus = 0
                
                for accolade in accolades_response.data:
                    if accolade['type'] == 'metacritic_critics':
                        critics_score = int(accolade['value'])
                    elif accolade['type'] == 'metacritic_users':
                        users_score = int(accolade['value'])
                    elif accolade['type'] == 'goty':
                        goty_bonus = 10  # GOTY bonus
                
                # Weighted score: 60% critics, 40% users, plus GOTY bonus
                composite_score = (critics_score * 0.6) + (users_score * 0.4) + goty_bonus
                return composite_score
                
            except:
                return 0
        
        # Sort games by composite score
        sorted_games = sorted(games_response.data, key=get_game_score, reverse=True)
        
        # Add games to list
        items_added = 0
        for i, game in enumerate(sorted_games[:50]):  # Top 50 games
            try:
                list_item_response = supabase.table("list_items").insert({
                    "list_id": list_id,
                    "item_id": game['id'],
                    "ranking": i + 1
                }).execute()
                
                if list_item_response.data:
                    items_added += 1
                    print(f"  → Added {game['name']} at ranking {i + 1}")
                    
            except Exception as e:
                print(f"  ✗ Failed to add {game['name']} to list: {e}")
        
        print(f"✓ Created games list with {items_added} items")
        return True
        
    except Exception as e:
        print(f"✗ Error creating games list: {e}")
        return False

async def import_games_data():
    """Main function to import games data"""
    print("🎮 Starting Games Data Import...")
    print("=" * 50)
    
    csv_path = os.path.join(os.path.dirname(__file__), "games.csv")
    
    try:
        games_data = []
        games_created = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Skip rows with missing essential data
                if not row.get('Name') or not row.get('item_year'):
                    print(f"⚠ Skipping row with missing data: {row}")
                    continue
                
                try:
                    item_year = int(row['item_year'])
                except (ValueError, TypeError):
                    print(f"⚠ Invalid year for {row.get('Name', 'Unknown')}: {row.get('item_year')}")
                    continue
                
                # Prepare description
                description = f"Video game developed by {row.get('Group', 'Unknown')} in {item_year}"
                if row.get('Description'):
                    description += f". Genre: {row['Description']}"
                
                # Create game with accolades
                success = await create_game_with_accolades(
                    name=row['Name'],
                    item_year=item_year,
                    group=row.get('Group', 'Unknown Developer'),
                    description=description,
                    meta_users=row.get('Meta - Users', ''),
                    meta_critics=row.get('Meta - Critics', ''),
                    goty=row.get('Game of the year', '')
                )
                
                if success:
                    games_created += 1
                    games_data.append(row)
                
                # Add small delay to avoid overwhelming the database
                await asyncio.sleep(0.1)
        
        print(f"\n✅ Games import completed: {games_created} games created")
        
        # Create predefined list
        if games_data:
            print("\n📋 Creating predefined games list...")
            await create_games_predefined_list(games_data)
        
        return games_created
        
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_path}")
        return 0
    except Exception as e:
        print(f"❌ Games import error: {e}")
        return 0

async def verify_games_import():
    """Verify the games import"""
    print("\n🔍 Verifying Games Import...")
    print("=" * 30)
    
    try:
        # Check games count
        games_response = supabase.table("items").select("*").eq("category", "games").execute()
        print(f"Total games imported: {len(games_response.data)}")
        
        # Check accolades distribution
        accolades_response = supabase.table("accolades").select("*").execute()
        
        accolade_types = {}
        for accolade in accolades_response.data:
            acc_type = accolade.get('type', 'unknown')
            accolade_types[acc_type] = accolade_types.get(acc_type, 0) + 1
        
        print("\nAccolades by type:")
        for acc_type, count in accolade_types.items():
            if 'metacritic' in acc_type or 'goty' in acc_type:
                print(f"  - {acc_type}: {count}")
        
        # Show sample games with accolades
        print("\n📋 Sample Games:")
        for game in games_response.data[:5]:
            print(f"\n{game['name']} ({game['item_year']}) - {game['group']}")
            
            # Get accolades for this game
            game_accolades = supabase.table("accolades").select("*").eq("item_id", game['id']).execute()
            for accolade in game_accolades.data:
                print(f"  • {accolade['name']}: {accolade['value']} ({accolade['type']})")
        
        # Check predefined list
        games_lists = supabase.table("lists").select("*").eq("category", "games").execute()
        print(f"\nGames lists created: {len(games_lists.data)}")
        
        print("\n✅ Verification completed!")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")

async def main():
    """Run the complete games import process"""
    print("🚀 Starting Complete Games Import Process...")
    
    # First, run the SQL extension (you should run this manually first)
    print("📝 Make sure to run the SQL extension first:")
    print("   psql -d your_database -f extend_items_table.sql")
    print()
    
    # Import games data
    total_games = await import_games_data()
    
    # Verify import
    if total_games > 0:
        await verify_games_import()
    
    print(f"\n🎉 Games import process completed! Total games: {total_games}")

if __name__ == "__main__":
    asyncio.run(main())