-- =============================================================================
-- MCP Dev Network — Schema Migration
-- Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
-- =============================================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ROL DE APLICACIÓN (descomentar en producción)
-- ponytail: El rol NO tiene BYPASSRLS para que RLS aplique siempre.
-- =============================================================================
-- CREATE ROLE app_user NOINHERIT LOGIN PASSWORD 'CHANGE_ME' NOBYPASSRLS;

-- =============================================================================
-- TABLAS
-- =============================================================================

-- Tabla de perfiles
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL CHECK (username ~ '^[a-zA-Z0-9_]{3,30}$'),
    stack TEXT[] NOT NULL DEFAULT '{}',
    bio TEXT NOT NULL DEFAULT '' CHECK (char_length(bio) <= 500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);

-- Tabla de mensajes privados
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    sender_id TEXT NOT NULL REFERENCES profiles(user_id),
    recipient_id TEXT NOT NULL REFERENCES profiles(user_id),
    content_encrypted TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (sender_id != recipient_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_recipient_created ON messages(recipient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_sender_created ON messages(sender_id, created_at DESC);

-- Tabla de recursos técnicos
CREATE TABLE IF NOT EXISTS resources (
    id BIGSERIAL PRIMARY KEY,
    author_id TEXT NOT NULL REFERENCES profiles(user_id),
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 3 AND 200),
    url_or_snippet TEXT NOT NULL CHECK (char_length(url_or_snippet) BETWEEN 1 AND 10000),
    tags TEXT[] NOT NULL DEFAULT '{}',
    search_vector TSVECTOR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_resources_tags ON resources USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_resources_search ON resources USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_resources_created ON resources(created_at DESC);

-- Trigger para mantener search_vector actualizado
CREATE OR REPLACE FUNCTION resources_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.url_or_snippet, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_resources_search ON resources;
CREATE TRIGGER trg_resources_search
    BEFORE INSERT OR UPDATE ON resources
    FOR EACH ROW EXECUTE FUNCTION resources_search_trigger();

-- Tabla de reportes
CREATE TABLE IF NOT EXISTS reports (
    id BIGSERIAL PRIMARY KEY,
    reporter_id TEXT NOT NULL REFERENCES profiles(user_id),
    content_type TEXT NOT NULL CHECK (content_type IN ('message', 'resource')),
    content_ref_id BIGINT NOT NULL,
    reason TEXT NOT NULL CHECK (char_length(reason) BETWEEN 10 AND 1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(reporter_id, content_type, content_ref_id)
);

-- Tabla de rate limiting
CREATE TABLE IF NOT EXISTS rate_limits (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup ON rate_limits(user_id, operation, created_at);

-- =============================================================================
-- ROW-LEVEL SECURITY
-- Requirement 9.1: FORCE habilitado en todas las tablas con datos de usuario
-- Requirement 9.6: Sin app.current_user_id → acceso denegado
-- =============================================================================

-- profiles (Req 9.3)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_select ON profiles;
CREATE POLICY profiles_select ON profiles
    FOR SELECT USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND current_setting('app.current_user_id', true) != ''
    );

DROP POLICY IF EXISTS profiles_insert ON profiles;
CREATE POLICY profiles_insert ON profiles
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS profiles_update ON profiles;
CREATE POLICY profiles_update ON profiles
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- messages (Req 9.2)
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS messages_select ON messages;
CREATE POLICY messages_select ON messages
    FOR SELECT USING (
        recipient_id = current_setting('app.current_user_id', true)
        OR sender_id = current_setting('app.current_user_id', true)
    );

DROP POLICY IF EXISTS messages_insert ON messages;
CREATE POLICY messages_insert ON messages
    FOR INSERT WITH CHECK (sender_id = current_setting('app.current_user_id', true));

-- resources (Req 9.5)
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE resources FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS resources_select ON resources;
CREATE POLICY resources_select ON resources
    FOR SELECT USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND current_setting('app.current_user_id', true) != ''
    );

DROP POLICY IF EXISTS resources_insert ON resources;
CREATE POLICY resources_insert ON resources
    FOR INSERT WITH CHECK (author_id = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS resources_update ON resources;
CREATE POLICY resources_update ON resources
    FOR UPDATE USING (author_id = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS resources_delete ON resources;
CREATE POLICY resources_delete ON resources
    FOR DELETE USING (author_id = current_setting('app.current_user_id', true));

-- reports (Req 9.4)
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS reports_select ON reports;
CREATE POLICY reports_select ON reports
    FOR SELECT USING (reporter_id = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS reports_insert ON reports;
CREATE POLICY reports_insert ON reports
    FOR INSERT WITH CHECK (reporter_id = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS reports_update ON reports;
CREATE POLICY reports_update ON reports
    FOR UPDATE USING (reporter_id = current_setting('app.current_user_id', true));

DROP POLICY IF EXISTS reports_delete ON reports;
CREATE POLICY reports_delete ON reports
    FOR DELETE USING (reporter_id = current_setting('app.current_user_id', true));

-- =============================================================================
-- GRANT permisos al rol de aplicación (descomentar en producción)
-- =============================================================================
-- GRANT SELECT, INSERT, UPDATE ON profiles TO app_user;
-- GRANT SELECT, INSERT ON messages TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON resources TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON reports TO app_user;
-- GRANT SELECT, INSERT, DELETE ON rate_limits TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
