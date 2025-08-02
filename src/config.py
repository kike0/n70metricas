"""
Configuración del sistema de reportes de redes sociales
"""
import os

class Config:
    # Configuración de Apify
    APIFY_API_TOKEN = "apify_api_aC7n0jeO2hDCGekELZyI4ywlt9ae9H33VRTw"
    APIFY_BASE_URL = "https://api.apify.com/v2"
    
    # Configuración de la base de datos
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de Flask
    SECRET_KEY = 'social_media_reports_secret_key_2024'
    
    # Configuración de reportes
    REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    
    # Actors de Apify para cada red social
    APIFY_ACTORS = {
        'facebook_posts': 'apify/facebook-posts-scraper',
        'facebook_ads': 'easyapi/facebook-ads-library-scraper',
        'instagram': 'apify/instagram-scraper',
        'instagram_posts': 'apify/instagram-post-scraper',
        'twitter': 'apidojo/tweet-scraper-v2',
        'tiktok': 'clockworks/tiktok-scraper',
        'youtube': 'streamers/youtube-scraper',
        'sentiment_analysis': 'tri_angle/social-media-sentiment-analysis-tool',
        'facebook_mentions': 'scraper_one/facebook-posts-search',
        'twitter_mentions': 'scraper_one/x-posts-search'
    }
    
    # Configuración de métricas
    METRICS_CONFIG = {
        'engagement_rate': True,
        'growth_rate': True,
        'sentiment_analysis': True,
        'competitor_analysis': True,
        'ad_performance': True
    }

