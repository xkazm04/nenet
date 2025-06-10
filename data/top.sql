-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types
CREATE TYPE category_enum AS ENUM ('music', 'sports', 'games');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE,
    username VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Items table (with popularity tracking)
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    category category_enum NOT NULL,
    subcategory VARCHAR(100),
    reference_url TEXT,
    image_url TEXT,
    -- New fields for better discovery
    description TEXT,
    item_year INTEGER,
    -- Popularity tracking
    view_count INTEGER DEFAULT 0,
    selection_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Create unique constraint on name + category + subcategory to prevent duplicates
    CONSTRAINT unique_item UNIQUE (name, category, subcategory)
);

-- Separate accolades table
CREATE TABLE accolades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL, -- e.g., 'award', 'achievement', 'record'
    name VARCHAR(255) NOT NULL, -- e.g., 'Ballon d''Or', 'World Cup'
    value VARCHAR(255) NOT NULL, -- e.g., '7x Winner', '2022', 'Gold Medal'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tags table for better discovery
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Items to tags junction table
CREATE TABLE item_tags (
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (item_id, tag_id)
);

-- Lists table
CREATE TABLE lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    category category_enum NOT NULL,
    subcategory VARCHAR(100),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    predefined BOOLEAN DEFAULT FALSE,
    size INTEGER DEFAULT 50 CHECK (size > 0 AND size <= 100),
    time_period VARCHAR(50) DEFAULT 'all',
    parent_list_id UUID REFERENCES lists(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Items vs Lists junction table (for rankings)
CREATE TABLE list_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    ranking INTEGER NOT NULL CHECK (ranking > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique item per list
    CONSTRAINT unique_item_per_list UNIQUE (list_id, item_id),
    -- Ensure unique ranking per list
    CONSTRAINT unique_ranking_per_list UNIQUE (list_id, ranking)
);

-- FEATURE 2: User engagement tables
CREATE TABLE user_votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    vote_value INTEGER CHECK (vote_value IN (-1, 1)), -- -1 for downvote, 1 for upvote
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One vote per user per item in a list
    CONSTRAINT unique_user_vote UNIQUE (user_id, list_id, item_id)
);

CREATE TABLE list_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES list_comments(id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE list_follows (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, list_id)
);

-- FEATURE 3: List versioning/history
CREATE TABLE list_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot_data JSONB NOT NULL, -- Stores the complete list state including items and rankings
    change_description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique version numbers per list
    CONSTRAINT unique_list_version UNIQUE (list_id, version_number)
);

-- FEATURE 5: Analytics-friendly aggregations
CREATE TABLE item_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    total_appearances INTEGER DEFAULT 0,
    average_ranking DECIMAL(5,2),
    best_ranking INTEGER,
    worst_ranking INTEGER,
    ranking_variance DECIMAL(5,2),
    top_10_count INTEGER DEFAULT 0,
    top_3_count INTEGER DEFAULT 0,
    first_place_count INTEGER DEFAULT 0,
    last_calculated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_item_stats UNIQUE (item_id)
);

-- Materialized view for trending items
CREATE MATERIALIZED VIEW trending_items AS
SELECT 
    i.id,
    i.name,
    i.category,
    i.subcategory,
    i.view_count,
    i.selection_count,
    COUNT(DISTINCT li.list_id) as list_appearances,
    COUNT(DISTINCT uv.id) as recent_votes,
    AVG(li.ranking) as avg_ranking
FROM items i
LEFT JOIN list_items li ON i.id = li.item_id
LEFT JOIN user_votes uv ON i.id = uv.item_id 
    AND uv.created_at > NOW() - INTERVAL '7 days'
GROUP BY i.id, i.name, i.category, i.subcategory, i.view_count, i.selection_count
ORDER BY recent_votes DESC, list_appearances DESC;

-- Create indexes for better performance
CREATE INDEX idx_lists_category ON lists(category);
CREATE INDEX idx_lists_subcategory ON lists(subcategory);
CREATE INDEX idx_lists_user_id ON lists(user_id);
CREATE INDEX idx_lists_predefined ON lists(predefined);
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_items_subcategory ON items(subcategory);
CREATE INDEX idx_items_item_year ON items(item_year);
CREATE INDEX idx_list_items_list_id ON list_items(list_id);
CREATE INDEX idx_list_items_ranking ON list_items(list_id, ranking);
CREATE INDEX idx_accolades_item_id ON accolades(item_id);
CREATE INDEX idx_accolades_type ON accolades(type);
CREATE INDEX idx_user_votes_list_item ON user_votes(list_id, item_id);
CREATE INDEX idx_list_comments_list_id ON list_comments(list_id);
CREATE INDEX idx_list_versions_list_id ON list_versions(list_id);

