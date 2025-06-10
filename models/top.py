from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid
from models.top_models.list import ListResponse
from models.top_models.enums import CategoryEnum, AccoladeType, VoteValue
class AccoladeBase(BaseModel):
    type: AccoladeType
    name: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=255)

class AccoladeCreate(AccoladeBase):
    item_id: uuid.UUID

class AccoladeUpdate(BaseModel):
    type: Optional[AccoladeType] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = Field(None, min_length=1, max_length=255)

class AccoladeResponse(AccoladeBase):
    id: uuid.UUID
    item_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Tag Models
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Enhanced Item Models
class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: CategoryEnum
    subcategory: Optional[str] = Field(None, max_length=100)
    reference_url: Optional[str] = None
    description: Optional[str] = None
    item_year: Optional[int] = Field(None, ge=1800, le=2030)

class ItemCreate(ItemBase):
    tags: Optional[List[str]] = []
    accolades: Optional[List[AccoladeBase]] = []
    reference_url: Optional[str] = None
    item_year_to: Optional[int] = None

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[CategoryEnum] = None
    subcategory: Optional[str] = Field(None, max_length=100)
    reference_url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    item_year: Optional[int] = Field(None, ge=1800, le=2030)

class ItemResponse(ItemBase):
    id: uuid.UUID
    image_url: Optional[str]
    view_count: int = 0
    selection_count: int = 0
    created_at: datetime
    updated_at: datetime
    accolades: List[AccoladeResponse] = []
    tags: List[TagResponse] = []
    

    class Config:
        from_attributes = True

# Item Statistics Models
class ItemStatisticsResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    total_appearances: int
    average_ranking: Optional[float]
    best_ranking: Optional[int]
    worst_ranking: Optional[int]
    ranking_variance: Optional[float]
    top_10_count: int
    top_3_count: int
    first_place_count: int
    last_calculated: datetime

    class Config:
        from_attributes = True

# Trending Item Models
class TrendingItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: CategoryEnum
    subcategory: Optional[str]
    view_count: int
    selection_count: int
    list_appearances: int
    recent_votes: int
    avg_ranking: Optional[float]

    class Config:
        from_attributes = True

class UserVoteBase(BaseModel):
    list_id: uuid.UUID
    item_id: uuid.UUID
    vote_value: VoteValue

class UserVoteCreate(UserVoteBase):
    pass

class UserVoteResponse(UserVoteBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



# Updated List Item Models
class ListItemBase(BaseModel):
    list_id: uuid.UUID
    item_id: uuid.UUID
    ranking: int = Field(..., ge=1)

class ListItemCreate(BaseModel):
    list_id: uuid.UUID
    item_id: uuid.UUID
    ranking: int = Field(..., ge=1)

class ListItemUpdate(BaseModel):
    ranking: int = Field(..., ge=1)

class ListItemResponse(ListItemBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
    
class ListItemWithDetails(BaseModel):
    id: uuid.UUID
    ranking: int
    item: ItemResponse
    vote_count: int = 0
    user_vote: Optional[VoteValue] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListWithItems(ListResponse):
    items: List[ListItemWithDetails] = []
    total_items: int = 0
    follower_count: int = 0
    comment_count: int = 0
    is_following: bool = False

# Request Models
class RerankRequest(BaseModel):
    item_rankings: List[dict] = Field(..., description="List of {item_id: UUID, new_ranking: int}")
    create_version: bool = Field(True, description="Create version snapshot after reranking")
    change_description: Optional[str] = Field(None, description="Description of the changes made")

    @validator('item_rankings')
    def validate_rankings(cls, v):
        if not v:
            raise ValueError('item_rankings cannot be empty')
        
        rankings = [item.get('new_ranking') for item in v]
        if len(rankings) != len(set(rankings)):
            raise ValueError('Duplicate rankings are not allowed')
        
        return v

class ImageUploadRequest(BaseModel):
    image_url: str = Field(..., description="URL of the uploaded image")

class BulkItemRequest(BaseModel):
    items: List[ItemCreate] = Field(..., description="List of items to create")


class ItemSearchFilters(BaseModel):
    category: Optional[CategoryEnum] = None
    subcategory: Optional[str] = None
    search_query: Optional[str] = None
    tags: Optional[List[str]] = []
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    min_appearances: Optional[int] = None
    sort_by: Optional[str] = Field("name", pattern="^(name|popularity|recent|ranking)$")

class ItemAnalyticsResponse(BaseModel):
    item_id: uuid.UUID
    total_appearances: int
    average_ranking: Optional[float]
    best_ranking: Optional[int] 
    worst_ranking: Optional[int]
    ranking_variance: Optional[float]
    top_10_count: int
    top_3_count: int
    first_place_count: int
    popularity_score: float
    trending_score: float

    class Config:
        from_attributes = True

# Enhanced Search Filters
class AdvancedItemSearchFilters(ItemSearchFilters):
    min_popularity: Optional[int] = None
    has_accolades: Optional[bool] = None
    accolade_types: Optional[List[AccoladeType]] = []
    min_appearances: Optional[int] = None
    ranking_position_filter: Optional[str] = None  # "top_10", "top_3", "first_place"



# Bulk Operations
class BulkAccoladeRequest(BaseModel):
    accolades: List[AccoladeCreate] = Field(..., description="List of accolades to create")

class ItemPopularityResponse(BaseModel):
    item_id: uuid.UUID
    view_count: int
    selection_count: int
    recent_trend: str  # "rising", "stable", "declining"
    popularity_rank: int
