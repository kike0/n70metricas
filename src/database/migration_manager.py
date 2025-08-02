"""
Gestor de migración de SQLite a PostgreSQL - SUPABASE-SPECIALIST
"""

import os
import json
import sqlite3
import psycopg2
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

class MigrationManager:
    """Gestor para migrar datos de SQLite a PostgreSQL"""
    
    def __init__(self, sqlite_path, postgresql_url):
        self.sqlite_path = sqlite_path
        self.postgresql_url = postgresql_url
        self.sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
        self.postgresql_engine = create_engine(postgresql_url)
        
    def validate_connections(self):
        """Validar conexiones a ambas bases de datos"""
        try:
            # Probar SQLite
            with self.sqlite_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión a SQLite exitosa")
            
            # Probar PostgreSQL
            with self.postgresql_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión a PostgreSQL exitosa")
            
            return True
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False
    
    def create_postgresql_schema(self):
        """Crear esquema de PostgreSQL"""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with self.postgresql_engine.connect() as conn:
                # Ejecutar el esquema en transacciones separadas
                statements = schema_sql.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            conn.execute(text(statement))
                            conn.commit()
                        except Exception as e:
                            logger.warning(f"Advertencia ejecutando: {statement[:50]}... - {e}")
            
            logger.info("✅ Esquema de PostgreSQL creado")
            return True
        except Exception as e:
            logger.error(f"❌ Error creando esquema: {e}")
            return False
    
    def migrate_users(self):
        """Migrar usuarios de SQLite a PostgreSQL"""
        try:
            # Leer usuarios de SQLite
            with self.sqlite_engine.connect() as sqlite_conn:
                users = sqlite_conn.execute(text("""
                    SELECT id, username, email, created_at, updated_at 
                    FROM user
                """)).fetchall()
            
            if not users:
                logger.info("ℹ️ No hay usuarios para migrar")
                return True
            
            # Insertar en PostgreSQL
            with self.postgresql_engine.connect() as pg_conn:
                for user in users:
                    pg_conn.execute(text("""
                        INSERT INTO auth.users (id, username, email, password_hash, created_at, updated_at)
                        VALUES (:id, :username, :email, 'migrated_password_hash', :created_at, :updated_at)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'created_at': user.created_at or datetime.utcnow(),
                        'updated_at': user.updated_at or datetime.utcnow()
                    })
                pg_conn.commit()
            
            logger.info(f"✅ Migrados {len(users)} usuarios")
            return True
        except Exception as e:
            logger.error(f"❌ Error migrando usuarios: {e}")
            return False
    
    def migrate_campaigns(self):
        """Migrar campañas de SQLite a PostgreSQL"""
        try:
            # Crear organización por defecto si no existe
            org_id = self.create_default_organization()
            
            # Leer campañas de SQLite
            with self.sqlite_engine.connect() as sqlite_conn:
                campaigns = sqlite_conn.execute(text("""
                    SELECT id, name, description, created_at, updated_at, is_active,
                           report_frequency, auto_generate
                    FROM campaigns
                """)).fetchall()
            
            if not campaigns:
                logger.info("ℹ️ No hay campañas para migrar")
                return True
            
            # Insertar en PostgreSQL
            with self.postgresql_engine.connect() as pg_conn:
                for campaign in campaigns:
                    # Generar slug a partir del nombre
                    slug = self.generate_slug(campaign.name)
                    
                    pg_conn.execute(text("""
                        INSERT INTO analytics.campaigns (
                            id, organization_id, created_by, name, description, slug,
                            report_frequency, auto_generate_reports, status, created_at, updated_at
                        )
                        VALUES (
                            :id, :org_id, :created_by, :name, :description, :slug,
                            :report_frequency, :auto_generate, :status, :created_at, :updated_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': campaign.id,
                        'org_id': org_id,
                        'created_by': self.get_default_user_id(),
                        'name': campaign.name,
                        'description': campaign.description,
                        'slug': slug,
                        'report_frequency': campaign.report_frequency or 'weekly',
                        'auto_generate': campaign.auto_generate or False,
                        'status': 'active' if campaign.is_active else 'paused',
                        'created_at': campaign.created_at or datetime.utcnow(),
                        'updated_at': campaign.updated_at or datetime.utcnow()
                    })
                pg_conn.commit()
            
            logger.info(f"✅ Migradas {len(campaigns)} campañas")
            return True
        except Exception as e:
            logger.error(f"❌ Error migrando campañas: {e}")
            return False
    
    def migrate_social_profiles(self):
        """Migrar perfiles sociales"""
        try:
            # Leer perfiles de SQLite
            with self.sqlite_engine.connect() as sqlite_conn:
                profiles = sqlite_conn.execute(text("""
                    SELECT id, campaign_id, name, platform, username, profile_url,
                           max_posts, scrape_comments, scrape_reactions, created_at,
                           last_scraped, is_active
                    FROM social_profiles
                """)).fetchall()
            
            if not profiles:
                logger.info("ℹ️ No hay perfiles para migrar")
                return True
            
            # Insertar en PostgreSQL
            with self.postgresql_engine.connect() as pg_conn:
                for profile in profiles:
                    # Obtener platform_id
                    platform_id = self.get_platform_id(profile.platform)
                    
                    pg_conn.execute(text("""
                        INSERT INTO analytics.social_profiles (
                            id, campaign_id, platform_id, name, username, profile_url,
                            extraction_config, is_active, monitoring_enabled, created_at, updated_at
                        )
                        VALUES (
                            :id, :campaign_id, :platform_id, :name, :username, :profile_url,
                            :extraction_config, :is_active, :monitoring_enabled, :created_at, :updated_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': profile.id,
                        'campaign_id': profile.campaign_id,
                        'platform_id': platform_id,
                        'name': profile.name,
                        'username': profile.username,
                        'profile_url': profile.profile_url,
                        'extraction_config': json.dumps({
                            'max_posts': profile.max_posts or 50,
                            'scrape_comments': profile.scrape_comments or True,
                            'scrape_reactions': profile.scrape_reactions or True
                        }),
                        'is_active': profile.is_active or True,
                        'monitoring_enabled': True,
                        'created_at': profile.created_at or datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                pg_conn.commit()
            
            logger.info(f"✅ Migrados {len(profiles)} perfiles sociales")
            return True
        except Exception as e:
            logger.error(f"❌ Error migrando perfiles: {e}")
            return False
    
    def migrate_metrics(self):
        """Migrar métricas diarias"""
        try:
            # Leer métricas de SQLite
            with self.sqlite_engine.connect() as sqlite_conn:
                metrics = sqlite_conn.execute(text("""
                    SELECT id, profile_id, date, followers, posts_count, video_posts_count,
                           total_interactions, total_video_interactions, total_views,
                           followers_growth, engagement_rate, created_at, apify_run_id
                    FROM social_metrics
                """)).fetchall()
            
            if not metrics:
                logger.info("ℹ️ No hay métricas para migrar")
                return True
            
            # Insertar en PostgreSQL
            with self.postgresql_engine.connect() as pg_conn:
                for metric in metrics:
                    pg_conn.execute(text("""
                        INSERT INTO analytics.daily_metrics (
                            id, profile_id, metric_date, followers_count, posts_count,
                            video_posts_count, total_likes, total_comments, total_shares,
                            total_views, followers_growth, engagement_rate, created_at, updated_at
                        )
                        VALUES (
                            :id, :profile_id, :metric_date, :followers_count, :posts_count,
                            :video_posts_count, :total_interactions, 0, 0,
                            :total_views, :followers_growth, :engagement_rate, :created_at, :updated_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': metric.id,
                        'profile_id': metric.profile_id,
                        'metric_date': metric.date,
                        'followers_count': metric.followers or 0,
                        'posts_count': metric.posts_count or 0,
                        'video_posts_count': metric.video_posts_count or 0,
                        'total_interactions': metric.total_interactions or 0,
                        'total_views': metric.total_views or 0,
                        'followers_growth': metric.followers_growth or 0,
                        'engagement_rate': metric.engagement_rate or 0,
                        'created_at': metric.created_at or datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                pg_conn.commit()
            
            logger.info(f"✅ Migradas {len(metrics)} métricas")
            return True
        except Exception as e:
            logger.error(f"❌ Error migrando métricas: {e}")
            return False
    
    def migrate_reports(self):
        """Migrar reportes"""
        try:
            # Leer reportes de SQLite
            with self.sqlite_engine.connect() as sqlite_conn:
                reports = sqlite_conn.execute(text("""
                    SELECT id, campaign_id, title, period_start, period_end,
                           pdf_path, json_data, status, created_at, completed_at
                    FROM reports
                """)).fetchall()
            
            if not reports:
                logger.info("ℹ️ No hay reportes para migrar")
                return True
            
            # Insertar en PostgreSQL
            with self.postgresql_engine.connect() as pg_conn:
                for report in reports:
                    pg_conn.execute(text("""
                        INSERT INTO analytics.reports (
                            id, campaign_id, created_by, title, period_start, period_end,
                            pdf_file_path, json_data, status, created_at, updated_at, completed_at
                        )
                        VALUES (
                            :id, :campaign_id, :created_by, :title, :period_start, :period_end,
                            :pdf_file_path, :json_data, :status, :created_at, :updated_at, :completed_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': report.id,
                        'campaign_id': report.campaign_id,
                        'created_by': self.get_default_user_id(),
                        'title': report.title,
                        'period_start': report.period_start,
                        'period_end': report.period_end,
                        'pdf_file_path': report.pdf_path,
                        'json_data': report.json_data,
                        'status': report.status or 'completed',
                        'created_at': report.created_at or datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'completed_at': report.completed_at
                    })
                pg_conn.commit()
            
            logger.info(f"✅ Migrados {len(reports)} reportes")
            return True
        except Exception as e:
            logger.error(f"❌ Error migrando reportes: {e}")
            return False
    
    def create_default_organization(self):
        """Crear organización por defecto"""
        try:
            with self.postgresql_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO analytics.organizations (name, slug, description)
                    VALUES ('Organización Migrada', 'migrated-org', 'Organización creada durante la migración')
                    ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                """))
                org_id = result.fetchone()[0]
                conn.commit()
                return org_id
        except Exception as e:
            logger.error(f"Error creando organización por defecto: {e}")
            return None
    
    def get_default_user_id(self):
        """Obtener ID de usuario por defecto"""
        try:
            with self.postgresql_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id FROM auth.users LIMIT 1
                """))
                user = result.fetchone()
                if user:
                    return user[0]
                
                # Crear usuario por defecto si no existe
                result = conn.execute(text("""
                    INSERT INTO auth.users (username, email, password_hash)
                    VALUES ('admin', 'admin@migrated.com', 'migrated_password_hash')
                    ON CONFLICT (email) DO UPDATE SET username = EXCLUDED.username
                    RETURNING id
                """))
                user_id = result.fetchone()[0]
                conn.commit()
                return user_id
        except Exception as e:
            logger.error(f"Error obteniendo usuario por defecto: {e}")
            return None
    
    def get_platform_id(self, platform_name):
        """Obtener ID de plataforma"""
        platform_mapping = {
            'facebook': 1,
            'instagram': 2,
            'twitter': 3,
            'tiktok': 4,
            'youtube': 5,
            'linkedin': 6
        }
        return platform_mapping.get(platform_name.lower(), 1)
    
    def generate_slug(self, name):
        """Generar slug a partir del nombre"""
        import re
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
        slug = re.sub(r'\s+', '-', slug)
        return slug[:100]
    
    def run_full_migration(self):
        """Ejecutar migración completa"""
        logger.info("🚀 Iniciando migración completa de SQLite a PostgreSQL")
        
        steps = [
            ("Validar conexiones", self.validate_connections),
            ("Crear esquema PostgreSQL", self.create_postgresql_schema),
            ("Migrar usuarios", self.migrate_users),
            ("Migrar campañas", self.migrate_campaigns),
            ("Migrar perfiles sociales", self.migrate_social_profiles),
            ("Migrar métricas", self.migrate_metrics),
            ("Migrar reportes", self.migrate_reports)
        ]
        
        for step_name, step_function in steps:
            logger.info(f"📋 {step_name}...")
            if not step_function():
                logger.error(f"❌ Falló: {step_name}")
                return False
        
        logger.info("🎉 Migración completada exitosamente")
        return True

def run_migration_cli():
    """Ejecutar migración desde línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrar datos de SQLite a PostgreSQL')
    parser.add_argument('--sqlite', required=True, help='Ruta al archivo SQLite')
    parser.add_argument('--postgresql', required=True, help='URL de conexión PostgreSQL')
    parser.add_argument('--verbose', action='store_true', help='Logging detallado')
    
    args = parser.parse_args()
    
    # Configurar logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Ejecutar migración
    manager = MigrationManager(args.sqlite, args.postgresql)
    success = manager.run_full_migration()
    
    if success:
        print("✅ Migración completada exitosamente")
        return 0
    else:
        print("❌ Migración falló")
        return 1

if __name__ == '__main__':
    exit(run_migration_cli())

