-- Extend items table with group and item_year_to columns

-- Add group column for genre/organization grouping
ALTER TABLE items 
ADD COLUMN IF NOT EXISTS "group" VARCHAR(150);

-- Add item_year_to for date ranges (useful for sports careers, game series, etc.)
ALTER TABLE items 
ADD COLUMN IF NOT EXISTS item_year_to INTEGER;

-- Add index for better performance on group queries
CREATE INDEX IF NOT EXISTS idx_items_group ON items("group");

-- Add index for year range queries
CREATE INDEX IF NOT EXISTS idx_items_year_range ON items(item_year, item_year_to);

-- Add comment to clarify usage
COMMENT ON COLUMN items."group" IS 'Genre for games, team/organization for sports, label for music, etc.';
COMMENT ON COLUMN items.item_year_to IS 'End year for ranges (e.g., player career end, game series end)';

-- Update existing items to have a default group if needed
UPDATE items 
SET "group" = 
    CASE 
        WHEN category = 'sports' AND subcategory = 'soccer' THEN 'Football Club'
        WHEN category = 'sports' AND subcategory = 'basketball' THEN 'NBA Team'
        WHEN category = 'sports' AND subcategory = 'hockey' THEN 'NHL Team'
        ELSE 'Unknown'
    END
WHERE "group" IS NULL;

-- Add constraint to ensure item_year_to is greater than or equal to item_year when both are present
ALTER TABLE items 
ADD CONSTRAINT check_year_range 
CHECK (item_year_to IS NULL OR item_year IS NULL OR item_year_to >= item_year);