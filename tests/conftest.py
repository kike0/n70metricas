"""
Pytest Configuration and Fixtures
QA-Engineer Implementation - Global Test Configuration
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import sqlite3
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Test database configuration
TEST_DB_CONFIG = {
    'database_url': 'sqlite:///:memory:',
    'echo': False,
    'pool_pre_ping': True
}

# Mock Apify configuration
MOCK_APIFY_CONFIG = {
    'api_token': 'test_token_12345',
    'base_url': 'https://api.apify.com/v2',
    'timeout': 30
}

@pytest.fixture(scope="session")
def test_config():
    """Global test configuration"""
    return {
        'testing': True,
        'debug': False,
        'database_url': TEST_DB_CONFIG['database_url'],
        'apify_api_token': MOCK_APIFY_CONFIG['api_token'],
        'secret_key': 'test-secret-key-for-testing-only',
        'jwt_secret_key': 'test-jwt-secret-key',
        'bcrypt_log_rounds': 4,  # Faster for testing
        'testing_mode': True
    }

@pytest.fixture(scope="session")
def app(test_config):
    """Create application instance for testing"""
    from main import create_app
    
    app = create_app(test_config)
    app.config.update(test_config)
    
    # Create application context
    ctx = app.app_context()
    ctx.push()
    
    yield app
    
    ctx.pop()

@pytest.fixture(scope="function")
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope="function")
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture(scope="function")
def temp_dir():
    """Create temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def test_database():
    """Create in-memory test database"""
    conn = sqlite3.connect(':memory:')
    
    # Create test tables
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE profiles (
            id INTEGER PRIMARY KEY,
            campaign_id INTEGER,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER,
            metric_date DATE,
            followers INTEGER DEFAULT 0,
            following INTEGER DEFAULT 0,
            posts INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles (id)
        )
    ''')
    
    # Insert test data
    cursor.execute('''
        INSERT INTO campaigns (name, description) 
        VALUES ('Test Campaign', 'Campaign for testing purposes')
    ''')
    
    cursor.execute('''
        INSERT INTO profiles (campaign_id, name, platform, url) 
        VALUES (1, 'Test Profile', 'facebook', 'https://facebook.com/test')
    ''')
    
    cursor.execute('''
        INSERT INTO metrics (profile_id, metric_date, followers, likes, comments) 
        VALUES (1, '2025-08-01', 1000, 50, 10)
    ''')
    
    conn.commit()
    
    yield conn
    
    conn.close()

@pytest.fixture(scope="function")
def mock_apify_client():
    """Mock Apify client for testing"""
    with patch('services.apify_client.ApifyClient') as mock_client:
        # Configure mock responses
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Mock successful data extraction
        mock_instance.extract_facebook_data.return_value = {
            'success': True,
            'data': {
                'followers': 1500,
                'posts': 25,
                'engagement_rate': 8.5,
                'last_updated': datetime.now().isoformat()
            }
        }
        
        mock_instance.extract_instagram_data.return_value = {
            'success': True,
            'data': {
                'followers': 2000,
                'posts': 30,
                'engagement_rate': 9.2,
                'last_updated': datetime.now().isoformat()
            }
        }
        
        mock_instance.extract_twitter_data.return_value = {
            'success': True,
            'data': {
                'followers': 800,
                'tweets': 150,
                'engagement_rate': 6.8,
                'last_updated': datetime.now().isoformat()
            }
        }
        
        yield mock_instance

@pytest.fixture(scope="function")
def sample_campaign_data():
    """Sample campaign data for testing"""
    return {
        'name': 'Test Campaign 2025',
        'description': 'Comprehensive test campaign for social media analytics',
        'profiles': [
            {
                'name': 'Facebook Test',
                'platform': 'facebook',
                'url': 'https://facebook.com/test-page'
            },
            {
                'name': 'Instagram Test',
                'platform': 'instagram', 
                'url': 'https://instagram.com/test-account'
            },
            {
                'name': 'Twitter Test',
                'platform': 'twitter',
                'url': 'https://twitter.com/test-handle'
            }
        ]
    }

@pytest.fixture(scope="function")
def sample_metrics_data():
    """Sample metrics data for testing"""
    return {
        'facebook': {
            'followers': 1500,
            'posts': 25,
            'likes': 750,
            'comments': 125,
            'shares': 50,
            'engagement_rate': 8.5
        },
        'instagram': {
            'followers': 2000,
            'posts': 30,
            'likes': 1200,
            'comments': 200,
            'shares': 80,
            'engagement_rate': 9.2
        },
        'twitter': {
            'followers': 800,
            'tweets': 150,
            'likes': 400,
            'retweets': 60,
            'replies': 80,
            'engagement_rate': 6.8
        }
    }

@pytest.fixture(scope="function")
def authenticated_user(client):
    """Create authenticated user session"""
    # Mock user authentication
    with client.session_transaction() as sess:
        sess['user_id'] = 'test_user_123'
        sess['user_role'] = 'admin'
        sess['authenticated'] = True
    
    return {
        'user_id': 'test_user_123',
        'role': 'admin',
        'permissions': ['read', 'write', 'admin']
    }

@pytest.fixture(scope="function")
def mock_pdf_generator():
    """Mock PDF generator for testing"""
    with patch('services.report_generator.PDFGenerator') as mock_gen:
        mock_instance = Mock()
        mock_gen.return_value = mock_instance
        
        # Mock successful PDF generation
        mock_instance.generate_report.return_value = {
            'success': True,
            'file_path': '/tmp/test_report.pdf',
            'file_size': 1024000,  # 1MB
            'pages': 5
        }
        
        yield mock_instance

@pytest.fixture(scope="function")
def performance_monitor():
    """Performance monitoring fixture"""
    import time
    import psutil
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.start_cpu = None
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.virtual_memory().used
            self.start_cpu = psutil.cpu_percent()
        
        def stop(self):
            end_time = time.time()
            end_memory = psutil.virtual_memory().used
            end_cpu = psutil.cpu_percent()
            
            return {
                'execution_time': end_time - self.start_time,
                'memory_delta': end_memory - self.start_memory,
                'cpu_usage': max(self.start_cpu, end_cpu)
            }
    
    return PerformanceMonitor()

@pytest.fixture(scope="function")
def security_context():
    """Security testing context"""
    return {
        'test_passwords': [
            'weak',
            'password123',
            'StrongP@ssw0rd!',
            'VeryStrongP@ssw0rd123!'
        ],
        'test_tokens': [
            'invalid_token',
            'expired_token',
            'malformed_token'
        ],
        'sql_injection_payloads': [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --"
        ],
        'xss_payloads': [
            '<script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            '<img src="x" onerror="alert(\'XSS\')">'
        ]
    }

# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "functional: mark test as functional test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "ui: mark test as UI test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers based on file location
    for item in items:
        # Add unit marker for tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker for tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker for tests in performance/ directory
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        
        # Add security marker for tests in security/ directory
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        
        # Add ui marker for tests in ui/ directory
        elif "ui" in str(item.fspath):
            item.add_marker(pytest.mark.ui)

# Test data cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Automatically cleanup test data after each test"""
    yield
    
    # Cleanup temporary files
    temp_files = [
        '/tmp/test_report.pdf',
        '/tmp/test_data.json',
        '/tmp/test_config.yaml'
    ]
    
    for file_path in temp_files:
        if os.path.exists(file_path):
            os.remove(file_path)

# Performance tracking
@pytest.fixture(autouse=True)
def track_test_performance(request):
    """Track performance of each test"""
    start_time = datetime.now()
    
    yield
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Log slow tests
    if duration > 5.0:  # 5 seconds threshold
        print(f"\n⚠️  Slow test detected: {request.node.name} took {duration:.2f}s")

# Error handling
@pytest.fixture(autouse=True)
def handle_test_errors(request):
    """Handle test errors and provide debugging info"""
    yield
    
    if request.node.rep_call.failed:
        print(f"\n❌ Test failed: {request.node.name}")
        print(f"Error: {request.node.rep_call.longrepr}")

def pytest_runtest_makereport(item, call):
    """Make test report available to fixtures"""
    if "rep_" + call.when not in item.__dict__:
        item.__dict__["rep_" + call.when] = call

