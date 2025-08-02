-- =====================================================
-- ESQUEMA OPTIMIZADO POSTGRESQL - SUPABASE-SPECIALIST
-- Sistema de Reportes de Redes Sociales
-- =====================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- =====================================================
-- ESQUEMAS
-- =====================================================

CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- =====================================================
-- TABLAS DE AUTENTICACIÓN
-- =====================================================

CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    
    -- Configuración de usuario
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'es',
    theme VARCHAR(20) DEFAULT 'light',
    
    -- Estado de la cuenta
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Índices
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE TABLE auth.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- TABLAS PRINCIPALES DE ANALYTICS
-- =====================================================

CREATE TABLE analytics.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    logo_url TEXT,
    website_url TEXT,
    
    -- Configuración
    timezone VARCHAR(50) DEFAULT 'UTC',
    default_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Límites y cuotas
    max_campaigns INTEGER DEFAULT 10,
    max_profiles_per_campaign INTEGER DEFAULT 50,
    max_monthly_extractions INTEGER DEFAULT 1000,
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    subscription_tier VARCHAR(20) DEFAULT 'basic',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE analytics.organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES analytics.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    permissions JSONB DEFAULT '{}',
    invited_by UUID REFERENCES auth.users(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(organization_id, user_id)
);

CREATE TABLE analytics.campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES analytics.organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    
    -- Información básica
    name VARCHAR(200) NOT NULL,
    description TEXT,
    slug VARCHAR(100) NOT NULL,
    
    -- Configuración de monitoreo
    monitoring_frequency VARCHAR(20) DEFAULT 'daily', -- hourly, daily, weekly
    auto_generate_reports BOOLEAN DEFAULT false,
    report_frequency VARCHAR(20) DEFAULT 'weekly', -- daily, weekly, monthly
    
    -- Configuración de extracción
    max_posts_per_profile INTEGER DEFAULT 100,
    extract_comments BOOLEAN DEFAULT true,
    extract_reactions BOOLEAN DEFAULT true,
    extract_shares BOOLEAN DEFAULT true,
    sentiment_analysis BOOLEAN DEFAULT true,
    
    -- Período de análisis
    analysis_start_date DATE,
    analysis_end_date DATE,
    
    -- Estado
    status VARCHAR(20) DEFAULT 'active', -- active, paused, archived
    is_public BOOLEAN DEFAULT false,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_extraction_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(organization_id, slug)
);

CREATE TABLE analytics.social_platforms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    icon_url TEXT,
    base_url TEXT,
    api_rate_limit INTEGER DEFAULT 100,
    supports_comments BOOLEAN DEFAULT true,
    supports_reactions BOOLEAN DEFAULT true,
    supports_shares BOOLEAN DEFAULT true,
    supports_video_metrics BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true
);

-- Insertar plataformas soportadas
INSERT INTO analytics.social_platforms (name, display_name, base_url, supports_video_metrics) VALUES
('facebook', 'Facebook', 'https://facebook.com', true),
('instagram', 'Instagram', 'https://instagram.com', true),
('twitter', 'Twitter/X', 'https://twitter.com', true),
('tiktok', 'TikTok', 'https://tiktok.com', true),
('youtube', 'YouTube', 'https://youtube.com', true),
('linkedin', 'LinkedIn', 'https://linkedin.com', false);

CREATE TABLE analytics.social_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES analytics.campaigns(id) ON DELETE CASCADE,
    platform_id INTEGER NOT NULL REFERENCES analytics.social_platforms(id),
    
    -- Información del perfil
    name VARCHAR(200) NOT NULL,
    username VARCHAR(200),
    profile_url TEXT NOT NULL,
    profile_id VARCHAR(200), -- ID interno de la plataforma
    
    -- Configuración específica
    extraction_config JSONB DEFAULT '{}',
    custom_fields JSONB DEFAULT '{}',
    
    -- Estado de monitoreo
    is_active BOOLEAN DEFAULT true,
    monitoring_enabled BOOLEAN DEFAULT true,
    last_successful_extraction TIMESTAMP WITH TIME ZONE,
    last_failed_extraction TIMESTAMP WITH TIME ZONE,
    consecutive_failures INTEGER DEFAULT 0,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(campaign_id, platform_id, username)
);

