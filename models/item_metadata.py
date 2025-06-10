from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from models.top_models.enums import CategoryEnum

class ItemMetadataRequest(BaseModel):
    """Request for item metadata research"""
    name: str
    category: CategoryEnum
    subcategory: str
    user_description: Optional[str] = None
    research_depth: str = "standard"  # standard, deep, quick

class ItemMetadataResponse(BaseModel):
    """Response with researched metadata"""
    name: str
    category: CategoryEnum
    subcategory: str
    
    # Core metadata
    description: Optional[str] = None
    group: Optional[str] = None
    item_year: Optional[int] = None
    item_year_to: Optional[int] = None
    
    # Enhanced metadata
    reference_url: Optional[str] = None
    image_url: Optional[str] = None
    additional_metadata: Dict[str, Any] = {}
    
    # Research quality indicators
    confidence_score: int = 0
    sources_used: List[str] = []
    research_timestamp: str
    
class MetadataValidationResult(BaseModel):
    """Result of metadata validation"""
    is_valid: bool
    confidence: int
    issues: List[str] = []
    suggestions: List[str] = []