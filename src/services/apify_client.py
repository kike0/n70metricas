"""
Cliente de Apify para manejar todas las interacciones con la API
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from apify_client import ApifyClient
from src.config import Config

class ApifyService:
    def __init__(self):
        self.client = ApifyClient(Config.APIFY_API_TOKEN)
        self.actors = Config.APIFY_ACTORS
    
    def run_actor(self, actor_id: str, input_data: Dict[str, Any], wait_for_finish: bool = True) -> Dict[str, Any]:
        """
        Ejecuta un actor de Apify con los datos de entrada especificados
        
        Args:
            actor_id: ID del actor a ejecutar
            input_data: Datos de entrada para el actor
            wait_for_finish: Si esperar a que termine la ejecución
            
        Returns:
            Resultado de la ejecución del actor
        """
        try:
            # Ejecutar el actor
            run = self.client.actor(actor_id).call(run_input=input_data)
            
            if wait_for_finish:
                # Esperar a que termine y obtener los resultados
                dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items
                return {
                    'success': True,
                    'run_id': run['id'],
                    'data': dataset_items,
                    'stats': run.get('stats', {}),
                    'finished_at': run.get('finishedAt'),
                    'started_at': run.get('startedAt')
                }
            else:
                return {
                    'success': True,
                    'run_id': run['id'],
                    'status': 'running'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'actor_id': actor_id
            }
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de una ejecución específica
        """
        try:
            run = self.client.run(run_id).get()
            return {
                'success': True,
                'status': run.get('status'),
                'finished_at': run.get('finishedAt'),
                'stats': run.get('stats', {})
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_run_results(self, run_id: str) -> Dict[str, Any]:
        """
        Obtiene los resultados de una ejecución terminada
        """
        try:
            run = self.client.run(run_id).get()
            if run.get('status') == 'SUCCEEDED':
                dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items
                return {
                    'success': True,
                    'data': dataset_items,
                    'stats': run.get('stats', {})
                }
            else:
                return {
                    'success': False,
                    'error': f"Run not finished or failed. Status: {run.get('status')}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def scrape_facebook_profile(self, profile_url: str, max_posts: int = 50) -> Dict[str, Any]:
        """
        Extrae datos de un perfil de Facebook
        """
        input_data = {
            "startUrls": [{"url": profile_url}],
            "maxPosts": max_posts,
            "scrapeComments": True,
            "scrapeReactions": True
        }
        return self.run_actor(self.actors['facebook_posts'], input_data)
    
    def scrape_instagram_profile(self, username: str, max_posts: int = 50) -> Dict[str, Any]:
        """
        Extrae datos de un perfil de Instagram
        """
        input_data = {
            "usernames": [username],
            "resultsLimit": max_posts,
            "addParentData": True
        }
        return self.run_actor(self.actors['instagram'], input_data)
    
    def scrape_twitter_profile(self, username: str, max_tweets: int = 50) -> Dict[str, Any]:
        """
        Extrae datos de un perfil de Twitter/X
        """
        input_data = {
            "searchTerms": [f"from:{username}"],
            "maxTweets": max_tweets,
            "addUserInfo": True
        }
        return self.run_actor(self.actors['twitter'], input_data)
    
    def scrape_tiktok_profile(self, username: str, max_videos: int = 50) -> Dict[str, Any]:
        """
        Extrae datos de un perfil de TikTok
        """
        input_data = {
            "profiles": [username],
            "resultsPerPage": max_videos
        }
        return self.run_actor(self.actors['tiktok'], input_data)
    
    def scrape_youtube_channel(self, channel_url: str, max_videos: int = 50) -> Dict[str, Any]:
        """
        Extrae datos de un canal de YouTube
        """
        input_data = {
            "startUrls": [{"url": channel_url}],
            "maxVideos": max_videos,
            "scrapeComments": True
        }
        return self.run_actor(self.actors['youtube'], input_data)
    
    def analyze_sentiment(self, profile_name: str) -> Dict[str, Any]:
        """
        Realiza análisis de sentimiento para un perfil en múltiples redes sociales
        """
        input_data = {
            "profileName": profile_name,
            "platforms": ["facebook", "instagram", "tiktok"],
            "maxPosts": 100
        }
        return self.run_actor(self.actors['sentiment_analysis'], input_data)
    
    def search_facebook_mentions(self, keywords: List[str], max_results: int = 100) -> Dict[str, Any]:
        """
        Busca menciones en Facebook
        """
        input_data = {
            "searchQueries": keywords,
            "maxResults": max_results,
            "sortBy": "recent"
        }
        return self.run_actor(self.actors['facebook_mentions'], input_data)
    
    def search_twitter_mentions(self, keywords: List[str], max_results: int = 100) -> Dict[str, Any]:
        """
        Busca menciones en Twitter/X
        """
        input_data = {
            "searchQueries": keywords,
            "maxResults": max_results,
            "sortBy": "recent"
        }
        return self.run_actor(self.actors['twitter_mentions'], input_data)
    
    def scrape_facebook_ads(self, page_name: str, country: str = "MX") -> Dict[str, Any]:
        """
        Extrae anuncios de Facebook Ads Library
        """
        input_data = {
            "searchTerm": page_name,
            "country": country,
            "adType": "political",
            "maxResults": 100
        }
        return self.run_actor(self.actors['facebook_ads'], input_data)