-- =====================================================
-- TABLAS DE MÉTRICAS Y DATOS
-- =====================================================

CREATE TABLE analytics.extraction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES analytics.campaigns(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES analytics.social_profiles(id) ON DELETE CASCADE,
    
    -- Información del job
    job_type VARCHAR(50) NOT NULL, -- full_extraction, incremental, metrics_only
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    
    -- Configuración de Apify
    apify_actor_id VARCHAR(100),
    apify_run_id VARCHAR(100),
    apify_task_id VARCHAR(100),
    
    -- Progreso y resultados
    total_profiles INTEGER DEFAULT 0,
    processed_profiles INTEGER DEFAULT 0,
    extracted_posts INTEGER DEFAULT 0,
    extracted_comments INTEGER DEFAULT 0,
    
    -- Tiempos
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    estimated_completion TIMESTAMP WITH TIME ZONE,
    
    -- Errores y logs
    error_message TEXT,
    error_details JSONB,
    execution_log JSONB DEFAULT '[]',
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE analytics.daily_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES analytics.social_profiles(id) ON DELETE CASCADE,
    extraction_job_id UUID REFERENCES analytics.extraction_jobs(id),
    
    -- Fecha de la métrica
    metric_date DATE NOT NULL,
    
    -- Métricas de audiencia
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    followers_growth INTEGER DEFAULT 0,
    
    -- Métricas de contenido
    posts_count INTEGER DEFAULT 0,
    video_posts_count INTEGER DEFAULT 0,
    image_posts_count INTEGER DEFAULT 0,
    text_posts_count INTEGER DEFAULT 0,
    
    -- Métricas de engagement
    total_likes INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    total_reactions INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    
    -- Métricas calculadas
    engagement_rate DECIMAL(5,4) DEFAULT 0,
    avg_likes_per_post DECIMAL(10,2) DEFAULT 0,
    avg_comments_per_post DECIMAL(10,2) DEFAULT 0,
    avg_shares_per_post DECIMAL(10,2) DEFAULT 0,
    
    -- Métricas específicas de video
    video_views INTEGER DEFAULT 0,
    video_completion_rate DECIMAL(5,4) DEFAULT 0,
    avg_watch_time INTEGER DEFAULT 0, -- en segundos
    
    -- Datos adicionales
    top_performing_post_id VARCHAR(200),
    top_performing_post_engagement INTEGER DEFAULT 0,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(profile_id, metric_date)
);

CREATE TABLE analytics.posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES analytics.social_profiles(id) ON DELETE CASCADE,
    extraction_job_id UUID REFERENCES analytics.extraction_jobs(id),
    
    -- Identificadores de la plataforma
    platform_post_id VARCHAR(200) NOT NULL,
    platform_url TEXT,
    
    -- Contenido del post
    content TEXT,
    content_type VARCHAR(50), -- text, image, video, carousel, story
    media_urls JSONB DEFAULT '[]',
    hashtags JSONB DEFAULT '[]',
    mentions JSONB DEFAULT '[]',
    
    -- Métricas del post
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    reactions_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    
    -- Métricas específicas de video
    video_duration INTEGER, -- en segundos
    video_views INTEGER DEFAULT 0,
    video_completion_rate DECIMAL(5,4),
    
    -- Análisis de sentimiento
    sentiment_score DECIMAL(3,2), -- -1 a 1
    sentiment_label VARCHAR(20), -- positive, negative, neutral
    sentiment_confidence DECIMAL(3,2), -- 0 a 1
    
    -- Fechas
    published_at TIMESTAMP WITH TIME ZONE,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    is_deleted BOOLEAN DEFAULT false,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(profile_id, platform_post_id)
);

CREATE TABLE analytics.comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES analytics.posts(id) ON DELETE CASCADE,
    
    -- Identificadores
    platform_comment_id VARCHAR(200) NOT NULL,
    parent_comment_id UUID REFERENCES analytics.comments(id),
    
    -- Contenido
    content TEXT NOT NULL,
    author_name VARCHAR(200),
    author_username VARCHAR(200),
    author_profile_url TEXT,
    
    -- Métricas
    likes_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    
    -- Análisis de sentimiento
    sentiment_score DECIMAL(3,2),
    sentiment_label VARCHAR(20),
    sentiment_confidence DECIMAL(3,2),
    
    -- Fechas
    published_at TIMESTAMP WITH TIME ZONE,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    is_spam BOOLEAN DEFAULT false,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(post_id, platform_comment_id)
);

