#!/usr/bin/env python3
"""
Docker Health Check Script for Social Media Reports System
QA-Engineer Implementation - Comprehensive health monitoring
"""

import sys
import time
import requests
import json
import os
import psutil
from datetime import datetime


class HealthChecker:
    """Comprehensive health checker for the application"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.timeout = 10
        self.checks = []
        
    def log(self, message, level="INFO"):
        """Log health check messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def check_http_endpoint(self):
        """Check if the main HTTP endpoint is responding"""
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.log("✓ HTTP endpoint is healthy")
                return True
            else:
                self.log(f"✗ HTTP endpoint returned status {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"✗ HTTP endpoint check failed: {e}", "ERROR")
            return False
    
    def check_database_connection(self):
        """Check database connectivity"""
        try:
            response = requests.get(
                f"{self.base_url}/api/health/database",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("database_status") == "healthy":
                    self.log("✓ Database connection is healthy")
                    return True
                else:
                    self.log("✗ Database connection is unhealthy", "ERROR")
                    return False
            else:
                self.log(f"✗ Database health check failed with status {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"✗ Database health check failed: {e}", "ERROR")
            return False
    
    def check_redis_connection(self):
        """Check Redis connectivity"""
        try:
            response = requests.get(
                f"{self.base_url}/api/health/redis",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("redis_status") == "healthy":
                    self.log("✓ Redis connection is healthy")
                    return True
                else:
                    self.log("✗ Redis connection is unhealthy", "ERROR")
                    return False
            else:
                self.log(f"✗ Redis health check failed with status {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"✗ Redis health check failed: {e}", "ERROR")
            return False
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                self.log(f"⚠ High CPU usage: {cpu_percent}%", "WARNING")
                return False
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.log(f"⚠ High memory usage: {memory.percent}%", "WARNING")
                return False
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                self.log(f"⚠ High disk usage: {disk.percent}%", "WARNING")
                return False
            
            self.log(f"✓ System resources OK (CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%)")
            return True
            
        except Exception as e:
            self.log(f"✗ System resource check failed: {e}", "ERROR")
            return False
    
    def check_application_status(self):
        """Check application-specific status"""
        try:
            response = requests.get(
                f"{self.base_url}/api/status",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if all services are running
                services_status = data.get("services", {})
                all_healthy = True
                
                for service, status in services_status.items():
                    if status != "healthy":
                        self.log(f"✗ Service {service} is {status}", "ERROR")
                        all_healthy = False
                    else:
                        self.log(f"✓ Service {service} is healthy")
                
                return all_healthy
            else:
                self.log(f"✗ Application status check failed with status {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"✗ Application status check failed: {e}", "ERROR")
            return False
    
    def check_external_dependencies(self):
        """Check external dependencies (Apify API)"""
        try:
            response = requests.get(
                f"{self.base_url}/api/health/external",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                apify_status = data.get("apify_status")
                if apify_status == "healthy":
                    self.log("✓ External dependencies are healthy")
                    return True
                else:
                    self.log(f"⚠ External dependencies status: {apify_status}", "WARNING")
                    # External dependencies being down shouldn't fail health check
                    return True
            else:
                self.log(f"⚠ External dependencies check failed with status {response.status_code}", "WARNING")
                return True  # Don't fail on external dependency issues
                
        except requests.exceptions.RequestException as e:
            self.log(f"⚠ External dependencies check failed: {e}", "WARNING")
            return True  # Don't fail on external dependency issues
    
    def check_file_system(self):
        """Check file system health"""
        try:
            # Check if required directories exist and are writable
            required_dirs = ["/app/reports", "/app/logs", "/app/uploads"]
            
            for directory in required_dirs:
                if not os.path.exists(directory):
                    self.log(f"✗ Required directory missing: {directory}", "ERROR")
                    return False
                
                if not os.access(directory, os.W_OK):
                    self.log(f"✗ Directory not writable: {directory}", "ERROR")
                    return False
            
            # Test file creation
            test_file = "/app/logs/health_check_test.tmp"
            try:
                with open(test_file, 'w') as f:
                    f.write("health check test")
                os.remove(test_file)
                self.log("✓ File system is healthy")
                return True
            except Exception as e:
                self.log(f"✗ File system write test failed: {e}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ File system check failed: {e}", "ERROR")
            return False
    
    def run_all_checks(self):
        """Run all health checks"""
        self.log("Starting comprehensive health check...")
        
        checks = [
            ("HTTP Endpoint", self.check_http_endpoint),
            ("Database Connection", self.check_database_connection),
            ("Redis Connection", self.check_redis_connection),
            ("System Resources", self.check_system_resources),
            ("Application Status", self.check_application_status),
            ("External Dependencies", self.check_external_dependencies),
            ("File System", self.check_file_system)
        ]
        
        results = {}
        overall_health = True
        
        for check_name, check_func in checks:
            self.log(f"Running {check_name} check...")
            try:
                result = check_func()
                results[check_name] = result
                if not result:
                    overall_health = False
            except Exception as e:
                self.log(f"✗ {check_name} check failed with exception: {e}", "ERROR")
                results[check_name] = False
                overall_health = False
        
        # Summary
        self.log("Health check summary:")
        for check_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            self.log(f"  {check_name}: {status}")
        
        if overall_health:
            self.log("🎉 Overall health status: HEALTHY")
            return 0
        else:
            self.log("💥 Overall health status: UNHEALTHY", "ERROR")
            return 1


def main():
    """Main health check function"""
    # Allow for application startup time
    startup_delay = int(os.environ.get("HEALTH_CHECK_STARTUP_DELAY", "5"))
    if startup_delay > 0:
        print(f"Waiting {startup_delay} seconds for application startup...")
        time.sleep(startup_delay)
    
    # Run health checks
    checker = HealthChecker()
    exit_code = checker.run_all_checks()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

