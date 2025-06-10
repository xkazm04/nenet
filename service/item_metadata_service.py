import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from models.top_models.enums import CategoryEnum, ResearchDepth
from models.top import ItemCreate, ItemResponse
from services.llm_clients.groq_client import GroqLLMClient
from services.web_research.firecrawl_metadata_service import firecrawl_metadata_service
from services.top.top_item import top_items_service
from config.database_top import supabase
from utils.metadata_prompt_builder import MetadataPromptBuilder

logger = logging.getLogger(__name__)

class ItemMetadataService:
    """Service for researching item metadata using LLM + Web sources"""
    
    def __init__(self):
        self.llm_client = GroqLLMClient()
        self.web_service = firecrawl_metadata_service
        self.prompt_builder = MetadataPromptBuilder()
        
        # Category-specific group mappings for validation
        self.category_group_mappings = {
            'games': {
                'video_games': [
                    'Action', 'Adventure', 'RPG', 'Strategy', 'Simulation', 
                    'Sports', 'Racing', 'Puzzle', 'Platform', 'Fighting',
                    'Shooter', 'Horror', 'Indie', 'MMO', 'MOBA'
                ]
            },
            'sports': {
                'soccer': ['Club Team', 'National Team', 'League'],
                'basketball': ['NBA Team', 'International Team', 'College'],
                'hockey': ['NHL Team', 'International Team', 'Junior League']
            },
            'music': {
                'artists': ['Pop', 'Rock', 'Hip-Hop', 'Electronic', 'Classical', 'Jazz', 'Country'],
                'albums': ['Studio Album', 'Live Album', 'Compilation', 'EP', 'Soundtrack']
            }
        }
    
    async def research_item_metadata(
        self, 
        name: str, 
        category: CategoryEnum, 
        subcategory: str, 
        user_description: Optional[str] = None,
        research_depth: ResearchDepth = ResearchDepth.standard
    ) -> Dict[str, Any]:
        """
        Research item metadata with LLM as primary source and Wikipedia for enhancement
        """
        try:
            logger.info(f"Researching metadata for: {name} ({category.value}/{subcategory}) - depth: {research_depth.value}")
            
            # Step 1: LLM Research (Primary) - Use LLM knowledge as the main source
            llm_result = await self._research_with_llm(name, category, subcategory, user_description)
            
            # Step 2: Web Research (Enhancement) - Only for missing attributes
            web_result = await self._research_with_web(name, category, subcategory, llm_result.get('llm_data', {}))
            
            # Step 3: Combine results with LLM as primary
            combined_result = self._combine_research_results(llm_result, web_result, category, subcategory)
            combined_result['research_depth'] = research_depth.value
            
            logger.info(f"Research completed for {name} with {combined_result['llm_confidence']}% confidence")
            return combined_result
            
        except Exception as e:
            logger.error(f"Item metadata research failed for {name}: {e}")
            return {
                'description': None,
                'group': None,
                'item_year': None,
                'reference_url': None,
                'image_url': None,
                'llm_confidence': 0,
                'web_sources_found': 0,
                'research_method': 'failed',
                'research_errors': [str(e)],
                'research_depth': research_depth.value
            }
    
    async def _research_with_llm(
        self, 
        name: str, 
        category: CategoryEnum, 
        subcategory: str, 
        user_description: Optional[str]
    ) -> Dict[str, Any]:
        """Research using LLM (Groq) for metadata extraction - PRIMARY SOURCE"""
        try:
            if not self.llm_client.is_available():
                return {'llm_confidence': 0, 'llm_data': {}, 'llm_error': 'LLM client not available'}
            
            # Build specialized prompt for metadata research
            prompt = self.prompt_builder.build_metadata_prompt(name, category, subcategory, user_description)
            
            logger.info(f"Using LLM as primary metadata source for: {name}")
            
            # Use the specialized metadata research method
            metadata_response = self.llm_client.research_metadata(
                name=name,
                category=category.value,
                subcategory=subcategory,
                custom_prompt=prompt
            )
            
            # Validate and clean the metadata
            validated_metadata = self._validate_llm_metadata(metadata_response, category, subcategory)
            
            return {
                'llm_confidence': 90,  # High confidence for LLM training data
                'llm_data': validated_metadata,
                'llm_method': 'groq_metadata_research'
            }
            
        except Exception as e:
            logger.warning(f"LLM research failed for {name}: {e}")
            return {'llm_confidence': 0, 'llm_data': {}, 'llm_error': str(e)}
    
    async def _research_with_web(
        self, 
        name: str, 
        category: CategoryEnum, 
        subcategory: str,
        llm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Research using Wikipedia for MISSING attributes only"""
        try:
            if not self.web_service._service_available:
                return {'web_confidence': 0, 'web_data': {}, 'web_error': 'Firecrawl not available'}
            
            # Check what's missing from LLM data
            missing_attributes = self._identify_missing_attributes(llm_data)
            
            if not missing_attributes:
                logger.info(f"All metadata available from LLM for {name}, skipping web research")
                return {'web_confidence': 0, 'web_data': {}, 'web_info': 'No missing attributes'}
            
            logger.info(f"Searching Wikipedia for missing attributes: {missing_attributes} for {name}")
            
            # Search Wikipedia for metadata
            web_result = await self.web_service.search_wikipedia_metadata(name, category.value, subcategory)
            
            if not web_result.get('success', False):
                return {
                    'web_confidence': 0, 
                    'web_data': {}, 
                    'web_error': web_result.get('error', 'Wikipedia search failed')
                }
            
            # Filter web metadata to only include missing attributes
            web_metadata = web_result.get('metadata', {})
            filtered_metadata = {
                key: value for key, value in web_metadata.items() 
                if key in missing_attributes and value is not None
            }
            
            # Add reference URL and image if available
            if web_result.get('reference_url'):
                filtered_metadata['reference_url'] = web_result['reference_url']
            
            return {
                'web_confidence': 70,
                'web_data': filtered_metadata,
                'web_method': 'wikipedia_enhancement',
                'missing_attributes_found': list(filtered_metadata.keys())
            }
            
        except Exception as e:
            logger.warning(f"Web research failed for {name}: {e}")
            return {'web_confidence': 0, 'web_data': {}, 'web_error': str(e)}
    
    def _identify_missing_attributes(self, llm_data: Dict[str, Any]) -> List[str]:
        """Identify which attributes are missing from LLM data"""
        missing = []
        
        core_attributes = ['description', 'group', 'item_year']
        enhancement_attributes = ['reference_url', 'image_url']
        
        for attr in core_attributes:
            if not llm_data.get(attr):
                missing.append(attr)
        
        # Always try to get enhancement attributes from web
        missing.extend(enhancement_attributes)
        
        return missing
    
    def _validate_llm_metadata(self, raw_metadata: dict, category: CategoryEnum, subcategory: str) -> Dict[str, Any]:
        """Validate and clean LLM metadata response"""
        validated = {}
        
        try:
            # Description
            if 'description' in raw_metadata and raw_metadata['description']:
                validated['description'] = str(raw_metadata['description'])[:500]
            
            # Group with validation
            if 'group' in raw_metadata and raw_metadata['group']:
                group = str(raw_metadata['group'])
                validated['group'] = self._validate_group(group, category, subcategory)
            
            # Years
            if 'item_year' in raw_metadata and raw_metadata['item_year']:
                try:
                    year = int(raw_metadata['item_year'])
                    if 1800 <= year <= datetime.now().year + 2:
                        validated['item_year'] = year
                except (ValueError, TypeError):
                    pass
            
            if 'item_year_to' in raw_metadata and raw_metadata['item_year_to']:
                try:
                    year_to = int(raw_metadata['item_year_to'])
                    if 1800 <= year_to <= datetime.now().year + 2:
                        validated['item_year_to'] = year_to
                except (ValueError, TypeError):
                    pass
            
            return validated
            
        except Exception as e:
            logger.warning(f"Failed to validate LLM metadata: {e}")
            return {}
    
    def _validate_group(self, group: str, category: CategoryEnum, subcategory: str) -> str:
        """Validate and normalize group against known categories"""
        if category.value not in self.category_group_mappings:
            return group
        
        subcategory_groups = self.category_group_mappings[category.value].get(subcategory, [])
        
        # Try exact match
        for valid_group in subcategory_groups:
            if group.lower() == valid_group.lower():
                return valid_group
        
        # Try partial match
        for valid_group in subcategory_groups:
            if group.lower() in valid_group.lower() or valid_group.lower() in group.lower():
                return valid_group
        
        return group
    
    def _combine_research_results(
        self, 
        llm_result: Dict[str, Any], 
        web_result: Dict[str, Any], 
        category: CategoryEnum, 
        subcategory: str
    ) -> Dict[str, Any]:
        """Combine LLM and web research results with LLM as primary source"""
        
        combined = {
            'description': None,
            'group': None,
            'item_year': None,
            'item_year_to': None,
            'reference_url': None,
            'image_url': None,
            'llm_confidence': 0,
            'web_sources_found': 0,
            'research_method': 'llm_primary_web_enhancement',
            'research_errors': []
        }
        
        # Collect errors
        if 'llm_error' in llm_result:
            combined['research_errors'].append(f"LLM: {llm_result['llm_error']}")
        if 'web_error' in web_result:
            combined['research_errors'].append(f"Web: {web_result['web_error']}")
        
        # Primary confidence is from LLM
        llm_confidence = llm_result.get('llm_confidence', 0)
        web_confidence = web_result.get('web_confidence', 0)
        
        # LLM is primary source, web only adds to confidence if it fills gaps
        combined['llm_confidence'] = llm_confidence
        if web_confidence > 0 and web_result.get('web_data'):
            combined['llm_confidence'] = min(llm_confidence + 5, 95)  # Small boost for web enhancement
        
        combined['web_sources_found'] = 1 if web_confidence > 0 else 0
        
        # Combine data with LLM as primary
        llm_data = llm_result.get('llm_data', {})
        web_data = web_result.get('web_data', {})
        
        # Use LLM data first, fill gaps with web data
        combined['description'] = llm_data.get('description') or web_data.get('description')
        combined['group'] = llm_data.get('group') or web_data.get('group')
        combined['item_year'] = llm_data.get('item_year') or web_data.get('item_year')
        combined['item_year_to'] = llm_data.get('item_year_to') or web_data.get('item_year_to')
        
        # Web-only attributes
        combined['reference_url'] = web_data.get('reference_url')
        combined['image_url'] = web_data.get('image_url')
        
        # Add metadata about sources used
        combined['primary_source'] = 'llm_training_data'
        combined['enhancement_source'] = 'wikipedia' if web_data else None
        combined['missing_attributes_filled'] = web_result.get('missing_attributes_found', [])
        
        return combined
    
    async def quick_validate_item(self, name: str, category: CategoryEnum, subcategory: str) -> int:
        """Quick validation to estimate research success confidence"""
        try:
            confidence = 50
            
            if len(name) > 2 and len(name) < 100:
                confidence += 10
            
            if self.llm_client.is_available():
                confidence += 30  # Higher weight for LLM availability
            
            if self.web_service._service_available:
                confidence += 10  # Lower weight for web enhancement
            
            if category in [CategoryEnum.games, CategoryEnum.sports, CategoryEnum.music]:
                confidence += 10
            
            return min(confidence, 95)
            
        except Exception as e:
            logger.warning(f"Quick validation failed for {name}: {e}")
            return 20
    
    async def get_existing_groups(self, category: CategoryEnum) -> List[str]:
        """Get existing groups for a category from database"""
        try:
            result = supabase.table('items').select('group').eq('category', category.value).execute()
            
            groups = set()
            for item in result.data if result.data else []:
                if item.get('group'):
                    groups.add(item['group'])
            
            return sorted(list(groups))
            
        except Exception as e:
            logger.error(f"Failed to get existing groups for {category}: {e}")
            return []
    
    async def create_item_from_research(
        self, 
        name: str, 
        category: CategoryEnum, 
        subcategory: str, 
        research_data: Dict[str, Any]
    ) -> Optional[ItemResponse]:
        """Create item from research data"""
        try:
            item_create = ItemCreate(
                name=name,
                category=category,
                subcategory=subcategory,
                description=research_data.get('description', f"{subcategory.title()} item"),
                group=research_data.get('group'),
                item_year=research_data.get('item_year'),
                item_year_to=research_data.get('item_year_to'),
                image_url=research_data.get('image_url'),
                reference_url=research_data.get('reference_url')
            )
            
            created_item = await top_items_service.create_item(item_create)
            logger.info(f"Created item from research: {created_item.name} ({created_item.id})")
            
            return created_item
            
        except Exception as e:
            logger.error(f"Failed to create item from research: {e}")
            raise

# Create service instance
item_metadata_service = ItemMetadataService()