-- =====================================================
-- TABLAS DE REPORTES
-- =====================================================

CREATE TABLE analytics.reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES analytics.campaigns(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    
    -- Información del reporte
    title VARCHAR(300) NOT NULL,
    description TEXT,
    report_type VARCHAR(50) DEFAULT 'standard', -- standard, custom, automated
    
    -- Período del reporte
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Configuración
    include_sentiment BOOLEAN DEFAULT true,
    include_top_posts BOOLEAN DEFAULT true,
    include_comments_analysis BOOLEAN DEFAULT false,
    top_posts_count INTEGER DEFAULT 3,
    
    -- Archivos generados
    pdf_file_path TEXT,
    json_data JSONB,
    excel_file_path TEXT,
    
    -- Estado de generación
    status VARCHAR(20) DEFAULT 'pending', -- pending, generating, completed, failed
    generation_progress INTEGER DEFAULT 0, -- 0-100
    
    -- Estadísticas del reporte
    total_profiles INTEGER DEFAULT 0,
    total_posts INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Configuración de acceso
    is_public BOOLEAN DEFAULT false,
    share_token VARCHAR(100) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE analytics.report_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES analytics.reports(id) ON DELETE CASCADE,
    
    -- Información de la sección
    section_type VARCHAR(50) NOT NULL, -- summary, metrics, top_posts, sentiment, growth
    title VARCHAR(200) NOT NULL,
    order_index INTEGER NOT NULL,
    
    -- Contenido
    content JSONB NOT NULL,
    chart_config JSONB,
    
    -- Estado
    is_visible BOOLEAN DEFAULT true,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- TABLAS DE MONITOREO Y LOGS
-- =====================================================

CREATE TABLE monitoring.system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    metric_unit VARCHAR(20),
    tags JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE monitoring.api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES analytics.organizations(id),
    user_id UUID REFERENCES auth.users(id),
    
    -- Información de la API
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    
    -- Request info
    ip_address INET,
    user_agent TEXT,
    request_size INTEGER,
    response_size INTEGER,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE monitoring.error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL, -- ERROR, WARNING, INFO
    message TEXT NOT NULL,
    error_code VARCHAR(50),
    stack_trace TEXT,
    context JSONB DEFAULT '{}',
    
    -- Asociaciones
    user_id UUID REFERENCES auth.users(id),
    organization_id UUID REFERENCES analytics.organizations(id),
    campaign_id UUID REFERENCES analytics.campaigns(id),
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ÍNDICES OPTIMIZADOS
-- =====================================================

-- Índices para autenticación
CREATE INDEX idx_users_email ON auth.users(email);
CREATE INDEX idx_users_username ON auth.users(username);
CREATE INDEX idx_users_active ON auth.users(is_active) WHERE is_active = true;
CREATE INDEX idx_user_sessions_token ON auth.user_sessions(token_hash);
CREATE INDEX idx_user_sessions_expires ON auth.user_sessions(expires_at);

-- Índices para organizaciones y campañas
CREATE INDEX idx_organizations_slug ON analytics.organizations(slug);
CREATE INDEX idx_organizations_active ON analytics.organizations(is_active) WHERE is_active = true;
CREATE INDEX idx_campaigns_org_id ON analytics.campaigns(organization_id);
CREATE INDEX idx_campaigns_status ON analytics.campaigns(status);
CREATE INDEX idx_campaigns_slug ON analytics.campaigns(organization_id, slug);

-- Índices para perfiles sociales
CREATE INDEX idx_social_profiles_campaign ON analytics.social_profiles(campaign_id);
CREATE INDEX idx_social_profiles_platform ON analytics.social_profiles(platform_id);
CREATE INDEX idx_social_profiles_active ON analytics.social_profiles(is_active) WHERE is_active = true;
CREATE INDEX idx_social_profiles_username ON analytics.social_profiles(username);

-- Índices para métricas diarias (particionado por fecha)
CREATE INDEX idx_daily_metrics_profile_date ON analytics.daily_metrics(profile_id, metric_date DESC);
CREATE INDEX idx_daily_metrics_date ON analytics.daily_metrics(metric_date DESC);
CREATE INDEX idx_daily_metrics_engagement ON analytics.daily_metrics(engagement_rate DESC);

-- Índices para posts
CREATE INDEX idx_posts_profile_id ON analytics.posts(profile_id);
CREATE INDEX idx_posts_published_at ON analytics.posts(published_at DESC);
CREATE INDEX idx_posts_platform_id ON analytics.posts(profile_id, platform_post_id);
CREATE INDEX idx_posts_engagement ON analytics.posts(likes_count + comments_count + shares_count DESC);
CREATE INDEX idx_posts_content_search ON analytics.posts USING gin(to_tsvector('spanish', content));

-- Índices para comentarios
CREATE INDEX idx_comments_post_id ON analytics.comments(post_id);
CREATE INDEX idx_comments_published_at ON analytics.comments(published_at DESC);
CREATE INDEX idx_comments_sentiment ON analytics.comments(sentiment_label);

-- Índices para reportes
CREATE INDEX idx_reports_campaign_id ON analytics.reports(campaign_id);
CREATE INDEX idx_reports_created_at ON analytics.reports(created_at DESC);
CREATE INDEX idx_reports_status ON analytics.reports(status);
CREATE INDEX idx_reports_share_token ON analytics.reports(share_token) WHERE share_token IS NOT NULL;

-- Índices para jobs de extracción
CREATE INDEX idx_extraction_jobs_campaign ON analytics.extraction_jobs(campaign_id);
CREATE INDEX idx_extraction_jobs_status ON analytics.extraction_jobs(status);
CREATE INDEX idx_extraction_jobs_created_at ON analytics.extraction_jobs(created_at DESC);

-- Índices para monitoreo
CREATE INDEX idx_system_metrics_name_time ON monitoring.system_metrics(metric_name, recorded_at DESC);
CREATE INDEX idx_api_usage_org_time ON monitoring.api_usage(organization_id, created_at DESC);
CREATE INDEX idx_error_logs_level_time ON monitoring.error_logs(level, created_at DESC);

-- =====================================================
-- FUNCIONES Y TRIGGERS
-- =====================================================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON analytics.organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON analytics.campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_social_profiles_updated_at BEFORE UPDATE ON analytics.social_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_daily_metrics_updated_at BEFORE UPDATE ON analytics.daily_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON analytics.posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON analytics.reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_extraction_jobs_updated_at BEFORE UPDATE ON analytics.extraction_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función para calcular engagement rate automáticamente
CREATE OR REPLACE FUNCTION calculate_engagement_rate()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.followers_count > 0 THEN
        NEW.engagement_rate = (NEW.total_likes + NEW.total_comments + NEW.total_shares)::DECIMAL / NEW.followers_count;
    ELSE
        NEW.engagement_rate = 0;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_daily_metrics_engagement BEFORE INSERT OR UPDATE ON analytics.daily_metrics FOR EACH ROW EXECUTE FUNCTION calculate_engagement_rate();

-- =====================================================
-- VISTAS OPTIMIZADAS
-- =====================================================

-- Vista para métricas de campaña consolidadas
CREATE VIEW analytics.campaign_metrics_summary AS
SELECT 
    c.id as campaign_id,
    c.name as campaign_name,
    COUNT(DISTINCT sp.id) as total_profiles,
    COUNT(DISTINCT p.id) as total_posts,
    SUM(dm.total_likes + dm.total_comments + dm.total_shares) as total_interactions,
    AVG(dm.engagement_rate) as avg_engagement_rate,
    SUM(dm.followers_count) as total_followers,
    MAX(dm.metric_date) as last_metric_date
FROM analytics.campaigns c
LEFT JOIN analytics.social_profiles sp ON c.id = sp.campaign_id
LEFT JOIN analytics.daily_metrics dm ON sp.id = dm.profile_id
LEFT JOIN analytics.posts p ON sp.id = p.profile_id
WHERE c.status = 'active'
GROUP BY c.id, c.name;

-- Vista para top posts por campaña
CREATE VIEW analytics.top_posts_by_campaign AS
SELECT 
    c.id as campaign_id,
    c.name as campaign_name,
    sp.name as profile_name,
    sp.platform_id,
    p.id as post_id,
    p.content,
    p.likes_count + p.comments_count + p.shares_count as total_engagement,
    p.published_at,
    ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY (p.likes_count + p.comments_count + p.shares_count) DESC) as rank
