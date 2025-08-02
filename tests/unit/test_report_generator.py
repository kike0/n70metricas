"""
Unit Tests for Report Generator
QA-Engineer Implementation - Comprehensive PDF Generation Testing
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
from pathlib import Path

# Import the module under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.report_generator import PDFReportGenerator, ReportError, TemplateError


class TestPDFReportGenerator:
    """Comprehensive unit tests for PDFReportGenerator"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for test outputs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def report_generator(self, temp_output_dir):
        """Create PDFReportGenerator instance for testing"""
        return PDFReportGenerator(output_dir=str(temp_output_dir))
    
    @pytest.fixture
    def sample_campaign_data(self):
        """Sample campaign data for testing"""
        return {
            "id": 1,
            "name": "Test Campaign 2025",
            "description": "Test campaign for unit testing",
            "created_at": "2025-08-01T10:00:00",
            "profiles": [
                {
                    "id": 1,
                    "name": "Test Facebook Page",
                    "platform": "facebook",
                    "url": "https://facebook.com/test"
                },
                {
                    "id": 2,
                    "name": "Test Instagram Account",
                    "platform": "instagram",
                    "url": "https://instagram.com/test"
                }
            ]
        }
    
    @pytest.fixture
    def sample_metrics_data(self):
        """Sample metrics data for testing"""
        return [
            {
                "profile_id": 1,
                "platform": "facebook",
                "metric_date": "2025-07-26",
                "followers": 1000,
                "posts": 20,
                "likes": 500,
                "comments": 100,
                "shares": 50,
                "engagement_rate": 8.5
            },
            {
                "profile_id": 1,
                "platform": "facebook",
                "metric_date": "2025-07-27",
                "followers": 1010,
                "posts": 21,
                "likes": 520,
                "comments": 105,
                "shares": 52,
                "engagement_rate": 8.7
            },
            {
                "profile_id": 2,
                "platform": "instagram",
                "metric_date": "2025-07-26",
                "followers": 1500,
                "posts": 15,
                "likes": 800,
                "comments": 150,
                "shares": 75,
                "engagement_rate": 9.2
            }
        ]
    
    def test_generator_initialization(self, temp_output_dir):
        """Test PDFReportGenerator initialization"""
        # Test with valid output directory
        generator = PDFReportGenerator(output_dir=str(temp_output_dir))
        assert generator.output_dir == str(temp_output_dir)
        assert generator.template_dir is not None
        assert generator.font_size == 12
        
        # Test with custom parameters
        generator = PDFReportGenerator(
            output_dir=str(temp_output_dir),
            font_size=14,
            page_format="A4"
        )
        assert generator.font_size == 14
        assert generator.page_format == "A4"
    
    def test_generator_initialization_invalid_directory(self):
        """Test PDFReportGenerator initialization with invalid directory"""
        with pytest.raises(ValueError, match="Output directory is required"):
            PDFReportGenerator(output_dir="")
        
        with pytest.raises(ValueError, match="Output directory is required"):
            PDFReportGenerator(output_dir=None)
    
    def test_create_output_directory(self, report_generator, temp_output_dir):
        """Test output directory creation"""
        # Test directory creation
        new_dir = temp_output_dir / "new_reports"
        generator = PDFReportGenerator(output_dir=str(new_dir))
        generator._ensure_output_directory()
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_generate_filename(self, report_generator):
        """Test filename generation"""
        # Test with campaign name
        filename = report_generator._generate_filename("Test Campaign")
        assert "test_campaign" in filename.lower()
        assert filename.endswith(".pdf")
        assert datetime.now().strftime("%Y%m%d") in filename
        
        # Test with special characters
        filename = report_generator._generate_filename("Test Campaign! @#$%")
        assert "test_campaign" in filename.lower()
        assert "@#$%" not in filename
    
    def test_validate_data_valid(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test data validation with valid data"""
        # Should not raise any exceptions
        report_generator._validate_data(sample_campaign_data, sample_metrics_data)
    
    def test_validate_data_invalid_campaign(self, report_generator, sample_metrics_data):
        """Test data validation with invalid campaign data"""
        # Missing required fields
        invalid_campaign = {"id": 1}
        
        with pytest.raises(ValueError, match="Campaign data is missing required fields"):
            report_generator._validate_data(invalid_campaign, sample_metrics_data)
    
    def test_validate_data_invalid_metrics(self, report_generator, sample_campaign_data):
        """Test data validation with invalid metrics data"""
        # Empty metrics
        with pytest.raises(ValueError, match="Metrics data cannot be empty"):
            report_generator._validate_data(sample_campaign_data, [])
        
        # Invalid metrics structure
        invalid_metrics = [{"invalid": "data"}]
        with pytest.raises(ValueError, match="Metrics data is missing required fields"):
            report_generator._validate_data(sample_campaign_data, invalid_metrics)
    
    def test_calculate_summary_statistics(self, report_generator, sample_metrics_data):
        """Test summary statistics calculation"""
        stats = report_generator._calculate_summary_statistics(sample_metrics_data)
        
        # Test total calculations
        assert stats["total_followers"] == 2510  # 1010 + 1500
        assert stats["total_posts"] == 36  # 21 + 15
        assert stats["total_likes"] == 1320  # 520 + 800
        
        # Test average calculations
        assert stats["avg_engagement_rate"] == pytest.approx(8.87, rel=1e-2)  # (8.7 + 9.2) / 2
        
        # Test growth calculations
        assert stats["follower_growth"] == 10  # 1010 - 1000 for Facebook
        assert stats["growth_rate"] == pytest.approx(1.0, rel=1e-2)  # 10/1000 * 100
    
    def test_calculate_platform_breakdown(self, report_generator, sample_metrics_data):
        """Test platform breakdown calculation"""
        breakdown = report_generator._calculate_platform_breakdown(sample_metrics_data)
        
        # Test Facebook data
        assert "facebook" in breakdown
        facebook_data = breakdown["facebook"]
        assert facebook_data["followers"] == 1010
        assert facebook_data["engagement_rate"] == 8.7
        
        # Test Instagram data
        assert "instagram" in breakdown
        instagram_data = breakdown["instagram"]
        assert instagram_data["followers"] == 1500
        assert instagram_data["engagement_rate"] == 9.2
    
    def test_generate_charts_data(self, report_generator, sample_metrics_data):
        """Test chart data generation"""
        charts_data = report_generator._generate_charts_data(sample_metrics_data)
        
        # Test engagement chart data
        assert "engagement_chart" in charts_data
        engagement_data = charts_data["engagement_chart"]
        assert len(engagement_data["dates"]) > 0
        assert len(engagement_data["values"]) > 0
        
        # Test followers chart data
        assert "followers_chart" in charts_data
        followers_data = charts_data["followers_chart"]
        assert len(followers_data["dates"]) > 0
        assert len(followers_data["values"]) > 0
    
    @patch('weasyprint.HTML')
    def test_generate_report_success(self, mock_html, report_generator, sample_campaign_data, sample_metrics_data, temp_output_dir):
        """Test successful report generation"""
        # Mock WeasyPrint HTML and PDF generation
        mock_html_instance = Mock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf = Mock()
        
        result = report_generator.generate_report(sample_campaign_data, sample_metrics_data)
        
        assert result["success"] is True
        assert "file_path" in result
        assert result["file_path"].endswith(".pdf")
        assert "file_size" in result
        assert "generation_time" in result
        
        # Verify WeasyPrint was called
        mock_html.assert_called_once()
        mock_html_instance.write_pdf.assert_called_once()
    
    @patch('weasyprint.HTML')
    def test_generate_report_weasyprint_error(self, mock_html, report_generator, sample_campaign_data, sample_metrics_data):
        """Test report generation with WeasyPrint error"""
        # Mock WeasyPrint to raise an exception
        mock_html.side_effect = Exception("WeasyPrint error")
        
        with pytest.raises(ReportError, match="Failed to generate PDF"):
            report_generator.generate_report(sample_campaign_data, sample_metrics_data)
    
    def test_generate_report_invalid_data(self, report_generator):
        """Test report generation with invalid data"""
        invalid_campaign = {}
        invalid_metrics = []
        
        with pytest.raises(ValueError):
            report_generator.generate_report(invalid_campaign, invalid_metrics)
    
    def test_template_rendering(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test HTML template rendering"""
        html_content = report_generator._render_template(sample_campaign_data, sample_metrics_data)
        
        # Verify template contains expected content
        assert sample_campaign_data["name"] in html_content
        assert "Test Campaign 2025" in html_content
        assert "facebook" in html_content.lower()
        assert "instagram" in html_content.lower()
        
        # Verify HTML structure
        assert "<html>" in html_content
        assert "</html>" in html_content
        assert "<body>" in html_content
        assert "</body>" in html_content
    
    def test_template_rendering_missing_template(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test template rendering with missing template file"""
        # Mock template directory to non-existent path
        report_generator.template_dir = "/non/existent/path"
        
        with pytest.raises(TemplateError, match="Template file not found"):
            report_generator._render_template(sample_campaign_data, sample_metrics_data)
    
    def test_css_styling_application(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test CSS styling application"""
        html_content = report_generator._render_template(sample_campaign_data, sample_metrics_data)
        
        # Verify CSS is included
        assert "<style>" in html_content or "stylesheet" in html_content
        
        # Verify styling elements
        assert "font-family" in html_content or "color" in html_content
    
    def test_data_formatting(self, report_generator):
        """Test data formatting functions"""
        # Test number formatting
        assert report_generator._format_number(1000) == "1,000"
        assert report_generator._format_number(1000000) == "1,000,000"
        
        # Test percentage formatting
        assert report_generator._format_percentage(0.085) == "8.5%"
        assert report_generator._format_percentage(0.1234) == "12.3%"
        
        # Test date formatting
        date_str = "2025-08-01"
        formatted = report_generator._format_date(date_str)
        assert "2025" in formatted
        assert "Aug" in formatted or "August" in formatted
    
    def test_error_handling_file_permissions(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test error handling for file permission issues"""
        # Mock file permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(ReportError, match="Permission denied"):
                report_generator.generate_report(sample_campaign_data, sample_metrics_data)
    
    def test_memory_usage_large_dataset(self, report_generator, sample_campaign_data):
        """Test memory usage with large dataset"""
        # Create large metrics dataset
        large_metrics = []
        for i in range(10000):
            large_metrics.append({
                "profile_id": 1,
                "platform": "facebook",
                "metric_date": f"2025-07-{(i % 30) + 1:02d}",
                "followers": 1000 + i,
                "posts": 20 + (i % 10),
                "likes": 500 + (i * 2),
                "comments": 100 + i,
                "shares": 50 + (i % 5),
                "engagement_rate": 8.5 + (i % 100) / 100
            })
        
        # Test that large dataset doesn't cause memory issues
        stats = report_generator._calculate_summary_statistics(large_metrics)
        assert stats is not None
        assert "total_followers" in stats
    
    def test_concurrent_report_generation(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test concurrent report generation"""
        import threading
        import time
        
        results = []
        errors = []
        
        def generate_report():
            try:
                with patch('weasyprint.HTML') as mock_html:
                    mock_html_instance = Mock()
                    mock_html.return_value = mock_html_instance
                    mock_html_instance.write_pdf = Mock()
                    
                    result = report_generator.generate_report(sample_campaign_data, sample_metrics_data)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=generate_report)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(results) == 3
        for result in results:
            assert result["success"] is True
    
    def test_report_metadata(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test report metadata generation"""
        with patch('weasyprint.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html.return_value = mock_html_instance
            mock_html_instance.write_pdf = Mock()
            
            result = report_generator.generate_report(sample_campaign_data, sample_metrics_data)
        
        # Verify metadata is included
        assert "generation_time" in result
        assert "file_size" in result
        assert "campaign_id" in result
        assert "metrics_count" in result
        
        # Verify metadata values
        assert result["campaign_id"] == sample_campaign_data["id"]
        assert result["metrics_count"] == len(sample_metrics_data)
        assert isinstance(result["generation_time"], float)
    
    def test_custom_template_variables(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test custom template variables"""
        # Add custom variables
        custom_vars = {
            "report_title": "Custom Report Title",
            "company_name": "Test Company",
            "logo_url": "https://example.com/logo.png"
        }
        
        html_content = report_generator._render_template(
            sample_campaign_data, 
            sample_metrics_data, 
            custom_vars=custom_vars
        )
        
        # Verify custom variables are included
        assert "Custom Report Title" in html_content
        assert "Test Company" in html_content
        assert "logo.png" in html_content
    
    def test_report_sections_completeness(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test that all required report sections are included"""
        html_content = report_generator._render_template(sample_campaign_data, sample_metrics_data)
        
        # Verify all required sections are present
        required_sections = [
            "Executive Summary",
            "Campaign Overview", 
            "Platform Metrics",
            "Engagement Analysis",
            "Growth Trends",
            "Recommendations"
        ]
        
        for section in required_sections:
            assert section.lower().replace(" ", "") in html_content.lower().replace(" ", "")
    
    @pytest.mark.parametrize("platform,expected_color", [
        ("facebook", "#1877F2"),
        ("instagram", "#E4405F"),
        ("twitter", "#1DA1F2"),
        ("linkedin", "#0A66C2"),
        ("youtube", "#FF0000"),
    ])
    def test_platform_color_coding(self, report_generator, platform, expected_color):
        """Test platform-specific color coding"""
        color = report_generator._get_platform_color(platform)
        assert color == expected_color
    
    def test_performance_benchmarks(self, report_generator, sample_campaign_data, sample_metrics_data, performance_monitor):
        """Test performance benchmarks for report generation"""
        performance_monitor.start()
        
        with patch('weasyprint.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html.return_value = mock_html_instance
            mock_html_instance.write_pdf = Mock()
            
            result = report_generator.generate_report(sample_campaign_data, sample_metrics_data)
        
        metrics = performance_monitor.stop()
        
        # Verify performance is within acceptable limits
        assert metrics['execution_time'] < 5.0  # Should complete in under 5 seconds
        assert result["success"] is True
    
    def test_output_file_integrity(self, report_generator, sample_campaign_data, sample_metrics_data, temp_output_dir):
        """Test output file integrity"""
        with patch('weasyprint.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html.return_value = mock_html_instance
            
            # Mock write_pdf to create actual file
            def mock_write_pdf(file_path):
                with open(file_path, 'wb') as f:
                    f.write(b'%PDF-1.4\nMock PDF content')
            
            mock_html_instance.write_pdf = mock_write_pdf
            
            result = report_generator.generate_report(sample_campaign_data, sample_metrics_data)
        
        # Verify file was created
        assert os.path.exists(result["file_path"])
        
        # Verify file is not empty
        assert os.path.getsize(result["file_path"]) > 0
        
        # Verify file has PDF header
        with open(result["file_path"], 'rb') as f:
            header = f.read(8)
            assert header.startswith(b'%PDF')


class TestReportError:
    """Test custom report exceptions"""
    
    def test_report_error_creation(self):
        """Test ReportError creation"""
        error = ReportError("Test report error")
        assert str(error) == "Test report error"
        assert isinstance(error, Exception)
    
    def test_template_error_creation(self):
        """Test TemplateError creation"""
        error = TemplateError("Template not found")
        assert str(error) == "Template not found"
        assert isinstance(error, ReportError)
        assert isinstance(error, Exception)


class TestReportGeneratorIntegration:
    """Integration-style unit tests for report generation"""
    
    @pytest.fixture
    def report_generator(self, temp_output_dir):
        """Create report generator for integration testing"""
        return PDFReportGenerator(output_dir=str(temp_output_dir))
    
    def test_end_to_end_report_generation(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test complete end-to-end report generation workflow"""
        with patch('weasyprint.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html.return_value = mock_html_instance
            mock_html_instance.write_pdf = Mock()
            
            # Execute complete workflow
            result = report_generator.generate_report(sample_campaign_data, sample_metrics_data)
            
            # Verify complete workflow success
            assert result["success"] is True
            assert all(key in result for key in ["file_path", "file_size", "generation_time"])
            
            # Verify all processing steps were executed
            mock_html.assert_called_once()
            mock_html_instance.write_pdf.assert_called_once()
    
    def test_multiple_reports_same_generator(self, report_generator, sample_campaign_data, sample_metrics_data):
        """Test generating multiple reports with same generator instance"""
        results = []
        
        with patch('weasyprint.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html.return_value = mock_html_instance
            mock_html_instance.write_pdf = Mock()
            
            # Generate multiple reports
            for i in range(3):
                campaign_data = sample_campaign_data.copy()
                campaign_data["name"] = f"Campaign {i+1}"
                
                result = report_generator.generate_report(campaign_data, sample_metrics_data)
                results.append(result)
        
        # Verify all reports were generated successfully
        assert len(results) == 3
        for result in results:
            assert result["success"] is True
        
        # Verify each report has unique filename
        filenames = [result["file_path"] for result in results]
        assert len(set(filenames)) == 3  # All unique


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services.report_generator"])

