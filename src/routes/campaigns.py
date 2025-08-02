"""
Rutas de API para gestión de campañas de monitoreo
"""
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.campaign import Campaign, SocialProfile, SocialMetric, Report
from src.services.apify_client import ApifyService

campaigns_bp = Blueprint('campaigns', __name__)
apify_service = ApifyService()

@campaigns_bp.route('/campaigns', methods=['GET'])
def get_campaigns():
    """Obtiene todas las campañas"""
    try:
        campaigns = Campaign.query.all()
        return jsonify({
            'success': True,
            'campaigns': [campaign.to_dict() for campaign in campaigns]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@campaigns_bp.route('/campaigns', methods=['POST'])
def create_campaign():
    """Crea una nueva campaña"""
    try:
        data = request.get_json()
        
        campaign = Campaign(
            name=data.get('name'),
            description=data.get('description', ''),
            report_frequency=data.get('report_frequency', 'weekly'),
            auto_generate=data.get('auto_generate', False)
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@campaigns_bp.route('/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Obtiene una campaña específica"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict(),
            'profiles': [profile.to_dict() for profile in campaign.profiles]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@campaigns_bp.route('/campaigns/<int:campaign_id>/profiles', methods=['POST'])
def add_profile_to_campaign(campaign_id):
    """Añade un perfil de red social a una campaña"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        data = request.get_json()
        
        profile = SocialProfile(
            campaign_id=campaign_id,
            name=data.get('name'),
            platform=data.get('platform'),
            username=data.get('username'),
            profile_url=data.get('profile_url'),
            max_posts=data.get('max_posts', 50),
            scrape_comments=data.get('scrape_comments', True),
            scrape_reactions=data.get('scrape_reactions', True)
        )
        
        db.session.add(profile)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'profile': profile.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@campaigns_bp.route('/profiles/<int:profile_id>/scrape', methods=['POST'])
def scrape_profile(profile_id):
    """Ejecuta scraping para un perfil específico"""
    try:
        profile = SocialProfile.query.get_or_404(profile_id)
        
        # Ejecutar scraping según la plataforma
        result = None
        if profile.platform == 'facebook':
            result = apify_service.scrape_facebook_profile(
                profile.profile_url, 
                profile.max_posts
            )
        elif profile.platform == 'instagram':
            result = apify_service.scrape_instagram_profile(
                profile.username, 
                profile.max_posts
            )
        elif profile.platform == 'twitter':
            result = apify_service.scrape_twitter_profile(
                profile.username, 
                profile.max_posts
            )
        elif profile.platform == 'tiktok':
            result = apify_service.scrape_tiktok_profile(
                profile.username, 
                profile.max_posts
            )
        elif profile.platform == 'youtube':
            result = apify_service.scrape_youtube_channel(
                profile.profile_url, 
                profile.max_posts
            )
        else:
            return jsonify({
                'success': False, 
                'error': f'Plataforma no soportada: {profile.platform}'
            }), 400
        
        if result and result.get('success'):
            # Actualizar timestamp de último scraping
            profile.last_scraped = datetime.utcnow()
            db.session.commit()
            
            # Procesar y guardar métricas
            metrics_data = _process_scraping_results(profile, result)
            
            return jsonify({
                'success': True,
                'run_id': result.get('run_id'),
                'metrics': metrics_data,
                'data_count': len(result.get('data', []))
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Error desconocido en scraping')
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@campaigns_bp.route('/campaigns/<int:campaign_id>/scrape-all', methods=['POST'])
def scrape_all_profiles(campaign_id):
    """Ejecuta scraping para todos los perfiles de una campaña"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        results = []
        
        for profile in campaign.profiles:
            if profile.is_active:
                # Aquí podrías implementar scraping asíncrono para mejor rendimiento
                result = scrape_profile(profile.id)
                results.append({
                    'profile_id': profile.id,
                    'profile_name': profile.name,
                    'platform': profile.platform,
                    'result': result[0].get_json() if hasattr(result[0], 'get_json') else result
                })
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@campaigns_bp.route('/profiles/<int:profile_id>/metrics', methods=['GET'])
def get_profile_metrics(profile_id):
    """Obtiene las métricas históricas de un perfil"""
    try:
        profile = SocialProfile.query.get_or_404(profile_id)
        
        # Parámetros de consulta
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = SocialMetric.query.filter_by(profile_id=profile_id)
        
        if start_date:
            query = query.filter(SocialMetric.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(SocialMetric.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        metrics = query.order_by(SocialMetric.date.desc()).all()
        
        return jsonify({
            'success': True,
            'profile': profile.to_dict(),
            'metrics': [metric.to_dict() for metric in metrics]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _process_scraping_results(profile, scraping_result):
    """Procesa los resultados del scraping y calcula métricas"""
    try:
        data = scraping_result.get('data', [])
        today = date.today()
        
        # Calcular métricas básicas según la plataforma
        metrics = {
            'followers': 0,
            'posts_count': len(data),
            'video_posts_count': 0,
            'total_interactions': 0,
            'total_video_interactions': 0,
            'total_views': 0
        }
        
        # Procesar datos según la plataforma
        if profile.platform == 'facebook':
            for post in data:
                metrics['total_interactions'] += post.get('likes', 0) + post.get('comments', 0) + post.get('shares', 0)
                if post.get('type') == 'video':
                    metrics['video_posts_count'] += 1
                    metrics['total_video_interactions'] += post.get('likes', 0) + post.get('comments', 0)
                    metrics['total_views'] += post.get('views', 0)
        
        elif profile.platform == 'instagram':
            for post in data:
                metrics['total_interactions'] += post.get('likesCount', 0) + post.get('commentsCount', 0)
                if post.get('type') == 'Video':
                    metrics['video_posts_count'] += 1
                    metrics['total_video_interactions'] += post.get('likesCount', 0) + post.get('commentsCount', 0)
                    metrics['total_views'] += post.get('viewsCount', 0)
        
        elif profile.platform == 'twitter':
            for tweet in data:
                metrics['total_interactions'] += tweet.get('likes', 0) + tweet.get('retweets', 0) + tweet.get('replies', 0)
                if tweet.get('isVideo'):
                    metrics['video_posts_count'] += 1
                    metrics['total_views'] += tweet.get('views', 0)
        
        elif profile.platform == 'tiktok':
            for video in data:
                metrics['total_interactions'] += video.get('likesCount', 0) + video.get('commentsCount', 0) + video.get('sharesCount', 0)
                metrics['video_posts_count'] += 1
                metrics['total_video_interactions'] = metrics['total_interactions']
                metrics['total_views'] += video.get('viewsCount', 0)
        
        # Calcular engagement rate
        if metrics['followers'] > 0:
            metrics['engagement_rate'] = (metrics['total_interactions'] / metrics['followers']) * 100
        
        # Buscar métrica anterior para calcular crecimiento
        previous_metric = SocialMetric.query.filter_by(profile_id=profile.id).order_by(SocialMetric.date.desc()).first()
        followers_growth = 0
        if previous_metric:
            followers_growth = metrics['followers'] - previous_metric.followers
        
        # Guardar métricas en la base de datos
        metric = SocialMetric(
            profile_id=profile.id,
            date=today,
            followers=metrics['followers'],
            posts_count=metrics['posts_count'],
            video_posts_count=metrics['video_posts_count'],
            total_interactions=metrics['total_interactions'],
            total_video_interactions=metrics['total_video_interactions'],
            total_views=metrics['total_views'],
            followers_growth=followers_growth,
            engagement_rate=metrics['engagement_rate'],
            apify_run_id=scraping_result.get('run_id')
        )
        
        db.session.add(metric)
        db.session.commit()
        
        return metric.to_dict()
        
    except Exception as e:
        db.session.rollback()
        raise e

