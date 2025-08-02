"""
Servicio para generar reportes en PDF similares al formato del ejemplo
"""
import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from src.config import Config
from src.models.campaign import Campaign, SocialProfile, SocialMetric

class ReportGenerator:
    def __init__(self):
        self.reports_dir = Config.REPORTS_DIR
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos personalizados para el reporte"""
        # Estilo para títulos principales
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2E86AB')
        ))
        
        # Estilo para títulos de sección
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#2E86AB')
        ))
        
        # Estilo para subtítulos
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#A23B72')
        ))
    
    def generate_campaign_report(self, campaign_id: int, start_date: date, end_date: date) -> str:
        """
        Genera un reporte completo para una campaña
        
        Args:
            campaign_id: ID de la campaña
            start_date: Fecha de inicio del período
            end_date: Fecha de fin del período
            
        Returns:
            Ruta del archivo PDF generado
        """
        try:
            # Obtener datos de la campaña
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaña {campaign_id} no encontrada")
            
            # Generar nombre del archivo
            filename = f"reporte_{campaign.name.replace(' ', '_')}_{start_date}_{end_date}.pdf"
            filepath = os.path.join(self.reports_dir, filename)
            
            # Crear documento PDF
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []
            
            # Portada
            story.extend(self._create_cover_page(campaign, start_date, end_date))
            story.append(PageBreak())
            
            # Métricas por plataforma
            for profile in campaign.profiles:
                if profile.is_active:
                    story.extend(self._create_platform_section(profile, start_date, end_date))
                    story.append(PageBreak())
            
            # Sección de anuncios (si hay datos)
            story.extend(self._create_ads_section(campaign, start_date, end_date))
            story.append(PageBreak())
            
            # Análisis de sentimiento y menciones
            story.extend(self._create_sentiment_section(campaign, start_date, end_date))
            
            # Construir PDF
            doc.build(story)
            
            return filepath
            
        except Exception as e:
            raise Exception(f"Error generando reporte: {str(e)}")
    
    def _create_cover_page(self, campaign: Campaign, start_date: date, end_date: date) -> List:
        """Crea la página de portada del reporte"""
        elements = []
        
        # Título principal
        title = Paragraph("Métricas", self.styles['MainTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Información de la campaña
        campaign_info = f"""
        <b>Campaña:</b> {campaign.name}<br/>
        <b>Período:</b> {start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')}<br/>
        <b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        
        info_para = Paragraph(campaign_info, self.styles['Normal'])
        elements.append(info_para)
        elements.append(Spacer(1, 1*inch))
        
        return elements
    
    def _create_platform_section(self, profile: SocialProfile, start_date: date, end_date: date) -> List:
        """Crea una sección para una plataforma específica"""
        elements = []
        
        # Título de la plataforma
        platform_title = Paragraph(f"{profile.name}", self.styles['SectionTitle'])
        elements.append(platform_title)
        
        platform_subtitle = Paragraph(f"{profile.platform.upper()}", self.styles['SubTitle'])
        elements.append(platform_subtitle)
        elements.append(Spacer(1, 0.3*inch))
        
        # Obtener métricas del período
        metrics = self._get_metrics_for_period(profile.id, start_date, end_date)
        
        if metrics:
            # Crear tabla de métricas
            table_data = self._create_metrics_table_data(profile.platform, metrics)
            
            # Crear tabla
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Crear gráficos
            chart_path = self._create_engagement_chart(profile, metrics)
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=6*inch, height=3*inch)
                elements.append(img)
                elements.append(Spacer(1, 0.2*inch))
        else:
            no_data = Paragraph("No hay datos disponibles para este período", self.styles['Normal'])
            elements.append(no_data)
        
        return elements
    
    def _create_metrics_table_data(self, platform: str, metrics: List[SocialMetric]) -> List[List]:
        """Crea los datos de la tabla de métricas según la plataforma"""
        if platform.lower() == 'facebook':
            headers = ['', 'Marzo', 'Abril', 'Mayo']
            data = [headers]
            
            # Organizar métricas por mes
            monthly_data = self._organize_metrics_by_month(metrics)
            
            rows = [
                ['Seguidores'] + [str(monthly_data.get(month, {}).get('followers', 0)) for month in ['03', '04', '05']],
                ['Publicaciones'] + [str(monthly_data.get(month, {}).get('posts_count', 0)) for month in ['03', '04', '05']],
                ['Publicaciones de Video'] + [str(monthly_data.get(month, {}).get('video_posts_count', 0)) for month in ['03', '04', '05']],
                ['Reproducciones Total'] + [str(monthly_data.get(month, {}).get('total_views', 0)) for month in ['03', '04', '05']],
                ['Total Interacciones'] + [str(monthly_data.get(month, {}).get('total_interactions', 0)) for month in ['03', '04', '05']],
                ['Total Interacciones de Video'] + [str(monthly_data.get(month, {}).get('total_video_interactions', 0)) for month in ['03', '04', '05']],
                ['Crecimiento'] + [str(monthly_data.get(month, {}).get('followers_growth', 0)) for month in ['03', '04', '05']],
                ['Engagement'] + [f"{monthly_data.get(month, {}).get('engagement_rate', 0):.2f}%" for month in ['03', '04', '05']]
            ]
            
            data.extend(rows)
            
        elif platform.lower() == 'instagram':
            headers = ['', 'Marzo', 'Abril', 'Mayo']
            data = [headers]
            
            monthly_data = self._organize_metrics_by_month(metrics)
            
            rows = [
                ['Seguidores'] + [str(monthly_data.get(month, {}).get('followers', 0)) for month in ['03', '04', '05']],
                ['Publicaciones'] + [str(monthly_data.get(month, {}).get('posts_count', 0)) for month in ['03', '04', '05']],
                ['Total Interacciones'] + [str(monthly_data.get(month, {}).get('total_interactions', 0)) for month in ['03', '04', '05']],
                ['Crecimiento'] + [str(monthly_data.get(month, {}).get('followers_growth', 0)) for month in ['03', '04', '05']],
                ['Engagement'] + [f"{monthly_data.get(month, {}).get('engagement_rate', 0):.2f}%" for month in ['03', '04', '05']]
            ]
            
            data.extend(rows)
            
        else:
            # Formato genérico para otras plataformas
            headers = ['Métrica', 'Valor']
            data = [headers]
            
            if metrics:
                latest_metric = metrics[-1]
                rows = [
                    ['Seguidores', str(latest_metric.followers)],
                    ['Publicaciones', str(latest_metric.posts_count)],
                    ['Total Interacciones', str(latest_metric.total_interactions)],
                    ['Engagement Rate', f"{latest_metric.engagement_rate:.2f}%"]
                ]
                data.extend(rows)
        
        return data
    
    def _organize_metrics_by_month(self, metrics: List[SocialMetric]) -> Dict:
        """Organiza las métricas por mes"""
        monthly_data = {}
        
        for metric in metrics:
            month_key = metric.date.strftime('%m')
            monthly_data[month_key] = {
                'followers': metric.followers,
                'posts_count': metric.posts_count,
                'video_posts_count': metric.video_posts_count,
                'total_interactions': metric.total_interactions,
                'total_video_interactions': metric.total_video_interactions,
                'total_views': metric.total_views,
                'followers_growth': metric.followers_growth,
                'engagement_rate': metric.engagement_rate
            }
        
        return monthly_data
    
    def _get_metrics_for_period(self, profile_id: int, start_date: date, end_date: date) -> List[SocialMetric]:
        """Obtiene las métricas para un período específico"""
        return SocialMetric.query.filter(
            SocialMetric.profile_id == profile_id,
            SocialMetric.date >= start_date,
            SocialMetric.date <= end_date
        ).order_by(SocialMetric.date).all()
    
    def _create_engagement_chart(self, profile: SocialProfile, metrics: List[SocialMetric]) -> str:
        """Crea un gráfico de engagement"""
        try:
            if not metrics:
                return None
            
            # Preparar datos
            dates = [metric.date for metric in metrics]
            engagement_rates = [metric.engagement_rate for metric in metrics]
            
            # Crear gráfico
            plt.figure(figsize=(10, 6))
            plt.plot(dates, engagement_rates, marker='o', linewidth=2, markersize=6)
            plt.title(f'Engagement Rate - {profile.name}', fontsize=14, fontweight='bold')
            plt.xlabel('Fecha')
            plt.ylabel('Engagement Rate (%)')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Guardar gráfico
            chart_filename = f"engagement_{profile.id}_{datetime.now().timestamp()}.png"
            chart_path = os.path.join(self.reports_dir, chart_filename)
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            print(f"Error creando gráfico: {e}")
            return None
    
    def _create_ads_section(self, campaign: Campaign, start_date: date, end_date: date) -> List:
        """Crea la sección de anuncios"""
        elements = []
        
        # Título de sección
        ads_title = Paragraph("Anuncios", self.styles['SectionTitle'])
        elements.append(ads_title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Aquí podrías integrar datos de Facebook Ads Library
        # Por ahora, crear una tabla de ejemplo
        ads_data = [
            ['PARTIDOS', 'ANUNCIOS ACTIVOS', 'ANUNCIOS PAUTADOS EN EL PERIODO', 'MONTO ACUMULADO'],
            [campaign.profiles[0].name if campaign.profiles else 'Perfil 1', '0', '40', '$11,860.00 MXN'],
            [campaign.profiles[1].name if len(campaign.profiles) > 1 else 'Perfil 2', '0', '31', '$48,769.00 MXN']
        ]
        
        ads_table = Table(ads_data)
        ads_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(ads_table)
        elements.append(Spacer(1, 0.5*inch))
        
        return elements
    
    def _create_sentiment_section(self, campaign: Campaign, start_date: date, end_date: date) -> List:
        """Crea la sección de análisis de sentimiento y menciones"""
        elements = []
        
        # Título de sección
        sentiment_title = Paragraph("Sentimiento y Menciones", self.styles['SectionTitle'])
        elements.append(sentiment_title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Aquí integrarías datos reales de análisis de sentimiento
        # Por ahora, crear contenido de ejemplo
        for profile in campaign.profiles[:2]:  # Limitar a 2 perfiles para el ejemplo
            profile_section = f"""
            <b>{profile.name}</b><br/>
            MENCIONES TOTALES: 10.1K | INTERACCIONES TOTALES: 87.6K | USUARIOS ÚNICOS: 2.71k<br/>
            IMPRESIONES EN X: 281M | ALCANCE EN REDES: 10.3M<br/><br/>
            
            1. Menciones relacionadas con actividades públicas y eventos<br/>
            2. Interacciones en redes sociales y engagement con seguidores<br/>
            3. Cobertura mediática y presencia en medios digitales<br/>
            """
            
            profile_para = Paragraph(profile_section, self.styles['Normal'])
            elements.append(profile_para)
            elements.append(Spacer(1, 0.3*inch))
        
        return elements

