"""
Rutas de API para generación de reportes
"""
import os
from datetime import datetime, date
from flask import Blueprint, request, jsonify, send_file
from src.models.user import db
from src.models.campaign import Campaign, Report
from src.services.simple_report_generator import SimpleReportGenerator

reports_bp = Blueprint('reports', __name__)
report_generator = SimpleReportGenerator()

@reports_bp.route('/campaigns/<int:campaign_id>/reports', methods=['GET'])
def get_campaign_reports(campaign_id):
    """Obtiene todos los reportes de una campaña"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        reports = Report.query.filter_by(campaign_id=campaign_id).order_by(Report.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict(),
            'reports': [report.to_dict() for report in reports]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@reports_bp.route('/campaigns/<int:campaign_id>/reports', methods=['POST'])
def generate_report(campaign_id):
    """Genera un nuevo reporte para una campaña"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        data = request.get_json()
        
        # Validar fechas
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({
                'success': False, 
                'error': 'start_date y end_date son requeridos'
            }), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400
        
        # Crear registro de reporte
        report_title = data.get('title', f"Reporte {campaign.name} - {start_date} a {end_date}")
        
        report = Report(
            campaign_id=campaign_id,
            title=report_title,
            period_start=start_date,
            period_end=end_date,
            status='generating'
        )
        
        db.session.add(report)
        db.session.commit()
        
        try:
            # Generar reporte HTML
            html_path = report_generator.generate_html_report(
                campaign_id, start_date, end_date
            )
            
            # Actualizar registro con la ruta del HTML
            report.pdf_path = html_path
            report.status = 'completed'
            report.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'report': report.to_dict(),
                'message': 'Reporte generado exitosamente'
            }), 201
            
        except Exception as e:
            # Marcar reporte como fallido
            report.status = 'failed'
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'Error generando reporte: {str(e)}'
            }), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@reports_bp.route('/reports/<int:report_id>/download', methods=['GET'])
def download_report(report_id):
    """Descarga un reporte en PDF"""
    try:
        report = Report.query.get_or_404(report_id)
        
        if not report.pdf_path or not os.path.exists(report.pdf_path):
            return jsonify({
                'success': False, 
                'error': 'Archivo de reporte no encontrado'
            }), 404
        
        return send_file(
            report.pdf_path,
            as_attachment=True,
            download_name=f"{report.title}.html",
            mimetype='text/html'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@reports_bp.route('/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Elimina un reporte"""
    try:
        report = Report.query.get_or_404(report_id)
        
        # Eliminar archivo PDF si existe
        if report.pdf_path and os.path.exists(report.pdf_path):
            os.remove(report.pdf_path)
        
        # Eliminar registro de la base de datos
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reporte eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@reports_bp.route('/campaigns/<int:campaign_id>/quick-report', methods=['POST'])
def generate_quick_report(campaign_id):
    """Genera un reporte rápido con datos de los últimos 30 días"""
    try:
        from datetime import timedelta
        
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Calcular fechas (últimos 30 días)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Generar reporte
        html_path = report_generator.generate_html_report(
            campaign_id, start_date, end_date
        )
        
        # Crear registro de reporte
        report = Report(
            campaign_id=campaign_id,
            title=f"Reporte Rápido {campaign.name} - {start_date} a {end_date}",
            period_start=start_date,
            period_end=end_date,
            pdf_path=html_path,
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'report': report.to_dict(),
            'download_url': f'/api/reports/{report.id}/download'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@reports_bp.route('/test-report', methods=['POST'])
def generate_test_report():
    """Genera un reporte de prueba con datos de ejemplo"""
    try:
        # Crear campaña de prueba si no existe
        test_campaign = Campaign.query.filter_by(name='Campaña de Prueba').first()
        
        if not test_campaign:
            test_campaign = Campaign(
                name='Campaña de Prueba',
                description='Campaña para probar la generación de reportes',
                report_frequency='weekly'
            )
            db.session.add(test_campaign)
            db.session.commit()
        
        # Generar reporte de prueba
        end_date = date.today()
        start_date = date(2024, 3, 1)
        
        html_path = report_generator.generate_html_report(
            test_campaign.id, start_date, end_date
        )
        
        return jsonify({
            'success': True,
            'message': 'Reporte de prueba generado',
            'html_path': html_path,
            'campaign_id': test_campaign.id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

