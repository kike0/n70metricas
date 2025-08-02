"""
Rutas para generación de reportes PDF
"""
import os
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, send_file
from src.models.user import db
from src.models.campaign import Campaign, Report
from src.services.pdf_report_generator import PDFReportGenerator

pdf_reports_bp = Blueprint('pdf_reports', __name__)
pdf_generator = PDFReportGenerator()

@pdf_reports_bp.route('/campaigns/<int:campaign_id>/pdf-report', methods=['POST'])
def generate_pdf_report(campaign_id):
    """Genera un reporte PDF para una campaña específica"""
    try:
        data = request.get_json() or {}
        
        # Obtener fechas del request o usar últimos 7 días por defecto
        if 'start_date' in data and 'end_date' in data:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        else:
            # Últimos 7 días por defecto
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
        
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Crear registro de reporte
        report = Report(
            campaign_id=campaign_id,
            title=f"Reporte PDF {campaign.name} - {start_date} a {end_date}",
            period_start=start_date,
            period_end=end_date,
            status='processing',
            created_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        try:
            # Generar reporte PDF
            pdf_path = pdf_generator.generate_campaign_pdf_report(
                campaign_id, start_date, end_date
            )
            
            # Actualizar registro con la ruta del PDF
            report.pdf_path = pdf_path
            report.status = 'completed'
            report.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'report': report.to_dict(),
                'download_url': f'/api/pdf-reports/{report.id}/download'
            })
            
        except Exception as e:
            report.status = 'failed'
            report.error_message = str(e)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'Error generando reporte: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@pdf_reports_bp.route('/pdf-reports/<int:report_id>/download', methods=['GET'])
def download_pdf_report(report_id):
    """Descarga un reporte PDF generado"""
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
            download_name=f"{report.title}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@pdf_reports_bp.route('/campaigns/<int:campaign_id>/quick-pdf-report', methods=['POST'])
def generate_quick_pdf_report(campaign_id):
    """Genera un reporte PDF rápido (últimos 7 días)"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Calcular fechas (últimos 7 días)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        # Generar reporte
        pdf_path = pdf_generator.generate_campaign_pdf_report(
            campaign_id, start_date, end_date
        )
        
        # Crear registro de reporte
        report = Report(
            campaign_id=campaign_id,
            title=f"Reporte PDF Rápido {campaign.name} - {start_date} a {end_date}",
            period_start=start_date,
            period_end=end_date,
            pdf_path=pdf_path,
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'report': report.to_dict(),
            'download_url': f'/api/pdf-reports/{report.id}/download'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@pdf_reports_bp.route('/generate-ismael-report', methods=['POST'])
def generate_ismael_report():
    """Genera un reporte específico para Ismael Burgueño"""
    try:
        # Buscar la campaña de Ismael Burgueño
        campaign = Campaign.query.filter(
            Campaign.name.like('%Ismael Burgueño%')
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaña de Ismael Burgueño no encontrada'
            }), 404
        
        # Últimos 7 días
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        # Generar reporte PDF
        pdf_path = pdf_generator.generate_campaign_pdf_report(
            campaign.id, start_date, end_date
        )
        
        # Crear registro de reporte
        report = Report(
            campaign_id=campaign.id,
            title=f"Reporte Ismael Burgueño - Últimos 7 días",
            period_start=start_date,
            period_end=end_date,
            pdf_path=pdf_path,
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reporte PDF de Ismael Burgueño generado exitosamente',
            'report': report.to_dict(),
            'download_url': f'/api/pdf-reports/{report.id}/download',
            'pdf_path': pdf_path,
            'campaign_id': campaign.id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

