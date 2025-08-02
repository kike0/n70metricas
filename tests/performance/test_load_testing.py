"""
Performance and Load Testing
QA-Engineer Implementation - Comprehensive Performance Testing with Locust
"""

import pytest
import time
import psutil
import requests
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import json
import threading
from datetime import datetime, timedelta
import statistics
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class SocialMediaReportsUser(HttpUser):
    """Locust user class for load testing social media reports system"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts"""
        self.login()
    
    def login(self):
        """Simulate user login"""
        login_data = {
            "username": "testuser",
            "password": "testpassword"
        }
        
        with self.client.post("/api/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Store auth token if needed
                try:
                    data = response.json()
                    if "token" in data:
                        self.token = data["token"]
                        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                except:
                    pass
            else:
                response.failure(f"Login failed with status {response.status_code}")
    
    @task(3)
    def view_dashboard(self):
        """Simulate viewing dashboard - most common action"""
        with self.client.get("/api/dashboard", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard load failed: {response.status_code}")
    
    @task(2)
    def list_campaigns(self):
        """Simulate listing campaigns"""
        with self.client.get("/api/campaigns", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Parse campaigns for use in other tasks
                try:
                    data = response.json()
                    if "campaigns" in data and data["campaigns"]:
                        self.campaigns = data["campaigns"]
                except:
                    pass
            else:
                response.failure(f"Campaigns list failed: {response.status_code}")
    
    @task(1)
    def view_campaign_details(self):
        """Simulate viewing campaign details"""
        if hasattr(self, 'campaigns') and self.campaigns:
            campaign_id = self.campaigns[0]["id"]
            with self.client.get(f"/api/campaigns/{campaign_id}", catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Campaign details failed: {response.status_code}")
    
    @task(1)
    def create_campaign(self):
        """Simulate creating a new campaign"""
        campaign_data = {
            "name": f"Load Test Campaign {int(time.time())}",
            "description": "Campaign created during load testing"
        }
        
        with self.client.post("/api/campaigns", json=campaign_data, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Campaign creation failed: {response.status_code}")
    
    @task(1)
    def extract_data(self):
        """Simulate data extraction - resource intensive operation"""
        if hasattr(self, 'campaigns') and self.campaigns:
            campaign_id = self.campaigns[0]["id"]
            with self.client.post(f"/api/campaigns/{campaign_id}/extract-data", catch_response=True) as response:
                if response.status_code in [200, 202]:  # Accept both success and accepted
                    response.success()
                else:
                    response.failure(f"Data extraction failed: {response.status_code}")
    
    @task(1)
    def generate_report(self):
        """Simulate report generation - most resource intensive operation"""
        if hasattr(self, 'campaigns') and self.campaigns:
            campaign_id = self.campaigns[0]["id"]
            with self.client.post(f"/api/campaigns/{campaign_id}/generate-report", catch_response=True) as response:
                if response.status_code in [200, 202]:
                    response.success()
                else:
                    response.failure(f"Report generation failed: {response.status_code}")


class APIEndpointUser(HttpUser):
    """Focused user class for API endpoint testing"""
    
    wait_time = between(0.5, 1.5)  # Faster requests for API testing
    
    @task
    def test_api_endpoints(self):
        """Test various API endpoints"""
        endpoints = [
            "/api/health",
            "/api/status", 
            "/api/campaigns",
            "/api/profiles",
            "/api/metrics"
        ]
        
        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code in [200, 401]:  # 401 is acceptable for protected endpoints
                    response.success()
                else:
                    response.failure(f"{endpoint} failed: {response.status_code}")


class TestPerformanceMetrics:
    """Performance testing with custom metrics collection"""
    
    def __init__(self):
        self.metrics = {
            "response_times": [],
            "cpu_usage": [],
            "memory_usage": [],
            "error_rates": [],
            "throughput": []
        }
        self.start_time = None
        self.monitoring = False
    
    def start_monitoring(self):
        """Start system monitoring"""
        self.monitoring = True
        self.start_time = time.time()
        
        def monitor_system():
            while self.monitoring:
                # Collect CPU and memory usage
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                self.metrics["cpu_usage"].append({
                    "timestamp": time.time(),
                    "value": cpu_percent
                })
                
                self.metrics["memory_usage"].append({
                    "timestamp": time.time(),
                    "value": memory_percent
                })
                
                time.sleep(1)
        
        monitor_thread = threading.Thread(target=monitor_system)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
    
    def collect_response_time(self, response_time):
        """Collect response time metric"""
        self.metrics["response_times"].append({
            "timestamp": time.time(),
            "value": response_time
        })
    
    def generate_report(self):
        """Generate performance report"""
        if not self.metrics["response_times"]:
            return {"error": "No metrics collected"}
        
        response_times = [m["value"] for m in self.metrics["response_times"]]
        cpu_usage = [m["value"] for m in self.metrics["cpu_usage"]]
        memory_usage = [m["value"] for m in self.metrics["memory_usage"]]
        
        report = {
            "test_duration": time.time() - self.start_time if self.start_time else 0,
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "avg": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": self._percentile(response_times, 95),
                "p99": self._percentile(response_times, 99)
            },
            "system_resources": {
                "cpu": {
                    "avg": statistics.mean(cpu_usage) if cpu_usage else 0,
                    "max": max(cpu_usage) if cpu_usage else 0
                },
                "memory": {
                    "avg": statistics.mean(memory_usage) if memory_usage else 0,
                    "max": max(memory_usage) if memory_usage else 0
                }
            },
            "total_requests": len(response_times)
        }
        
        return report
    
    def _percentile(self, data, percentile):
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestLoadTesting:
    """Load testing test cases"""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for testing"""
        return "http://localhost:5000"  # Flask development server
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring fixture"""
        monitor = TestPerformanceMetrics()
        monitor.start_monitoring()
        yield monitor
        monitor.stop_monitoring()
    
    def test_single_user_performance(self, base_url, performance_monitor):
        """Test performance with single user"""
        session = requests.Session()
        
        # Test various endpoints
        endpoints = [
            "/api/health",
            "/api/campaigns",
            "/api/dashboard"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            try:
                response = session.get(f"{base_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                performance_monitor.collect_response_time(response_time)
                
                # Assert response time is acceptable
                assert response_time < 2000, f"Response time too slow: {response_time}ms for {endpoint}"
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"Request failed for {endpoint}: {e}")
        
        # Generate and validate performance report
        report = performance_monitor.generate_report()
        
        assert report["response_times"]["avg"] < 1000, "Average response time too high"
        assert report["response_times"]["p95"] < 2000, "95th percentile response time too high"
        assert report["system_resources"]["cpu"]["avg"] < 80, "CPU usage too high"
        assert report["system_resources"]["memory"]["avg"] < 80, "Memory usage too high"
    
    def test_concurrent_users_simulation(self, base_url):
        """Test with multiple concurrent users simulation"""
        import concurrent.futures
        import threading
        
        results = []
        errors = []
        
        def simulate_user(user_id):
            """Simulate single user behavior"""
            session = requests.Session()
            user_results = []
            
            try:
                # Simulate user workflow
                workflows = [
                    ("GET", "/api/health"),
                    ("GET", "/api/campaigns"),
                    ("GET", "/api/dashboard")
                ]
                
                for method, endpoint in workflows:
                    start_time = time.time()
                    response = session.request(method, f"{base_url}{endpoint}", timeout=10)
                    response_time = (time.time() - start_time) * 1000
                    
                    user_results.append({
                        "user_id": user_id,
                        "endpoint": endpoint,
                        "response_time": response_time,
                        "status_code": response.status_code
                    })
                    
                    # Small delay between requests
                    time.sleep(0.1)
                
                results.extend(user_results)
                
            except Exception as e:
                errors.append(f"User {user_id}: {e}")
        
        # Run concurrent users
        num_users = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(simulate_user, i) for i in range(num_users)]
            concurrent.futures.wait(futures)
        
        # Analyze results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) > 0, "No results collected"
        
        # Calculate metrics
        response_times = [r["response_time"] for r in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Validate performance under load
        assert avg_response_time < 3000, f"Average response time under load too high: {avg_response_time}ms"
        assert max_response_time < 10000, f"Max response time under load too high: {max_response_time}ms"
        
        # Check success rate
        successful_requests = len([r for r in results if r["status_code"] < 400])
        success_rate = successful_requests / len(results) * 100
        assert success_rate >= 95, f"Success rate too low: {success_rate}%"
    
    def test_stress_testing(self, base_url):
        """Stress test to find breaking point"""
        import concurrent.futures
        
        max_users = 50
        step_size = 10
        step_duration = 30  # seconds
        
        results = {}
        
        for num_users in range(step_size, max_users + 1, step_size):
            print(f"Testing with {num_users} concurrent users...")
            
            user_results = []
            errors = []
            start_time = time.time()
            
            def stress_user(user_id):
                session = requests.Session()
                user_errors = []
                user_times = []
                
                end_time = time.time() + step_duration
                
                while time.time() < end_time:
                    try:
                        response_start = time.time()
                        response = session.get(f"{base_url}/api/health", timeout=5)
                        response_time = (time.time() - response_start) * 1000
                        
                        user_times.append(response_time)
                        
                        if response.status_code >= 400:
                            user_errors.append(f"HTTP {response.status_code}")
                        
                    except Exception as e:
                        user_errors.append(str(e))
                    
                    time.sleep(0.1)  # Small delay
                
                return {"times": user_times, "errors": user_errors}
            
            # Run stress test
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
                futures = [executor.submit(stress_user, i) for i in range(num_users)]
                user_results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            # Analyze results
            all_times = []
            all_errors = []
            
            for result in user_results:
                all_times.extend(result["times"])
                all_errors.extend(result["errors"])
            
            if all_times:
                avg_response_time = statistics.mean(all_times)
                error_rate = len(all_errors) / len(all_times) * 100 if all_times else 100
                
                results[num_users] = {
                    "avg_response_time": avg_response_time,
                    "error_rate": error_rate,
                    "total_requests": len(all_times),
                    "total_errors": len(all_errors)
                }
                
                print(f"  Avg response time: {avg_response_time:.2f}ms")
                print(f"  Error rate: {error_rate:.2f}%")
                
                # Stop if error rate is too high
                if error_rate > 10:
                    print(f"Breaking point reached at {num_users} users")
                    break
            else:
                print(f"  No successful requests at {num_users} users")
                break
        
        # Validate stress test results
        assert len(results) > 0, "No stress test results collected"
        
        # Find optimal user count (where error rate is still acceptable)
        optimal_users = 0
        for users, metrics in results.items():
            if metrics["error_rate"] <= 5:  # 5% error rate threshold
                optimal_users = users
        
        assert optimal_users >= 10, f"System can't handle minimum load: {optimal_users} users"
        print(f"System can handle up to {optimal_users} concurrent users with <5% error rate")
    
    def test_memory_leak_detection(self, base_url):
        """Test for memory leaks during extended operation"""
        import gc
        
        initial_memory = psutil.virtual_memory().used
        session = requests.Session()
        
        # Run requests for extended period
        num_requests = 100
        memory_samples = []
        
        for i in range(num_requests):
            try:
                response = session.get(f"{base_url}/api/health", timeout=5)
                
                # Sample memory every 10 requests
                if i % 10 == 0:
                    gc.collect()  # Force garbage collection
                    current_memory = psutil.virtual_memory().used
                    memory_samples.append(current_memory)
                
            except Exception as e:
                pytest.fail(f"Request {i} failed: {e}")
        
        # Analyze memory usage trend
        if len(memory_samples) >= 3:
            # Check if memory is consistently increasing
            memory_increases = 0
            for i in range(1, len(memory_samples)):
                if memory_samples[i] > memory_samples[i-1]:
                    memory_increases += 1
            
            # If memory increases in more than 70% of samples, potential leak
            increase_rate = memory_increases / (len(memory_samples) - 1)
            
            # Allow some memory increase but not excessive
            assert increase_rate < 0.7, f"Potential memory leak detected: {increase_rate:.2%} increase rate"
            
            # Check total memory increase
            total_increase = memory_samples[-1] - memory_samples[0]
            increase_mb = total_increase / (1024 * 1024)
            
            assert increase_mb < 100, f"Excessive memory increase: {increase_mb:.2f}MB"
    
    def test_database_performance(self, base_url):
        """Test database performance under load"""
        session = requests.Session()
        
        # Test database-heavy operations
        db_operations = [
            ("GET", "/api/campaigns"),  # Read operation
            ("POST", "/api/campaigns", {"name": "DB Test Campaign", "description": "Test"}),  # Write operation
            ("GET", "/api/metrics"),  # Complex query operation
        ]
        
        db_times = []
        
        for method, endpoint, *data in db_operations:
            # Run each operation multiple times
            for _ in range(10):
                start_time = time.time()
                
                try:
                    if data:
                        response = session.request(method, f"{base_url}{endpoint}", json=data[0], timeout=10)
                    else:
                        response = session.request(method, f"{base_url}{endpoint}", timeout=10)
                    
                    response_time = (time.time() - start_time) * 1000
                    db_times.append({
                        "operation": f"{method} {endpoint}",
                        "response_time": response_time,
                        "status_code": response.status_code
                    })
                    
                except Exception as e:
                    pytest.fail(f"Database operation failed: {e}")
        
        # Analyze database performance
        if db_times:
            avg_db_time = statistics.mean([t["response_time"] for t in db_times])
            max_db_time = max([t["response_time"] for t in db_times])
            
            # Database operations should be reasonably fast
            assert avg_db_time < 5000, f"Average database operation too slow: {avg_db_time}ms"
            assert max_db_time < 15000, f"Slowest database operation too slow: {max_db_time}ms"
            
            # Check for failed operations
            failed_ops = [t for t in db_times if t["status_code"] >= 400]
            failure_rate = len(failed_ops) / len(db_times) * 100
            
            assert failure_rate < 5, f"Database operation failure rate too high: {failure_rate}%"


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    def test_api_response_time_benchmarks(self, base_url="http://localhost:5000"):
        """Test API response time benchmarks"""
        session = requests.Session()
        
        # Define performance benchmarks for different endpoint types
        benchmarks = {
            "/api/health": 100,      # Health check should be very fast
            "/api/campaigns": 500,   # Simple CRUD operations
            "/api/dashboard": 1000,  # Dashboard with aggregated data
            "/api/reports": 2000,    # Report generation (if quick reports)
        }
        
        results = {}
        
        for endpoint, max_time in benchmarks.items():
            times = []
            
            # Test each endpoint multiple times
            for _ in range(5):
                start_time = time.time()
                try:
                    response = session.get(f"{base_url}{endpoint}", timeout=10)
                    response_time = (time.time() - start_time) * 1000
                    times.append(response_time)
                    
                except Exception as e:
                    pytest.fail(f"Benchmark test failed for {endpoint}: {e}")
            
            avg_time = statistics.mean(times)
            results[endpoint] = avg_time
            
            # Assert benchmark is met
            assert avg_time <= max_time, f"{endpoint} benchmark failed: {avg_time}ms > {max_time}ms"
        
        print("Performance Benchmarks Results:")
        for endpoint, time_ms in results.items():
            print(f"  {endpoint}: {time_ms:.2f}ms")
    
    def test_throughput_benchmarks(self, base_url="http://localhost:5000"):
        """Test system throughput benchmarks"""
        import concurrent.futures
        
        # Target: Handle at least 100 requests per second
        target_rps = 100
        test_duration = 10  # seconds
        
        results = []
        start_time = time.time()
        end_time = start_time + test_duration
        
        def make_request():
            session = requests.Session()
            request_start = time.time()
            try:
                response = session.get(f"{base_url}/api/health", timeout=5)
                request_time = time.time() - request_start
                return {
                    "success": response.status_code < 400,
                    "response_time": request_time,
                    "timestamp": request_start
                }
            except Exception:
                return {
                    "success": False,
                    "response_time": None,
                    "timestamp": request_start
                }
        
        # Generate load
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            
            while time.time() < end_time:
                future = executor.submit(make_request)
                futures.append(future)
                time.sleep(1 / target_rps)  # Pace requests to target RPS
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        # Analyze throughput
        actual_duration = time.time() - start_time
        total_requests = len(results)
        successful_requests = len([r for r in results if r["success"]])
        
        actual_rps = total_requests / actual_duration
        success_rate = successful_requests / total_requests * 100 if total_requests > 0 else 0
        
        print(f"Throughput Test Results:")
        print(f"  Target RPS: {target_rps}")
        print(f"  Actual RPS: {actual_rps:.2f}")
        print(f"  Success Rate: {success_rate:.2f}%")
        
        # Validate throughput benchmarks
        assert actual_rps >= target_rps * 0.8, f"Throughput too low: {actual_rps:.2f} < {target_rps * 0.8}"
        assert success_rate >= 95, f"Success rate too low: {success_rate:.2f}%"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])

