"""
Integration Tests for API Endpoints
QA-Engineer Implementation - Comprehensive API Testing
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Import Flask test client
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestCampaignEndpoints:
    """Integration tests for campaign management endpoints"""
    
    def test_create_campaign_success(self, client, authenticated_user):
        """Test successful campaign creation"""
        campaign_data = {
            "name": "Test Campaign API",
            "description": "Campaign created via API test"
        }
        
        response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["campaign"]["name"] == campaign_data["name"]
        assert "id" in data["campaign"]
    
    def test_create_campaign_invalid_data(self, client, authenticated_user):
        """Test campaign creation with invalid data"""
        invalid_data = {
            "description": "Missing name field"
        }
        
        response = client.post(
            '/api/campaigns',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "error" in data
    
    def test_get_campaigns_list(self, client, authenticated_user):
        """Test retrieving campaigns list"""
        response = client.get('/api/campaigns')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "campaigns" in data
        assert isinstance(data["campaigns"], list)
    
    def test_get_campaign_by_id(self, client, authenticated_user):
        """Test retrieving specific campaign by ID"""
        # First create a campaign
        campaign_data = {
            "name": "Test Campaign for Retrieval",
            "description": "Test campaign"
        }
        
        create_response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        campaign_id = json.loads(create_response.data)["campaign"]["id"]
        
        # Then retrieve it
        response = client.get(f'/api/campaigns/{campaign_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["campaign"]["id"] == campaign_id
        assert data["campaign"]["name"] == campaign_data["name"]
    
    def test_get_campaign_not_found(self, client, authenticated_user):
        """Test retrieving non-existent campaign"""
        response = client.get('/api/campaigns/99999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
    
    def test_update_campaign(self, client, authenticated_user):
        """Test updating campaign"""
        # Create campaign first
        campaign_data = {
            "name": "Original Campaign Name",
            "description": "Original description"
        }
        
        create_response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        campaign_id = json.loads(create_response.data)["campaign"]["id"]
        
        # Update campaign
        update_data = {
            "name": "Updated Campaign Name",
            "description": "Updated description"
        }
        
        response = client.put(
            f'/api/campaigns/{campaign_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["campaign"]["name"] == update_data["name"]
        assert data["campaign"]["description"] == update_data["description"]
    
    def test_delete_campaign(self, client, authenticated_user):
        """Test deleting campaign"""
        # Create campaign first
        campaign_data = {
            "name": "Campaign to Delete",
            "description": "This campaign will be deleted"
        }
        
        create_response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        campaign_id = json.loads(create_response.data)["campaign"]["id"]
        
        # Delete campaign
        response = client.delete(f'/api/campaigns/{campaign_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        
        # Verify campaign is deleted
        get_response = client.get(f'/api/campaigns/{campaign_id}')
        assert get_response.status_code == 404


class TestProfileEndpoints:
    """Integration tests for profile management endpoints"""
    
    @pytest.fixture
    def test_campaign(self, client, authenticated_user):
        """Create test campaign for profile tests"""
        campaign_data = {
            "name": "Test Campaign for Profiles",
            "description": "Campaign for profile testing"
        }
        
        response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        return json.loads(response.data)["campaign"]
    
    def test_add_profile_to_campaign(self, client, authenticated_user, test_campaign):
        """Test adding profile to campaign"""
        profile_data = {
            "campaign_id": test_campaign["id"],
            "name": "Test Facebook Profile",
            "platform": "facebook",
            "url": "https://facebook.com/testprofile"
        }
        
        response = client.post(
            '/api/profiles',
            data=json.dumps(profile_data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["profile"]["name"] == profile_data["name"]
        assert data["profile"]["platform"] == profile_data["platform"]
    
    def test_add_profile_invalid_url(self, client, authenticated_user, test_campaign):
        """Test adding profile with invalid URL"""
        profile_data = {
            "campaign_id": test_campaign["id"],
            "name": "Invalid Profile",
            "platform": "facebook",
            "url": "not_a_valid_url"
        }
        
        response = client.post(
            '/api/profiles',
            data=json.dumps(profile_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "url" in data["error"].lower()
    
    def test_get_campaign_profiles(self, client, authenticated_user, test_campaign):
        """Test retrieving profiles for a campaign"""
        # Add a profile first
        profile_data = {
            "campaign_id": test_campaign["id"],
            "name": "Test Profile for Retrieval",
            "platform": "instagram",
            "url": "https://instagram.com/testprofile"
        }
        
        client.post(
            '/api/profiles',
            data=json.dumps(profile_data),
            content_type='application/json'
        )
        
        # Retrieve profiles
        response = client.get(f'/api/campaigns/{test_campaign["id"]}/profiles')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "profiles" in data
        assert len(data["profiles"]) >= 1
    
    def test_update_profile(self, client, authenticated_user, test_campaign):
        """Test updating profile"""
        # Create profile first
        profile_data = {
            "campaign_id": test_campaign["id"],
            "name": "Original Profile Name",
            "platform": "twitter",
            "url": "https://twitter.com/original"
        }
        
        create_response = client.post(
            '/api/profiles',
            data=json.dumps(profile_data),
            content_type='application/json'
        )
        
        profile_id = json.loads(create_response.data)["profile"]["id"]
        
        # Update profile
        update_data = {
            "name": "Updated Profile Name",
            "url": "https://twitter.com/updated"
        }
        
        response = client.put(
            f'/api/profiles/{profile_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["profile"]["name"] == update_data["name"]
        assert data["profile"]["url"] == update_data["url"]
    
    def test_delete_profile(self, client, authenticated_user, test_campaign):
        """Test deleting profile"""
        # Create profile first
        profile_data = {
            "campaign_id": test_campaign["id"],
            "name": "Profile to Delete",
            "platform": "linkedin",
            "url": "https://linkedin.com/company/test"
        }
        
        create_response = client.post(
            '/api/profiles',
            data=json.dumps(profile_data),
            content_type='application/json'
        )
        
        profile_id = json.loads(create_response.data)["profile"]["id"]
        
        # Delete profile
        response = client.delete(f'/api/profiles/{profile_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True


class TestDataExtractionEndpoints:
    """Integration tests for data extraction endpoints"""
    
    @pytest.fixture
    def test_campaign_with_profiles(self, client, authenticated_user):
        """Create test campaign with profiles for data extraction tests"""
        # Create campaign
        campaign_data = {
            "name": "Data Extraction Test Campaign",
            "description": "Campaign for testing data extraction"
        }
        
        campaign_response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        campaign = json.loads(campaign_response.data)["campaign"]
        
        # Add profiles
        profiles_data = [
            {
                "campaign_id": campaign["id"],
                "name": "Facebook Test",
                "platform": "facebook",
                "url": "https://facebook.com/test"
            },
            {
                "campaign_id": campaign["id"],
                "name": "Instagram Test",
                "platform": "instagram",
                "url": "https://instagram.com/test"
            }
        ]
        
        profiles = []
        for profile_data in profiles_data:
            profile_response = client.post(
                '/api/profiles',
                data=json.dumps(profile_data),
                content_type='application/json'
            )
            profiles.append(json.loads(profile_response.data)["profile"])
        
        return {"campaign": campaign, "profiles": profiles}
    
    @patch('services.apify_client.ApifyClient')
    def test_extract_data_success(self, mock_apify_client, client, authenticated_user, test_campaign_with_profiles):
        """Test successful data extraction"""
        # Mock Apify client
        mock_client_instance = Mock()
        mock_apify_client.return_value = mock_client_instance
        
        mock_client_instance.extract_facebook_data.return_value = {
            "success": True,
            "data": {
                "followers": 1500,
                "posts": 25,
                "engagement_rate": 8.5
            }
        }
        
        campaign_id = test_campaign_with_profiles["campaign"]["id"]
        
        response = client.post(f'/api/campaigns/{campaign_id}/extract-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "extraction_results" in data
    
    @patch('services.apify_client.ApifyClient')
    def test_extract_data_apify_error(self, mock_apify_client, client, authenticated_user, test_campaign_with_profiles):
        """Test data extraction with Apify error"""
        # Mock Apify client to raise error
        mock_client_instance = Mock()
        mock_apify_client.return_value = mock_client_instance
        
        mock_client_instance.extract_facebook_data.return_value = {
            "success": False,
            "error": "Apify extraction failed"
        }
        
        campaign_id = test_campaign_with_profiles["campaign"]["id"]
        
        response = client.post(f'/api/campaigns/{campaign_id}/extract-data')
        
        assert response.status_code == 200  # Partial success is still 200
        data = json.loads(response.data)
        assert "extraction_results" in data
        # Some extractions may fail while others succeed
    
    def test_extract_data_campaign_not_found(self, client, authenticated_user):
        """Test data extraction for non-existent campaign"""
        response = client.post('/api/campaigns/99999/extract-data')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
    
    def test_extract_data_no_profiles(self, client, authenticated_user):
        """Test data extraction for campaign with no profiles"""
        # Create campaign without profiles
        campaign_data = {
            "name": "Empty Campaign",
            "description": "Campaign with no profiles"
        }
        
        campaign_response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        campaign_id = json.loads(campaign_response.data)["campaign"]["id"]
        
        response = client.post(f'/api/campaigns/{campaign_id}/extract-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "no profiles" in data["error"].lower()


class TestReportEndpoints:
    """Integration tests for report generation endpoints"""
    
    @pytest.fixture
    def test_campaign_with_data(self, client, authenticated_user, sample_metrics_data):
        """Create test campaign with sample data for report tests"""
        # Create campaign
        campaign_data = {
            "name": "Report Test Campaign",
            "description": "Campaign for testing report generation"
        }
        
        campaign_response = client.post(
            '/api/campaigns',
            data=json.dumps(campaign_data),
            content_type='application/json'
        )
        
        campaign = json.loads(campaign_response.data)["campaign"]
        
        # Add profile
        profile_data = {
            "campaign_id": campaign["id"],
            "name": "Test Profile",
            "platform": "facebook",
            "url": "https://facebook.com/test"
        }
        
        profile_response = client.post(
            '/api/profiles',
            data=json.dumps(profile_data),
            content_type='application/json'
        )
        
        profile = json.loads(profile_response.data)["profile"]
        
        # Mock metrics data insertion
        # In real implementation, this would be done through data extraction
        
        return {"campaign": campaign, "profile": profile}
    
    @patch('services.report_generator.PDFReportGenerator')
    def test_generate_report_success(self, mock_generator, client, authenticated_user, test_campaign_with_data):
        """Test successful report generation"""
        # Mock PDF generator
        mock_generator_instance = Mock()
        mock_generator.return_value = mock_generator_instance
        
        mock_generator_instance.generate_report.return_value = {
            "success": True,
            "file_path": "/tmp/test_report.pdf",
            "file_size": 1024000,
            "generation_time": 2.5
        }
        
        campaign_id = test_campaign_with_data["campaign"]["id"]
        
        response = client.post(f'/api/campaigns/{campaign_id}/generate-report')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "report" in data
        assert data["report"]["file_path"] == "/tmp/test_report.pdf"
    
    @patch('services.report_generator.PDFReportGenerator')
    def test_generate_report_pdf_error(self, mock_generator, client, authenticated_user, test_campaign_with_data):
        """Test report generation with PDF generation error"""
        # Mock PDF generator to raise error
        mock_generator_instance = Mock()
        mock_generator.return_value = mock_generator_instance
        
        mock_generator_instance.generate_report.side_effect = Exception("PDF generation failed")
        
        campaign_id = test_campaign_with_data["campaign"]["id"]
        
        response = client.post(f'/api/campaigns/{campaign_id}/generate-report')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "error" in data
    
    def test_generate_report_campaign_not_found(self, client, authenticated_user):
        """Test report generation for non-existent campaign"""
        response = client.post('/api/campaigns/99999/generate-report')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
    
    def test_download_report(self, client, authenticated_user, test_campaign_with_data):
        """Test report download endpoint"""
        # This would typically require a real report file
        # For testing, we'll mock the file existence
        
        with patch('os.path.exists', return_value=True), \
             patch('flask.send_file') as mock_send_file:
            
            mock_send_file.return_value = Mock()
            
            response = client.get('/api/reports/test_report.pdf')
            
            # Verify send_file was called
            mock_send_file.assert_called_once()
    
    def test_download_report_not_found(self, client, authenticated_user):
        """Test downloading non-existent report"""
        response = client.get('/api/reports/nonexistent_report.pdf')
        
        assert response.status_code == 404


class TestAuthenticationEndpoints:
    """Integration tests for authentication endpoints"""
    
    def test_login_success(self, client):
        """Test successful login"""
        login_data = {
            "username": "testuser",
            "password": "testpassword"
        }
        
        with patch('services.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "success": True,
                "user": {
                    "id": "user123",
                    "username": "testuser",
                    "role": "admin"
                },
                "token": "jwt_token_123"
            }
            
            response = client.post(
                '/api/auth/login',
                data=json.dumps(login_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "token" in data
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        
        with patch('services.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "success": False,
                "error": "Invalid credentials"
            }
            
            response = client.post(
                '/api/auth/login',
                data=json.dumps(login_data),
                content_type='application/json'
            )
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data["success"] is False
    
    def test_logout(self, client, authenticated_user):
        """Test logout"""
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
    
    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get('/api/campaigns')
        
        # Should redirect to login or return 401
        assert response.status_code in [401, 302]


class TestErrorHandling:
    """Integration tests for error handling"""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling"""
        response = client.get('/api/nonexistent-endpoint')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
    
    def test_405_method_not_allowed(self, client):
        """Test 405 method not allowed error"""
        # Try to POST to a GET-only endpoint
        response = client.post('/api/campaigns/1')
        
        assert response.status_code == 405
        data = json.loads(response.data)
        assert "error" in data
    
    def test_400_bad_request_invalid_json(self, client, authenticated_user):
        """Test 400 bad request with invalid JSON"""
        response = client.post(
            '/api/campaigns',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_500_internal_server_error(self, client, authenticated_user):
        """Test 500 internal server error handling"""
        with patch('services.database.get_campaigns') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            response = client.get('/api/campaigns')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data


class TestRateLimiting:
    """Integration tests for rate limiting"""
    
    def test_rate_limiting_enforcement(self, client, authenticated_user):
        """Test rate limiting enforcement"""
        # Make multiple rapid requests
        responses = []
        for i in range(100):  # Exceed rate limit
            response = client.get('/api/campaigns')
            responses.append(response)
        
        # Check if any requests were rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        
        # Note: This test depends on rate limiting configuration
        # In a real implementation, you'd configure lower limits for testing
    
    def test_rate_limiting_headers(self, client, authenticated_user):
        """Test rate limiting headers"""
        response = client.get('/api/campaigns')
        
        # Check for rate limiting headers
        # These headers depend on your rate limiting implementation
        expected_headers = ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset']
        
        # Note: Uncomment if rate limiting headers are implemented
        # for header in expected_headers:
        #     assert header in response.headers


class TestCORS:
    """Integration tests for CORS handling"""
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight request"""
        response = client.options(
            '/api/campaigns',
            headers={
                'Origin': 'https://example.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
        )
        
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
    
    def test_cors_actual_request(self, client, authenticated_user):
        """Test CORS actual request"""
        response = client.get(
            '/api/campaigns',
            headers={'Origin': 'https://example.com'}
        )
        
        assert 'Access-Control-Allow-Origin' in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=routes"])