FROM analytics.campaigns c
JOIN analytics.social_profiles sp ON c.id = sp.campaign_id
JOIN analytics.posts p ON sp.id = p.profile_id
WHERE p.is_active = true AND p.published_at >= NOW() - INTERVAL '30 days';

-- Vista para análisis de sentimiento por campaña
CREATE VIEW analytics.sentiment_analysis_summary AS
SELECT 
    c.id as campaign_id,
    c.name as campaign_name,
    COUNT(CASE WHEN p.sentiment_label = 'positive' THEN 1 END) as positive_posts,
    COUNT(CASE WHEN p.sentiment_label = 'negative' THEN 1 END) as negative_posts,
    COUNT(CASE WHEN p.sentiment_label = 'neutral' THEN 1 END) as neutral_posts,
    AVG(p.sentiment_score) as avg_sentiment_score,
    COUNT(p.id) as total_posts_with_sentiment
FROM analytics.campaigns c
JOIN analytics.social_profiles sp ON c.id = sp.campaign_id
JOIN analytics.posts p ON sp.id = p.profile_id
WHERE p.sentiment_score IS NOT NULL
GROUP BY c.id, c.name;

-- =====================================================
-- POLÍTICAS DE SEGURIDAD (RLS)
-- =====================================================

-- Habilitar RLS en tablas sensibles
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.social_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.reports ENABLE ROW LEVEL SECURITY;

