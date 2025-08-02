"""
Generador de reportes simplificado para despliegue en producción
"""
import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
from src.config import Config
from src.models.campaign import Campaign, SocialProfile, SocialMetric

class SimpleReportGenerator:
    def __init__(self):
        self.reports_dir = Config.REPORTS_DIR
    
    def generate_campaign_report(self, campaign_id: int, start_date: date, end_date: date) -> str:
        """
        Genera un reporte en formato JSON para una campaña
        
        Args:
            campaign_id: ID de la campaña
            start_date: Fecha de inicio del período
            end_date: Fecha de fin del período
            
        Returns:
            Ruta del archivo JSON generado
        """
        try:
            # Obtener datos de la campaña
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaña {campaign_id} no encontrada")
            
            # Generar nombre del archivo
            filename = f"reporte_{campaign.name.replace(' ', '_')}_{start_date}_{end_date}.json"
            filepath = os.path.join(self.reports_dir, filename)
            
            # Crear estructura del reporte
            report_data = {
                'campaign': {
                    'id': campaign.id,
                    'name': campaign.name,
                    'description': campaign.description,
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'generated_at': datetime.now().isoformat()
                },
                'platforms': [],
                'summary': {
                    'total_followers': 0,
                    'total_posts': 0,
                    'total_interactions': 0,
                    'avg_engagement_rate': 0.0
                }
            }
            
            total_followers = 0
            total_posts = 0
            total_interactions = 0
            total_engagement = 0.0
            platform_count = 0
            
            # Procesar cada perfil de la campaña
            for profile in campaign.profiles:
                if profile.is_active:
                    # Obtener métricas del período
                    metrics = self._get_metrics_for_period(profile.id, start_date, end_date)
                    
                    if metrics:
                        platform_data = {
                            'profile_id': profile.id,
                            'name': profile.name,
                            'platform': profile.platform,
                            'username': profile.username,
                            'metrics': []
                        }
                        
                        latest_metric = metrics[-1] if metrics else None
                        
                        if latest_metric:
                            # Organizar métricas por mes
                            monthly_data = self._organize_metrics_by_month(metrics)
                            
                            platform_data['metrics'] = {
                                'monthly': monthly_data,
                                'latest': {
                                    'followers': latest_metric.followers,
                                    'posts_count': latest_metric.posts_count,
                                    'video_posts_count': latest_metric.video_posts_count,
                                    'total_interactions': latest_metric.total_interactions,
                                    'total_video_interactions': latest_metric.total_video_interactions,
                                    'total_views': latest_metric.total_views,
                                    'followers_growth': latest_metric.followers_growth,
                                    'engagement_rate': latest_metric.engagement_rate
                                }
                            }
                            
                            # Acumular para el resumen
                            total_followers += latest_metric.followers
                            total_posts += latest_metric.posts_count
                            total_interactions += latest_metric.total_interactions
                            total_engagement += latest_metric.engagement_rate
                            platform_count += 1
                        
                        report_data['platforms'].append(platform_data)
            
            # Calcular resumen
            report_data['summary'] = {
                'total_followers': total_followers,
                'total_posts': total_posts,
                'total_interactions': total_interactions,
                'avg_engagement_rate': total_engagement / platform_count if platform_count > 0 else 0.0,
                'platforms_count': platform_count
            }
            
            # Guardar reporte en JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return filepath
            
        except Exception as e:
            raise Exception(f"Error generando reporte: {str(e)}")
    
    def _get_metrics_for_period(self, profile_id: int, start_date: date, end_date: date) -> List[SocialMetric]:
        """Obtiene las métricas para un período específico"""
        return SocialMetric.query.filter(
            SocialMetric.profile_id == profile_id,
            SocialMetric.date >= start_date,
            SocialMetric.date <= end_date
        ).order_by(SocialMetric.date).all()
    
    def _organize_metrics_by_month(self, metrics: List[SocialMetric]) -> Dict:
        """Organiza las métricas por mes"""
        monthly_data = {}
        
        for metric in metrics:
            month_key = metric.date.strftime('%Y-%m')
            month_name = metric.date.strftime('%B')
            
            monthly_data[month_key] = {
                'month_name': month_name,
                'followers': metric.followers,
                'posts_count': metric.posts_count,
                'video_posts_count': metric.video_posts_count,
                'total_interactions': metric.total_interactions,
                'total_video_interactions': metric.total_video_interactions,
                'total_views': metric.total_views,
                'followers_growth': metric.followers_growth,
                'engagement_rate': metric.engagement_rate,
                'date': metric.date.isoformat()
            }
        
        return monthly_data
    
    def generate_html_report(self, campaign_id: int, start_date: date, end_date: date) -> str:
        """
        Genera un reporte en formato HTML
        """
        try:
            # Obtener datos del reporte JSON
            json_path = self.generate_campaign_report(campaign_id, start_date, end_date)
            
            with open(json_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Generar HTML
            html_filename = json_path.replace('.json', '.html')
            
            html_content = self._generate_html_content(report_data)
            
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return html_filename
            
        except Exception as e:
            raise Exception(f"Error generando reporte HTML: {str(e)}")
    
    def _generate_html_content(self, report_data: Dict) -> str:
        """Genera el contenido HTML del reporte"""
        
        campaign = report_data['campaign']
        platforms = report_data['platforms']
        summary = report_data['summary']
        
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Métricas - {campaign['name']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin: 0 0 10px 0;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
            margin: 0;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .summary {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            border-left: 5px solid #2E86AB;
        }}
        
        .summary h2 {{
            color: #2E86AB;
            margin-top: 0;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .summary-item {{
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .summary-item h3 {{
            color: #2E86AB;
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        
        .summary-item p {{
            color: #666;
            margin: 0;
            font-weight: 600;
        }}
        
        .platform {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            border-left: 5px solid #A23B72;
        }}
        
        .platform h2 {{
            color: #A23B72;
            margin-top: 0;
        }}
        
        .platform-info {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .metrics-table th {{
            background: #2E86AB;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: 600;
        }}
        
        .metrics-table td {{
            padding: 12px 15px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}
        
        .metrics-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .metric-label {{
            font-weight: 600;
            color: #333;
            text-align: left !important;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #eee;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Métricas de Redes Sociales</h1>
            <p>{campaign['name']}</p>
            <p>{campaign['period_start']} - {campaign['period_end']}</p>
        </div>
        
        <div class="content">
            <div class="summary">
                <h2>📈 Resumen General</h2>
                <div class="summary-grid">
                    <div class="summary-item">
                        <h3>{summary['total_followers']:,}</h3>
                        <p>Seguidores Totales</p>
                    </div>
                    <div class="summary-item">
                        <h3>{summary['total_posts']:,}</h3>
                        <p>Publicaciones Totales</p>
                    </div>
                    <div class="summary-item">
                        <h3>{summary['total_interactions']:,}</h3>
                        <p>Interacciones Totales</p>
                    </div>
                    <div class="summary-item">
                        <h3>{summary['avg_engagement_rate']:.2f}%</h3>
                        <p>Engagement Promedio</p>
                    </div>
                </div>
            </div>
        """
        
        # Añadir sección para cada plataforma
        for platform in platforms:
            latest = platform['metrics']['latest']
            monthly = platform['metrics']['monthly']
            
            html += f"""
            <div class="platform">
                <h2>📱 {platform['name']} ({platform['platform'].upper()})</h2>
                
                <div class="platform-info">
                    <p><strong>Usuario:</strong> {platform['username'] or 'N/A'}</p>
                    <p><strong>Última actualización:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                
                <table class="metrics-table">
                    <thead>
                        <tr>
                            <th>Métrica</th>
            """
            
            # Añadir headers de meses
            for month_key in sorted(monthly.keys()):
                month_name = monthly[month_key]['month_name']
                html += f"<th>{month_name}</th>"
            
            html += """
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # Añadir filas de métricas
            metrics_rows = [
                ('Seguidores', 'followers'),
                ('Publicaciones', 'posts_count'),
                ('Publicaciones de Video', 'video_posts_count'),
                ('Total Interacciones', 'total_interactions'),
                ('Interacciones de Video', 'total_video_interactions'),
                ('Reproducciones', 'total_views'),
                ('Crecimiento', 'followers_growth'),
                ('Engagement Rate', 'engagement_rate')
            ]
            
            for label, key in metrics_rows:
                html += f'<tr><td class="metric-label">{label}</td>'
                
                for month_key in sorted(monthly.keys()):
                    value = monthly[month_key].get(key, 0)
                    if key == 'engagement_rate':
                        html += f'<td>{value:.2f}%</td>'
                    else:
                        html += f'<td>{value:,}</td>'
                
                html += '</tr>'
            
            html += """
                    </tbody>
                </table>
            </div>
            """
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
            <p>Sistema de Reportes de Redes Sociales con Apify</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html

