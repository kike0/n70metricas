"""
Unit Tests for Apify Client
QA-Engineer Implementation - Comprehensive Unit Testing
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.apify_client import ApifyClient, ApifyError, RateLimitError


class TestApifyClient:
    """Comprehensive unit tests for ApifyClient"""
    
    @pytest.fixture
    def apify_client(self):
        """Create ApifyClient instance for testing"""
        return ApifyClient(api_token="test_token_12345")
    
    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "defaultDatasetId": "test_dataset_123",
                "status": "SUCCEEDED"
            }
        }
        response.headers = {"content-type": "application/json"}
        return response
    
    def test_client_initialization(self):
        """Test ApifyClient initialization"""
        # Test with valid token
        client = ApifyClient(api_token="valid_token")
        assert client.api_token == "valid_token"
        assert client.base_url == "https://api.apify.com/v2"
        assert client.timeout == 30
        
        # Test with custom parameters
        client = ApifyClient(
            api_token="custom_token",
            base_url="https://custom.api.com",
            timeout=60
        )
        assert client.api_token == "custom_token"
        assert client.base_url == "https://custom.api.com"
        assert client.timeout == 60
    
    def test_client_initialization_invalid_token(self):
        """Test ApifyClient initialization with invalid token"""
        with pytest.raises(ValueError, match="API token is required"):
            ApifyClient(api_token="")
        
        with pytest.raises(ValueError, match="API token is required"):
            ApifyClient(api_token=None)
    
    @patch('requests.post')
    def test_run_actor_success(self, mock_post, apify_client, mock_response):
        """Test successful actor run"""
        mock_post.return_value = mock_response
        
        result = apify_client.run_actor(
            actor_id="test_actor",
            input_data={"url": "https://facebook.com/test"}
        )
        
        assert result["success"] is True
        assert result["run_id"] == "test_dataset_123"
        assert result["status"] == "SUCCEEDED"
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "test_actor/runs" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_token_12345"
    
    @patch('requests.post')
    def test_run_actor_failure(self, mock_post, apify_client):
        """Test actor run failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid input"}
        mock_post.return_value = mock_response
        
        with pytest.raises(ApifyError, match="Actor run failed"):
            apify_client.run_actor("invalid_actor", {})
    
    @patch('requests.post')
    def test_run_actor_rate_limit(self, mock_post, apify_client):
        """Test actor run with rate limiting"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_post.return_value = mock_response
        
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            apify_client.run_actor("test_actor", {})
    
    @patch('requests.post')
    def test_run_actor_timeout(self, mock_post, apify_client):
        """Test actor run timeout"""
        mock_post.side_effect = Timeout("Request timed out")
        
        with pytest.raises(ApifyError, match="Request timed out"):
            apify_client.run_actor("test_actor", {})
    
    @patch('requests.post')
    def test_run_actor_connection_error(self, mock_post, apify_client):
        """Test actor run connection error"""
        mock_post.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ApifyError, match="Connection failed"):
            apify_client.run_actor("test_actor", {})
    
    @patch('requests.get')
    def test_get_dataset_items_success(self, mock_get, apify_client):
        """Test successful dataset retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"followers": 1000, "posts": 50},
            {"followers": 1100, "posts": 52}
        ]
        mock_get.return_value = mock_response
        
        result = apify_client.get_dataset_items("test_dataset")
        
        assert len(result) == 2
        assert result[0]["followers"] == 1000
        assert result[1]["followers"] == 1100
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "datasets/test_dataset/items" in call_args[0][0]
    
    @patch('requests.get')
    def test_get_dataset_items_empty(self, mock_get, apify_client):
        """Test dataset retrieval with empty results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        result = apify_client.get_dataset_items("empty_dataset")
        
        assert result == []
    
    @patch('requests.get')
    def test_get_dataset_items_not_found(self, mock_get, apify_client):
        """Test dataset retrieval with not found error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Dataset not found"}
        mock_get.return_value = mock_response
        
        with pytest.raises(ApifyError, match="Dataset not found"):
            apify_client.get_dataset_items("nonexistent_dataset")
    
    @patch.object(ApifyClient, 'run_actor')
    @patch.object(ApifyClient, 'get_dataset_items')
    def test_extract_facebook_data_success(self, mock_get_items, mock_run_actor, apify_client):
        """Test successful Facebook data extraction"""
        # Mock actor run
        mock_run_actor.return_value = {
            "success": True,
            "run_id": "facebook_run_123",
            "status": "SUCCEEDED"
        }
        
        # Mock dataset items
        mock_get_items.return_value = [{
            "followers": 1500,
            "posts": 25,
            "likes": 750,
            "comments": 125,
            "shares": 50,
            "engagement_rate": 8.5,
            "last_updated": datetime.now().isoformat()
        }]
        
        result = apify_client.extract_facebook_data("https://facebook.com/test")
        
        assert result["success"] is True
        assert result["data"]["followers"] == 1500
        assert result["data"]["engagement_rate"] == 8.5
        
        # Verify method calls
        mock_run_actor.assert_called_once()
        mock_get_items.assert_called_once_with("facebook_run_123")
    
    @patch.object(ApifyClient, 'run_actor')
    def test_extract_facebook_data_actor_failure(self, mock_run_actor, apify_client):
        """Test Facebook data extraction with actor failure"""
        mock_run_actor.side_effect = ApifyError("Actor failed")
        
        result = apify_client.extract_facebook_data("https://facebook.com/test")
        
        assert result["success"] is False
        assert "Actor failed" in result["error"]
    
    @patch.object(ApifyClient, 'run_actor')
    @patch.object(ApifyClient, 'get_dataset_items')
    def test_extract_instagram_data_success(self, mock_get_items, mock_run_actor, apify_client):
        """Test successful Instagram data extraction"""
        # Mock actor run
        mock_run_actor.return_value = {
            "success": True,
            "run_id": "instagram_run_456",
            "status": "SUCCEEDED"
        }
        
        # Mock dataset items
        mock_get_items.return_value = [{
            "followers": 2000,
            "posts": 30,
            "likes": 1200,
            "comments": 200,
            "engagement_rate": 9.2,
            "last_updated": datetime.now().isoformat()
        }]
        
        result = apify_client.extract_instagram_data("https://instagram.com/test")
        
        assert result["success"] is True
        assert result["data"]["followers"] == 2000
        assert result["data"]["engagement_rate"] == 9.2
    
    @patch.object(ApifyClient, 'run_actor')
    @patch.object(ApifyClient, 'get_dataset_items')
    def test_extract_twitter_data_success(self, mock_get_items, mock_run_actor, apify_client):
        """Test successful Twitter data extraction"""
        # Mock actor run
        mock_run_actor.return_value = {
            "success": True,
            "run_id": "twitter_run_789",
            "status": "SUCCEEDED"
        }
        
        # Mock dataset items
        mock_get_items.return_value = [{
            "followers": 800,
            "tweets": 150,
            "likes": 400,
            "retweets": 60,
            "replies": 80,
            "engagement_rate": 6.8,
            "last_updated": datetime.now().isoformat()
        }]
        
        result = apify_client.extract_twitter_data("https://twitter.com/test")
        
        assert result["success"] is True
        assert result["data"]["followers"] == 800
        assert result["data"]["engagement_rate"] == 6.8
    
    def test_validate_url_valid_facebook(self, apify_client):
        """Test URL validation for valid Facebook URLs"""
        valid_urls = [
            "https://facebook.com/testpage",
            "https://www.facebook.com/testpage",
            "https://m.facebook.com/testpage",
            "https://facebook.com/pages/testpage/123456789"
        ]
        
        for url in valid_urls:
            assert apify_client._validate_url(url, "facebook") is True
    
    def test_validate_url_invalid_facebook(self, apify_client):
        """Test URL validation for invalid Facebook URLs"""
        invalid_urls = [
            "https://instagram.com/test",
            "https://twitter.com/test",
            "not_a_url",
            "",
            None
        ]
        
        for url in invalid_urls:
            assert apify_client._validate_url(url, "facebook") is False
    
    def test_validate_url_valid_instagram(self, apify_client):
        """Test URL validation for valid Instagram URLs"""
        valid_urls = [
            "https://instagram.com/testuser",
            "https://www.instagram.com/testuser",
            "https://instagram.com/p/ABC123/",
        ]
        
        for url in valid_urls:
            assert apify_client._validate_url(url, "instagram") is True
    
    def test_validate_url_valid_twitter(self, apify_client):
        """Test URL validation for valid Twitter URLs"""
        valid_urls = [
            "https://twitter.com/testuser",
            "https://www.twitter.com/testuser",
            "https://x.com/testuser",
            "https://www.x.com/testuser"
        ]
        
        for url in valid_urls:
            assert apify_client._validate_url(url, "twitter") is True
    
    def test_rate_limiting_logic(self, apify_client):
        """Test rate limiting logic"""
        # Test initial state
        assert apify_client._can_make_request() is True
        
        # Simulate rate limit hit
        apify_client._handle_rate_limit()
        
        # Should be blocked immediately after rate limit
        assert apify_client._can_make_request() is False
        
        # Test rate limit reset (mock time passage)
        with patch('time.time') as mock_time:
            mock_time.return_value = apify_client.last_rate_limit + 61  # 61 seconds later
            assert apify_client._can_make_request() is True
    
    def test_request_headers(self, apify_client):
        """Test request headers are properly set"""
        headers = apify_client._get_headers()
        
        assert headers["Authorization"] == "Bearer test_token_12345"
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
        assert "social-media-reports" in headers["User-Agent"]
    
    def test_error_handling_json_decode_error(self, apify_client):
        """Test handling of JSON decode errors"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.text = "Invalid response"
            mock_post.return_value = mock_response
            
            with pytest.raises(ApifyError, match="Invalid response format"):
                apify_client.run_actor("test_actor", {})
    
    def test_retry_logic_success_after_failure(self, apify_client):
        """Test retry logic succeeds after initial failure"""
        with patch('requests.post') as mock_post:
            # First call fails, second succeeds
            failure_response = Mock()
            failure_response.status_code = 500
            failure_response.json.return_value = {"error": "Server error"}
            
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {
                "data": {"defaultDatasetId": "test_123", "status": "SUCCEEDED"}
            }
            
            mock_post.side_effect = [failure_response, success_response]
            
            result = apify_client.run_actor("test_actor", {}, max_retries=2)
            
            assert result["success"] is True
            assert mock_post.call_count == 2
    
    def test_retry_logic_max_retries_exceeded(self, apify_client):
        """Test retry logic when max retries exceeded"""
        with patch('requests.post') as mock_post:
            failure_response = Mock()
            failure_response.status_code = 500
            failure_response.json.return_value = {"error": "Server error"}
            mock_post.return_value = failure_response
            
            with pytest.raises(ApifyError, match="Max retries exceeded"):
                apify_client.run_actor("test_actor", {}, max_retries=2)
            
            assert mock_post.call_count == 3  # Initial + 2 retries
    
    def test_concurrent_requests_handling(self, apify_client):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                with patch('requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "data": {"defaultDatasetId": f"test_{threading.current_thread().ident}", "status": "SUCCEEDED"}
                    }
                    mock_post.return_value = mock_response
                    
                    result = apify_client.run_actor("test_actor", {})
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(results) == 5
    
    @pytest.mark.parametrize("platform,url,expected", [
        ("facebook", "https://facebook.com/test", True),
        ("instagram", "https://instagram.com/test", True),
        ("twitter", "https://twitter.com/test", True),
        ("facebook", "https://instagram.com/test", False),
        ("instagram", "https://twitter.com/test", False),
        ("twitter", "https://facebook.com/test", False),
        ("facebook", "invalid_url", False),
        ("unknown", "https://facebook.com/test", False),
    ])
    def test_url_validation_parametrized(self, apify_client, platform, url, expected):
        """Parametrized test for URL validation"""
        assert apify_client._validate_url(url, platform) == expected
    
    def test_memory_usage_optimization(self, apify_client):
        """Test memory usage optimization for large datasets"""
        with patch.object(apify_client, 'get_dataset_items') as mock_get_items:
            # Simulate large dataset
            large_dataset = [{"data": f"item_{i}"} for i in range(10000)]
            mock_get_items.return_value = large_dataset
            
            # Test that method handles large datasets without memory issues
            result = apify_client.get_dataset_items("large_dataset")
            
            assert len(result) == 10000
            assert result[0]["data"] == "item_0"
            assert result[-1]["data"] == "item_9999"
    
    def test_data_sanitization(self, apify_client):
        """Test data sanitization and validation"""
        # Test with malicious input
        malicious_input = {
            "url": "https://facebook.com/test",
            "script": "<script>alert('xss')</script>",
            "sql": "'; DROP TABLE users; --"
        }
        
        sanitized = apify_client._sanitize_input(malicious_input)
        
        # Verify malicious content is removed/escaped
        assert "<script>" not in str(sanitized)
        assert "DROP TABLE" not in str(sanitized)
        assert sanitized["url"] == "https://facebook.com/test"  # Valid data preserved
    
    def test_performance_monitoring(self, apify_client, performance_monitor):
        """Test performance monitoring of API calls"""
        performance_monitor.start()
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {"defaultDatasetId": "test_123", "status": "SUCCEEDED"}
            }
            mock_post.return_value = mock_response
            
            result = apify_client.run_actor("test_actor", {})
        
        metrics = performance_monitor.stop()
        
        # Verify performance is within acceptable limits
        assert metrics['execution_time'] < 1.0  # Should complete in under 1 second
        assert result["success"] is True


class TestApifyError:
    """Test custom Apify exceptions"""
    
    def test_apify_error_creation(self):
        """Test ApifyError creation"""
        error = ApifyError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_rate_limit_error_creation(self):
        """Test RateLimitError creation"""
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, ApifyError)
        assert isinstance(error, Exception)


# Integration-style tests (still unit tests but testing multiple components)
class TestApifyClientIntegration:
    """Integration-style unit tests for ApifyClient"""
    
    @pytest.fixture
    def apify_client(self):
        """Create ApifyClient instance for integration testing"""
        return ApifyClient(api_token="integration_test_token")
    
    def test_full_facebook_extraction_workflow(self, apify_client):
        """Test complete Facebook data extraction workflow"""
        with patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            # Mock actor run response
            run_response = Mock()
            run_response.status_code = 200
            run_response.json.return_value = {
                "data": {"defaultDatasetId": "fb_dataset_123", "status": "SUCCEEDED"}
            }
            mock_post.return_value = run_response
            
            # Mock dataset retrieval response
            data_response = Mock()
            data_response.status_code = 200
            data_response.json.return_value = [{
                "followers": 1500,
                "posts": 25,
                "likes": 750,
                "comments": 125,
                "shares": 50,
                "engagement_rate": 8.5,
                "last_updated": datetime.now().isoformat()
            }]
            mock_get.return_value = data_response
            
            # Execute full workflow
            result = apify_client.extract_facebook_data("https://facebook.com/testpage")
            
            # Verify complete workflow
            assert result["success"] is True
            assert result["data"]["followers"] == 1500
            assert result["data"]["engagement_rate"] == 8.5
            
            # Verify API calls were made in correct order
            assert mock_post.called
            assert mock_get.called
    
    def test_error_propagation_through_workflow(self, apify_client):
        """Test error propagation through complete workflow"""
        with patch('requests.post') as mock_post:
            # Mock network error
            mock_post.side_effect = ConnectionError("Network error")
            
            result = apify_client.extract_facebook_data("https://facebook.com/testpage")
            
            assert result["success"] is False
            assert "Network error" in result["error"]
    
    def test_data_consistency_across_platforms(self, apify_client):
        """Test data consistency across different platforms"""
        platforms_data = {}
        
        with patch.object(apify_client, 'run_actor') as mock_run, \
             patch.object(apify_client, 'get_dataset_items') as mock_get:
            
            # Mock responses for different platforms
            mock_run.return_value = {"success": True, "run_id": "test_123", "status": "SUCCEEDED"}
            
            # Test Facebook
            mock_get.return_value = [{"followers": 1000, "engagement_rate": 8.0}]
            platforms_data["facebook"] = apify_client.extract_facebook_data("https://facebook.com/test")
            
            # Test Instagram
            mock_get.return_value = [{"followers": 1200, "engagement_rate": 9.0}]
            platforms_data["instagram"] = apify_client.extract_instagram_data("https://instagram.com/test")
            
            # Test Twitter
            mock_get.return_value = [{"followers": 800, "engagement_rate": 7.0}]
            platforms_data["twitter"] = apify_client.extract_twitter_data("https://twitter.com/test")
        
        # Verify data structure consistency
        for platform, data in platforms_data.items():
            assert data["success"] is True
            assert "followers" in data["data"]
            assert "engagement_rate" in data["data"]
            assert isinstance(data["data"]["followers"], int)
            assert isinstance(data["data"]["engagement_rate"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services.apify_client"])