-- Política para usuarios (solo pueden ver su propia información)
CREATE POLICY users_own_data ON auth.users
    FOR ALL USING (id = current_setting('app.current_user_id')::UUID);

-- Política para organizaciones (solo miembros pueden acceder)
CREATE POLICY organization_members_access ON analytics.organizations
    FOR ALL USING (
        id IN (
            SELECT organization_id 
            FROM analytics.organization_members 
            WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- =====================================================
-- DATOS INICIALES
-- =====================================================

-- Crear organización por defecto
INSERT INTO analytics.organizations (id, name, slug, description) 
VALUES (
    uuid_generate_v4(),
    'Organización Demo',
    'demo-org',
    'Organización de demostración para el sistema de reportes'
);

-- =====================================================
-- COMENTARIOS Y DOCUMENTACIÓN
-- =====================================================

COMMENT ON SCHEMA analytics IS 'Esquema principal para datos de analytics y reportes de redes sociales';
COMMENT ON SCHEMA auth IS 'Esquema para autenticación y gestión de usuarios';
COMMENT ON SCHEMA monitoring IS 'Esquema para monitoreo del sistema y logs';

COMMENT ON TABLE analytics.campaigns IS 'Campañas de monitoreo de redes sociales';
COMMENT ON TABLE analytics.social_profiles IS 'Perfiles de redes sociales a monitorear';
COMMENT ON TABLE analytics.daily_metrics IS 'Métricas diarias agregadas por perfil';
COMMENT ON TABLE analytics.posts IS 'Posts individuales extraídos de redes sociales';
COMMENT ON TABLE analytics.comments IS 'Comentarios de posts con análisis de sentimiento';
COMMENT ON TABLE analytics.reports IS 'Reportes generados del sistema';

-- =====================================================
-- FINALIZACIÓN
-- =====================================================

-- Crear usuario de aplicación con permisos limitados
-- CREATE USER app_user WITH PASSWORD 'secure_password_here';
-- GRANT USAGE ON SCHEMA analytics, auth, monitoring TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO app_user;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA auth TO app_user;
-- GRANT INSERT ON ALL TABLES IN SCHEMA monitoring TO app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA analytics, auth, monitoring TO app_user;

COMMIT;

