from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging
from pydantic import BaseModel

from models.top import ItemResponse
from models.top_models.enums import CategoryEnum, DuplicateAction, ResearchDepth
from services.top.item_metadata_service import item_metadata_service
from services.top.item_validation_service import item_validation_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["item-research"])

class ItemResearchRequest(BaseModel):
    """Enhanced request model for item research with duplicate handling"""
    name: str
    category: CategoryEnum
    subcategory: str
    user_provided_description: Optional[str] = None
    auto_create: bool = False
    allow_duplicate: bool = False  # New parameter for duplicate handling
    research_depth: ResearchDepth = ResearchDepth.standard
    duplicate_action: DuplicateAction = DuplicateAction.reject

class DuplicateInfo(BaseModel):
    """Information about duplicate items found"""
    is_duplicate: bool
    duplicate_count: int
    existing_items: List[ItemResponse] = []
    similarity_scores: List[float] = []
    exact_match: bool = False

class ItemResearchResponse(BaseModel):
    """Enhanced response model with duplicate information"""
    name: str
    category: CategoryEnum
    subcategory: str
    
    # Validation results
    is_valid: bool = True
    validation_errors: List[str] = []
    
    # Duplicate information
    duplicate_info: DuplicateInfo
    
    # Researched metadata (only if research was performed)
    description: Optional[str] = None
    group: Optional[str] = None
    item_year: Optional[int] = None
    item_year_to: Optional[int] = None
    reference_url: Optional[str] = None
    image_url: Optional[str] = None
    
    # Research metadata
    research_performed: bool = False
    llm_confidence: int = 0
    web_sources_found: int = 0
    research_method: str = "none"
    research_errors: List[str] = []
    
    # Auto-creation result
    item_created: bool = False
    item_id: Optional[str] = None

@router.post("/", response_model=ItemResearchResponse)
async def research_item_metadata(request: ItemResearchRequest) -> ItemResearchResponse:
    """
    Research item metadata with duplicate validation
    
    Flow:
    1. Validate item name and basic data
    2. Check for duplicates in database
    3. If duplicates found and allow_duplicate=False, return early
    4. If duplicates found and allow_duplicate=True, proceed with research
    5. Perform LLM + Web research
    6. Optionally auto-create item
    """
    try:
        logger.info(f"Starting item research for: {request.name} ({request.category.value}/{request.subcategory})")
        
        # Step 1: Basic validation
        validation_result = await item_validation_service.validate_item_request(
            name=request.name,
            category=request.category,
            subcategory=request.subcategory
        )
        
        if not validation_result['is_valid']:
            return ItemResearchResponse(
                name=request.name,
                category=request.category,
                subcategory=request.subcategory,
                is_valid=False,
                validation_errors=validation_result['errors'],
                duplicate_info=DuplicateInfo(is_duplicate=False, duplicate_count=0),
                research_performed=False
            )
        
        # Step 2: Check for duplicates
        duplicate_result = await item_validation_service.check_duplicates(
            name=request.name,
            category=request.category,
            subcategory=request.subcategory
        )
        
        duplicate_info = DuplicateInfo(
            is_duplicate=duplicate_result['is_duplicate'],
            duplicate_count=duplicate_result['duplicate_count'],
            existing_items=duplicate_result.get('existing_items', []),
            similarity_scores=duplicate_result.get('similarity_scores', []),
            exact_match=duplicate_result.get('exact_match', False)
        )
        
        # Step 3: Handle duplicate policy
        if duplicate_info.is_duplicate and not request.allow_duplicate:
            logger.info(f"Duplicate found for {request.name}, blocking research (allow_duplicate=False)")
            return ItemResearchResponse(
                name=request.name,
                category=request.category,
                subcategory=request.subcategory,
                is_valid=True,
                duplicate_info=duplicate_info,
                research_performed=False,
                research_method="blocked_by_duplicate",
                research_errors=[f"Item already exists in database. {duplicate_info.duplicate_count} similar items found."]
            )
        
        # Step 4: Perform research (if allowed or no duplicates)
        logger.info(f"Performing research for {request.name} (duplicates: {duplicate_info.duplicate_count}, allowed: {request.allow_duplicate})")
        
        research_result = await item_metadata_service.research_item_metadata(
            name=request.name,
            category=request.category,
            subcategory=request.subcategory,
            user_description=request.user_provided_description,
            research_depth=request.research_depth
        )
        
        # Build response with research results
        response = ItemResearchResponse(
            name=request.name,
            category=request.category,
            subcategory=request.subcategory,
            is_valid=True,
            duplicate_info=duplicate_info,
            research_performed=True,
            **research_result
        )
        
        # Add duplicate warning to research errors if duplicates exist
        if duplicate_info.is_duplicate:
            response.research_errors.append(
                f"Note: {duplicate_info.duplicate_count} similar items already exist in database"
            )
        
        # Step 5: Auto-create item if requested and conditions are met
        should_auto_create = (
            request.auto_create and 
            research_result.get('llm_confidence', 0) > 70 and
            (not duplicate_info.exact_match or request.duplicate_action == DuplicateAction.allow)
        )
        
        if should_auto_create:
            try:
                created_item = await item_metadata_service.create_item_from_research(
                    request.name,
                    request.category,
                    request.subcategory,
                    research_result
                )
                
                if created_item:
                    response.item_created = True
                    response.item_id = str(created_item.id)
                    logger.info(f"Auto-created item: {created_item.name} ({created_item.id})")
                
            except Exception as create_error:
                logger.warning(f"Auto-creation failed for {request.name}: {create_error}")
                response.research_errors.append(f"Auto-creation failed: {str(create_error)}")
        elif request.auto_create and duplicate_info.exact_match:
            response.research_errors.append("Auto-creation blocked: exact duplicate found")
        
        logger.info(f"Item research completed for {request.name} (confidence: {response.llm_confidence}%)")
        return response
        
    except Exception as e:
        error_msg = f"Failed to research item metadata: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/validate")
async def validate_item_only(
    name: str,
    category: CategoryEnum,
    subcategory: str,
    check_duplicates: bool = True
):
    """
    Quick validation endpoint without performing research
    """
    try:
        # Basic validation
        validation_result = await item_validation_service.validate_item_request(name, category, subcategory)
        
        response = {
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "is_valid": validation_result['is_valid'],
            "validation_errors": validation_result['errors']
        }
        
        # Add duplicate check if requested
        if check_duplicates:
            duplicate_result = await item_validation_service.check_duplicates(name, category, subcategory)
            response['duplicate_info'] = DuplicateInfo(
                is_duplicate=duplicate_result['is_duplicate'],
                duplicate_count=duplicate_result['duplicate_count'],
                existing_items=duplicate_result.get('existing_items', []),
                exact_match=duplicate_result.get('exact_match', False)
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Validation failed for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))