-- Update timestamp triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lists_updated_at BEFORE UPDATE ON lists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_list_items_updated_at BEFORE UPDATE ON list_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accolades_updated_at BEFORE UPDATE ON accolades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_votes_updated_at BEFORE UPDATE ON user_votes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_list_comments_updated_at BEFORE UPDATE ON list_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to rerank items when inserting/updating
CREATE OR REPLACE FUNCTION rerank_list_items()
RETURNS TRIGGER AS $$
BEGIN
    -- If inserting or updating ranking
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.ranking != OLD.ranking) THEN
        -- Shift existing items down
        UPDATE list_items 
        SET ranking = ranking + 1
        WHERE list_id = NEW.list_id 
        AND ranking >= NEW.ranking 
        AND id != NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_rerank_list_items 
    BEFORE INSERT OR UPDATE ON list_items
    FOR EACH ROW EXECUTE FUNCTION rerank_list_items();

-- Function to increment view count
CREATE OR REPLACE FUNCTION increment_item_view_count(item_uuid UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE items 
    SET view_count = view_count + 1 
    WHERE id = item_uuid;
END;
$$ language 'plpgsql';

-- Function to increment selection count
CREATE OR REPLACE FUNCTION increment_item_selection_count(item_uuid UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE items 
    SET selection_count = selection_count + 1 
    WHERE id = item_uuid;
END;
$$ language 'plpgsql';

-- Function to create list version snapshot
CREATE OR REPLACE FUNCTION create_list_version_snapshot(
    p_list_id UUID, 
    p_user_id UUID, 
    p_description TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_version_number INTEGER;
    v_snapshot JSONB;
BEGIN
    -- Get next version number
    SELECT COALESCE(MAX(version_number), 0) + 1 
    INTO v_version_number
    FROM list_versions 
    WHERE list_id = p_list_id;
    
    -- Create snapshot
    SELECT jsonb_build_object(
        'list_info', row_to_json(l.*),
        'items', jsonb_agg(
            jsonb_build_object(
                'ranking', li.ranking,
                'item', row_to_json(i.*),
                'accolades', (
                    SELECT jsonb_agg(row_to_json(a.*))
                    FROM accolades a
                    WHERE a.item_id = i.id
                )
            ) ORDER BY li.ranking
        )
    )
    INTO v_snapshot
    FROM lists l
    JOIN list_items li ON l.id = li.list_id
    JOIN items i ON li.item_id = i.id
    WHERE l.id = p_list_id
    GROUP BY l.id;
    
    -- Insert version
    INSERT INTO list_versions (
        list_id, 
        version_number, 
        snapshot_data, 
        change_description, 
        created_by
    )
    VALUES (
        p_list_id, 
        v_version_number, 
        v_snapshot, 
        p_description, 
        p_user_id
    );
END;
$$ language 'plpgsql';

-- Function to update item statistics
CREATE OR REPLACE FUNCTION update_item_statistics(p_item_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO item_statistics (
        item_id,
        total_appearances,
        average_ranking,
        best_ranking,
        worst_ranking,
        ranking_variance,
        top_10_count,
        top_3_count,
        first_place_count
    )
    SELECT 
        p_item_id,
        COUNT(*),
        AVG(ranking),
        MIN(ranking),
        MAX(ranking),
        VARIANCE(ranking),
        COUNT(*) FILTER (WHERE ranking <= 10),
        COUNT(*) FILTER (WHERE ranking <= 3),
        COUNT(*) FILTER (WHERE ranking = 1)
    FROM list_items
    WHERE item_id = p_item_id
    ON CONFLICT (item_id) 
    DO UPDATE SET
        total_appearances = EXCLUDED.total_appearances,
        average_ranking = EXCLUDED.average_ranking,
        best_ranking = EXCLUDED.best_ranking,
        worst_ranking = EXCLUDED.worst_ranking,
        ranking_variance = EXCLUDED.ranking_variance,
        top_10_count = EXCLUDED.top_10_count,
        top_3_count = EXCLUDED.top_3_count,
        first_place_count = EXCLUDED.first_place_count,
        last_calculated = NOW();
END;
$$ language 'plpgsql';

-- Insert sample data
INSERT INTO items (name, category, subcategory, description, item_year) VALUES
('Pele', 'sports', 'soccer', 'Brazilian football legend widely regarded as one of the greatest players of all time', 1956),
('Diego Maradona', 'sports', 'soccer', 'Argentine football genius known for the "Hand of God" and incredible dribbling skills', 1976),
('Johan Cruyff', 'sports', 'soccer', 'Dutch master who revolutionized football with "Total Football" philosophy', 1964),
('Franz Beckenbauer', 'sports', 'soccer', 'German defender who redefined the sweeper role', 1963),
('Lionel Messi', 'sports', 'soccer', 'Argentine wizard with unprecedented dribbling and scoring ability', 2004),
('Cristiano Ronaldo', 'sports', 'soccer', 'Portuguese phenomenon known for athleticism and goal-scoring prowess', 2002),
('Alfredo Di Stefano', 'sports', 'soccer', 'Real Madrid legend who dominated European football', 1945),
('Ferenc Puskas', 'sports', 'soccer', 'Hungarian striker with legendary left foot', 1943),
('George Best', 'sports', 'soccer', 'Northern Irish winger known for skill and charisma', 1963),
('Michel Platini', 'sports', 'soccer', 'French playmaker with exceptional vision and technique', 1972)
ON CONFLICT (name, category, subcategory) DO NOTHING;

-- Insert accolades for the players
DO $$
DECLARE
    player_id UUID;
BEGIN
    -- Pele's accolades
    SELECT id INTO player_id FROM items WHERE name = 'Pele' AND category = 'sports';
    INSERT INTO accolades (item_id, type, name, value) VALUES
    (player_id, 'award', 'FIFA World Cup', '3x Winner'),
    (player_id, 'achievement', 'Career Goals', '1281 goals'),
    (player_id, 'record', 'Santos Appearances', '638 games');
    
    -- Messi's accolades
    SELECT id INTO player_id FROM items WHERE name = 'Lionel Messi' AND category = 'sports';
    INSERT INTO accolades (item_id, type, name, value) VALUES
    (player_id, 'award', 'Ballon d''Or', '8x Winner'),
    (player_id, 'award', 'FIFA World Cup', '1x Winner'),
    (player_id, 'achievement', 'Barcelona Goals', '672 goals'),
    (player_id, 'record', 'Most goals in a calendar year', '91 goals (2012)');
    
    -- Ronaldo's accolades
    SELECT id INTO player_id FROM items WHERE name = 'Cristiano Ronaldo' AND category = 'sports';
    INSERT INTO accolades (item_id, type, name, value) VALUES
    (player_id, 'award', 'Ballon d''Or', '5x Winner'),
    (player_id, 'award', 'UEFA Champions League', '5x Winner'),
    (player_id, 'achievement', 'Career Goals', '850+ goals'),
    (player_id, 'record', 'Champions League All-time Top Scorer', '140 goals');
END $$;

-- Create sample tags
INSERT INTO tags (name) VALUES
('Legend'), ('GOAT'), ('World Cup Winner'), ('Ballon d''Or Winner'), 
('Goal Machine'), ('Playmaker'), ('Dribbler'), ('Leader')
ON CONFLICT (name) DO NOTHING;

-- Create a sample predefined list
INSERT INTO lists (title, category, subcategory, predefined, size) VALUES
('Greatest Soccer Players of All Time', 'sports', 'soccer', TRUE, 50);

-- Add items to the sample list
DO $$
DECLARE
    list_uuid UUID;
    item_uuid UUID;
    rank_counter INTEGER := 1;
BEGIN
    -- Get the list ID
    SELECT id INTO list_uuid FROM lists WHERE title = 'Greatest Soccer Players of All Time';
    
    -- Add top 10 soccer players to the list
    FOR item_uuid IN 
        SELECT id FROM items 
        WHERE category = 'sports' AND subcategory = 'soccer' 
        ORDER BY name 
        LIMIT 10
    LOOP
        INSERT INTO list_items (list_id, item_id, ranking) 
        VALUES (list_uuid, item_uuid, rank_counter);
        rank_counter := rank_counter + 1;
    END LOOP;
    
    -- Create initial version snapshot
    PERFORM create_list_version_snapshot(list_uuid, NULL, 'Initial list creation');
END $$;

-- Refresh materialized view
REFRESH MATERIALIZED VIEW trending_items;