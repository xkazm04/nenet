from config.database_top import supabase
from typing import List, Optional, Dict, Any
import uuid
from supabase import Client
import logging
from models.top import (
    ItemCreate, ItemUpdate, ItemResponse,
    ListItemCreate, ListItemResponse, ListItemWithDetails,
    CategoryEnum,
    AccoladeCreate, AccoladeResponse,
    TagResponse,
    ItemAnalyticsResponse,
    ItemPopularityResponse,
    AdvancedItemSearchFilters,
)

logger = logging.getLogger(__name__)


class TopItemsService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    # Item CRUD operations

    async def create_item(self, item_data: ItemCreate) -> ItemResponse:
        """Create a new item"""
        try:
            result = self.supabase.table('items').insert(
                item_data.dict()).execute()
            if result.data:
                return ItemResponse(**result.data[0])
            raise Exception("Failed to create item")
        except Exception as e:
            logger.error(f"Error creating item: {e}")
            raise

    async def get_item_by_id(self, item_id: uuid.UUID) -> Optional[ItemResponse]:
        """Get item by ID"""
        try:
            result = self.supabase.table('items').select(
                '*').eq('id', str(item_id)).execute()
            if result.data:
                return ItemResponse(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            raise

    async def update_item(self, item_id: uuid.UUID, item_data: ItemUpdate) -> Optional[ItemResponse]:
        """Update an item"""
        try:
            update_data = {k: v for k, v in item_data.dict().items()
                           if v is not None}
            result = self.supabase.table('items').update(
                update_data).eq('id', str(item_id)).execute()
            if result.data:
                return ItemResponse(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {e}")
            raise

    async def add_item_image(self, item_id: uuid.UUID, image_url: str) -> Optional[ItemResponse]:
        """Add image to an item"""
        try:
            result = self.supabase.table('items').update(
                {'image_url': image_url}).eq('id', str(item_id)).execute()
            if result.data:
                return ItemResponse(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error adding image to item {item_id}: {e}")
            raise

    async def search_items(
        self,
        filters: AdvancedItemSearchFilters,
        limit: int = 50,
        offset: int = 0
    ) -> List[ItemResponse]:
        """Search items with filters"""
        try:
            query = self.supabase.table('items').select('*')

            # Fix: Check if category is enum or string
            if filters.category:
                category_value = filters.category.value if hasattr(filters.category, 'value') else filters.category
                query = query.eq('category', category_value)
                
            if filters.subcategory:
                query = query.eq('subcategory', filters.subcategory)
                
            if filters.search_query:
                query = query.or_(f'name.ilike.%{filters.search_query}%,description.ilike.%{filters.search_query}%')

            # Add tag filtering if tags are provided
            if filters.tags:
                # This would require a more complex query with joins - simplified for now
                pass

            # Add year filtering
            if filters.year_from:
                query = query.gte('item_year', filters.year_from)
            if filters.year_to:
                query = query.lte('item_year', filters.year_to)

            # Add sorting
            if filters.sort_by == "popularity":
                query = query.order('selection_count', desc=True)
            elif filters.sort_by == "recent":
                query = query.order('created_at', desc=True)
            elif filters.sort_by == "ranking":
                # Would need to join with list_items for average ranking
                query = query.order('view_count', desc=True)  # Fallback to view_count
            else:  # default to name
                query = query.order('name')

            # Apply pagination
            result = query.range(offset, offset + limit - 1).execute()

            return [ItemResponse(**item) for item in result.data] if result.data else []
            
        except Exception as e:
            logger.error(f"Error searching items: {e}")
            raise

    async def add_item_to_list(self, list_item_data: ListItemCreate) -> ListItemResponse:
        """Add item to list"""
        try:
            result = self.supabase.table('list_items').insert(
                list_item_data.dict()).execute()
            if result.data:
                return ListItemResponse(**result.data[0])
            raise Exception("Failed to add item to list")
        except Exception as e:
            logger.error(f"Error adding item to list: {e}")
            raise

    async def get_list_items(self, list_id: uuid.UUID) -> List[ListItemWithDetails]:
        """Get all items in a list with details, sorted by ranking"""
        try:
            result = self.supabase.table('list_items').select('''
                id, ranking, created_at, updated_at,
                items (*)
            ''').eq('list_id', str(list_id)).order('ranking').execute()

            items = []
            for item_data in result.data if result.data else []:
                item_response = ItemResponse(**item_data['items'])
                list_item = ListItemWithDetails(
                    id=item_data['id'],
                    ranking=item_data['ranking'],
                    item=item_response,
                    created_at=item_data['created_at'],
                    updated_at=item_data['updated_at']
                )
                items.append(list_item)

            return items
        except Exception as e:
            logger.error(f"Error getting list items for {list_id}: {e}")
            raise

    async def remove_item_from_list(self, list_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        """Remove item from list"""
        try:
            result = self.supabase.table('list_items').delete().eq(
                'list_id', str(list_id)).eq('item_id', str(item_id)).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.error(f"Error removing item from list: {e}")
            raise

    async def rerank_list_items(self, list_id: uuid.UUID, item_rankings: List[Dict[str, Any]]) -> List[ListItemWithDetails]:
        """Rerank items in a list"""
        try:
            # Update rankings for each item
            for item_ranking in item_rankings:
                item_id = item_ranking['item_id']
                new_ranking = item_ranking['new_ranking']

                self.supabase.table('list_items').update({
                    'ranking': new_ranking
                }).eq('list_id', str(list_id)).eq('item_id', str(item_id)).execute()

            # Return updated list
            return await self.get_list_items(list_id)
        except Exception as e:
            logger.error(f"Error reranking list items: {e}")
            raise
# Add these methods to your existing TopItemsService class


async def get_item_analytics(self, item_id: uuid.UUID) -> Optional[ItemAnalyticsResponse]:
    """Get comprehensive analytics for an item"""
    try:
        # Update statistics first
        self.supabase.rpc('update_item_statistics', {
                          'p_item_id': str(item_id)}).execute()

        # Get analytics data
        result = self.supabase.table('item_statistics').select('''
            *,
            items!inner(view_count, selection_count)
        ''').eq('item_id', str(item_id)).execute()

        if not result.data:
            return None

        data = result.data[0]

        # Calculate popularity and trending scores
        popularity_score = (data['items']['view_count'] * 0.3 +
                            data['items']['selection_count'] * 0.7)

        trending_score = await self._calculate_trending_score(item_id)

        return ItemAnalyticsResponse(
            item_id=item_id,
            **{k: v for k, v in data.items() if k not in ['items']},
            popularity_score=popularity_score,
            trending_score=trending_score
        )

    except Exception as e:
        logger.error(f"Error getting item analytics {item_id}: {e}")
        raise



async def search_items_advanced(self, filters: AdvancedItemSearchFilters, limit: int = 50, offset: int = 0) -> List[ItemResponse]:
    """Advanced search with analytics filters"""
    try:
        query = self.supabase.table('items').select('''
            *,
            accolades (*),
            item_tags (tags (*)),
            item_statistics (*)
        ''')

        # Apply existing filters
        if filters.category:
            query = query.eq('category', filters.category.value)
        if filters.subcategory:
            query = query.eq('subcategory', filters.subcategory)
        if filters.search_query:
            query = query.or_(
                f'name.ilike.%{filters.search_query}%,description.ilike.%{filters.search_query}%')

        # Apply new analytics filters
        if filters.min_popularity:
            query = query.gte('selection_count', filters.min_popularity)
        if filters.min_appearances:
            query = query.gte(
                'item_statistics.total_appearances', filters.min_appearances)

        # Apply ranking position filter
        if filters.ranking_position_filter:
            if filters.ranking_position_filter == "top_10":
                query = query.gt('item_statistics.top_10_count', 0)
            elif filters.ranking_position_filter == "top_3":
                query = query.gt('item_statistics.top_3_count', 0)
            elif filters.ranking_position_filter == "first_place":
                query = query.gt('item_statistics.first_place_count', 0)

        result = query.range(offset, offset + limit - 1).execute()

        items = []
        for item_data in result.data if result.data else []:
            # Filter by accolade criteria
            accolades = [AccoladeResponse(**acc)
                         for acc in item_data.get('accolades', [])]

            if filters.has_accolades and not accolades:
                continue

            if filters.accolade_types:
                accolade_type_names = [acc.type for acc in accolades]
                if not any(acc_type.value in accolade_type_names for acc_type in filters.accolade_types):
                    continue

            tags = [TagResponse(**tag['tags'])
                    for tag in item_data.get('item_tags', [])]

            # Filter by tags
            if filters.tags:
                item_tag_names = [tag.name for tag in tags]
                if not any(tag in item_tag_names for tag in filters.tags):
                    continue

            item_response = ItemResponse(
                **{k: v for k, v in item_data.items() if k not in ['accolades', 'item_tags', 'item_statistics']},
                accolades=accolades,
                tags=tags
            )
            items.append(item_response)

        return items

    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise


async def create_bulk_accolades(self, accolades: List[AccoladeCreate]) -> List[AccoladeResponse]:
    """Create multiple accolades at once"""
    try:
        results = []
        for accolade_data in accolades:
            try:
                result = await self.add_accolade(accolade_data)
                results.append(result)
            except Exception as e:
                logger.warning(
                    f"Failed to create accolade for item {accolade_data.item_id}: {e}")
                continue
        return results
    except Exception as e:
        logger.error(f"Error creating bulk accolades: {e}")
        raise


async def get_item_popularity_trends(self, item_id: uuid.UUID, days: int = 30) -> ItemPopularityResponse:
    """Get item popularity trends over time"""
    try:
        # Get current stats
        current_item = await self.get_item_by_id(item_id)
        if not current_item:
            raise Exception("Item not found")

        # Calculate trend direction (simplified)
        recent_votes = self.supabase.table('user_votes').select('vote_value').eq(
            'item_id', str(item_id)).gte('created_at', f'now() - interval \'{days} days\'').execute()

        total_recent_votes = sum(
            vote['vote_value'] for vote in recent_votes.data) if recent_votes.data else 0

        if total_recent_votes > 5:
            trend = "rising"
        elif total_recent_votes < -5:
            trend = "declining"
        else:
            trend = "stable"

        # Get popularity rank (simplified)
        rank_result = self.supabase.rpc('get_item_popularity_rank', {
                                        'p_item_id': str(item_id)}).execute()
        popularity_rank = rank_result.data[0] if rank_result.data else 999

        return ItemPopularityResponse(
            item_id=item_id,
            view_count=current_item.view_count,
            selection_count=current_item.selection_count,
            recent_trend=trend,
            popularity_rank=popularity_rank
        )

    except Exception as e:
        logger.error(f"Error getting popularity trends: {e}")
        raise

# Initialize service instance
top_items_service = TopItemsService(supabase)
