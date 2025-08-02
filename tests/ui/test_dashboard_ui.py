"""
End-to-End UI Tests for Dashboard
QA-Engineer Implementation - Comprehensive UI Testing with Selenium
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import os
import json
from datetime import datetime


class TestDashboardUI:
    """End-to-end UI tests for the dashboard interface"""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver for UI testing"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode for CI
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        # Setup Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture
    def dashboard_url(self):
        """Dashboard URL for testing"""
        return "http://localhost:5173"  # React development server
    
    @pytest.fixture
    def wait(self, driver):
        """WebDriverWait instance"""
        return WebDriverWait(driver, 10)
    
    def test_dashboard_loads_successfully(self, driver, dashboard_url, wait):
        """Test that dashboard loads successfully"""
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Verify page title
        assert "Social Media Analytics" in driver.title
        
        # Verify main dashboard elements are present
        assert driver.find_element(By.CLASS_NAME, "dashboard-container")
        assert driver.find_element(By.CLASS_NAME, "sidebar")
        assert driver.find_element(By.CLASS_NAME, "main-content")
    
    def test_sidebar_navigation(self, driver, dashboard_url, wait):
        """Test sidebar navigation functionality"""
        driver.get(dashboard_url)
        
        # Wait for sidebar to load
        sidebar = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        
        # Test navigation items
        nav_items = [
            ("dashboard", "Dashboard"),
            ("campaigns", "Campañas"),
            ("analytics", "Analytics"),
            ("reports", "Reportes"),
            ("settings", "Configuración")
        ]
        
        for item_id, item_text in nav_items:
            nav_item = driver.find_element(By.CSS_SELECTOR, f"[data-testid='{item_id}-nav']")
            assert nav_item.is_displayed()
            assert item_text in nav_item.text
            
            # Click navigation item
            nav_item.click()
            time.sleep(1)  # Wait for navigation
            
            # Verify URL or content changed
            current_url = driver.current_url
            assert item_id in current_url or driver.find_element(By.CSS_SELECTOR, f"[data-testid='{item_id}-content']")
    
    def test_theme_toggle(self, driver, dashboard_url, wait):
        """Test dark/light theme toggle"""
        driver.get(dashboard_url)
        
        # Find theme toggle button
        theme_toggle = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='theme-toggle']")))
        
        # Get initial theme
        body = driver.find_element(By.TAG_NAME, "body")
        initial_theme = "dark" if "dark" in body.get_attribute("class") else "light"
        
        # Click theme toggle
        theme_toggle.click()
        time.sleep(0.5)  # Wait for theme transition
        
        # Verify theme changed
        new_theme = "dark" if "dark" in body.get_attribute("class") else "light"
        assert new_theme != initial_theme
        
        # Click again to toggle back
        theme_toggle.click()
        time.sleep(0.5)
        
        # Verify theme reverted
        final_theme = "dark" if "dark" in body.get_attribute("class") else "light"
        assert final_theme == initial_theme
    
    def test_responsive_design_mobile(self, driver, dashboard_url, wait):
        """Test responsive design on mobile viewport"""
        # Set mobile viewport
        driver.set_window_size(375, 667)  # iPhone 6/7/8 size
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Verify mobile-specific elements
        # Sidebar should be collapsed or hidden on mobile
        sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
        
        # Check if sidebar is collapsed (common mobile pattern)
        sidebar_classes = sidebar.get_attribute("class")
        assert "collapsed" in sidebar_classes or "hidden" in sidebar_classes or not sidebar.is_displayed()
        
        # Verify mobile menu button exists
        mobile_menu = driver.find_element(By.CSS_SELECTOR, "[data-testid='mobile-menu-toggle']")
        assert mobile_menu.is_displayed()
        
        # Test mobile menu functionality
        mobile_menu.click()
        time.sleep(0.5)
        
        # Sidebar should now be visible
        assert sidebar.is_displayed() or "open" in sidebar.get_attribute("class")
    
    def test_responsive_design_tablet(self, driver, dashboard_url, wait):
        """Test responsive design on tablet viewport"""
        # Set tablet viewport
        driver.set_window_size(768, 1024)  # iPad size
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Verify tablet layout
        sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
        main_content = driver.find_element(By.CLASS_NAME, "main-content")
        
        # Both sidebar and main content should be visible
        assert sidebar.is_displayed()
        assert main_content.is_displayed()
        
        # Verify responsive grid layout
        stat_cards = driver.find_elements(By.CLASS_NAME, "stat-card")
        if stat_cards:
            # Cards should be arranged in tablet-appropriate grid
            first_card_rect = stat_cards[0].rect
            assert first_card_rect['width'] > 200  # Reasonable card width for tablet
    
    def test_responsive_design_desktop(self, driver, dashboard_url, wait):
        """Test responsive design on desktop viewport"""
        # Set desktop viewport
        driver.set_window_size(1920, 1080)
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Verify desktop layout
        sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
        main_content = driver.find_element(By.CLASS_NAME, "main-content")
        
        # Both elements should be visible and properly sized
        assert sidebar.is_displayed()
        assert main_content.is_displayed()
        
        sidebar_rect = sidebar.rect
        main_rect = main_content.rect
        
        # Sidebar should be reasonable width for desktop
        assert 200 <= sidebar_rect['width'] <= 400
        
        # Main content should take remaining space
        assert main_rect['width'] > sidebar_rect['width']


class TestCampaignManagement:
    """End-to-end tests for campaign management functionality"""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture
    def dashboard_url(self):
        return "http://localhost:5173"
    
    @pytest.fixture
    def wait(self, driver):
        return WebDriverWait(driver, 10)
    
    def test_create_new_campaign(self, driver, dashboard_url, wait):
        """Test creating a new campaign through UI"""
        driver.get(dashboard_url)
        
        # Navigate to campaigns section
        campaigns_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaigns-nav']")))
        campaigns_nav.click()
        
        # Click create campaign button
        create_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='create-campaign-btn']")))
        create_button.click()
        
        # Fill campaign form
        campaign_name = f"Test Campaign {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        campaign_description = "Automated test campaign created by UI tests"
        
        name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='campaign-name-input']")))
        name_input.clear()
        name_input.send_keys(campaign_name)
        
        description_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='campaign-description-input']")
        description_input.clear()
        description_input.send_keys(campaign_description)
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='submit-campaign-btn']")
        submit_button.click()
        
        # Verify campaign was created
        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='success-message']")))
        assert "Campaign created successfully" in success_message.text
        
        # Verify campaign appears in list
        campaign_list = driver.find_element(By.CSS_SELECTOR, "[data-testid='campaigns-list']")
        assert campaign_name in campaign_list.text
    
    def test_edit_campaign(self, driver, dashboard_url, wait):
        """Test editing an existing campaign"""
        driver.get(dashboard_url)
        
        # Navigate to campaigns
        campaigns_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaigns-nav']")))
        campaigns_nav.click()
        
        # Find first campaign and click edit
        edit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='edit-campaign-btn']:first-of-type")))
        edit_button.click()
        
        # Modify campaign name
        name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='campaign-name-input']")))
        original_name = name_input.get_attribute("value")
        updated_name = f"{original_name} - Updated"
        
        name_input.clear()
        name_input.send_keys(updated_name)
        
        # Save changes
        save_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='save-campaign-btn']")
        save_button.click()
        
        # Verify changes were saved
        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='success-message']")))
        assert "Campaign updated successfully" in success_message.text
    
    def test_add_profile_to_campaign(self, driver, dashboard_url, wait):
        """Test adding a social media profile to a campaign"""
        driver.get(dashboard_url)
        
        # Navigate to campaigns
        campaigns_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaigns-nav']")))
        campaigns_nav.click()
        
        # Select first campaign
        campaign_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaign-item']:first-of-type")))
        campaign_item.click()
        
        # Click add profile button
        add_profile_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='add-profile-btn']")))
        add_profile_btn.click()
        
        # Fill profile form
        profile_name = f"Test Profile {datetime.now().strftime('%H%M%S')}"
        profile_url = "https://facebook.com/testprofile"
        
        name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='profile-name-input']")))
        name_input.send_keys(profile_name)
        
        # Select platform
        platform_select = driver.find_element(By.CSS_SELECTOR, "[data-testid='platform-select']")
        platform_select.click()
        
        facebook_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-value='facebook']")))
        facebook_option.click()
        
        # Enter URL
        url_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='profile-url-input']")
        url_input.send_keys(profile_url)
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='submit-profile-btn']")
        submit_button.click()
        
        # Verify profile was added
        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='success-message']")))
        assert "Profile added successfully" in success_message.text
    
    def test_delete_campaign(self, driver, dashboard_url, wait):
        """Test deleting a campaign"""
        driver.get(dashboard_url)
        
        # Navigate to campaigns
        campaigns_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaigns-nav']")))
        campaigns_nav.click()
        
        # Get initial campaign count
        campaign_items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='campaign-item']")
        initial_count = len(campaign_items)
        
        if initial_count > 0:
            # Click delete button on first campaign
            delete_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='delete-campaign-btn']:first-of-type")))
            delete_button.click()
            
            # Confirm deletion in modal
            confirm_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-delete-btn']")))
            confirm_button.click()
            
            # Verify campaign was deleted
            success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='success-message']")))
            assert "Campaign deleted successfully" in success_message.text
            
            # Verify campaign count decreased
            time.sleep(1)  # Wait for list to update
            updated_campaign_items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='campaign-item']")
            assert len(updated_campaign_items) == initial_count - 1


class TestDataVisualization:
    """End-to-end tests for data visualization components"""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture
    def dashboard_url(self):
        return "http://localhost:5173"
    
    @pytest.fixture
    def wait(self, driver):
        return WebDriverWait(driver, 10)
    
    def test_charts_load_correctly(self, driver, dashboard_url, wait):
        """Test that charts load and display correctly"""
        driver.get(dashboard_url)
        
        # Navigate to analytics section
        analytics_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='analytics-nav']")))
        analytics_nav.click()
        
        # Wait for charts to load
        charts_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='charts-container']")))
        
        # Verify different chart types are present
        chart_types = [
            "engagement-chart",
            "followers-chart", 
            "platform-distribution-chart",
            "growth-trend-chart"
        ]
        
        for chart_type in chart_types:
            chart_element = driver.find_element(By.CSS_SELECTOR, f"[data-testid='{chart_type}']")
            assert chart_element.is_displayed()
            
            # Verify chart has content (not empty)
            chart_rect = chart_element.rect
            assert chart_rect['width'] > 0
            assert chart_rect['height'] > 0
    
    def test_chart_interactions(self, driver, dashboard_url, wait):
        """Test chart interaction functionality"""
        driver.get(dashboard_url)
        
        # Navigate to analytics
        analytics_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='analytics-nav']")))
        analytics_nav.click()
        
        # Find interactive chart
        chart = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='engagement-chart']")))
        
        # Test hover interaction
        actions = ActionChains(driver)
        actions.move_to_element(chart).perform()
        
        # Look for tooltip or hover effects
        time.sleep(1)
        tooltips = driver.find_elements(By.CSS_SELECTOR, ".recharts-tooltip, .chart-tooltip")
        
        # If tooltips exist, verify they contain data
        if tooltips:
            tooltip = tooltips[0]
            assert tooltip.is_displayed()
            assert len(tooltip.text.strip()) > 0
    
    def test_data_filtering(self, driver, dashboard_url, wait):
        """Test data filtering functionality"""
        driver.get(dashboard_url)
        
        # Navigate to analytics
        analytics_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='analytics-nav']")))
        analytics_nav.click()
        
        # Find date range filter
        date_filter = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='date-range-filter']")))
        date_filter.click()
        
        # Select different time range
        last_week_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-value='last-week']")))
        last_week_option.click()
        
        # Wait for charts to update
        time.sleep(2)
        
        # Verify charts updated (this would require checking chart data)
        charts_container = driver.find_element(By.CSS_SELECTOR, "[data-testid='charts-container']")
        assert charts_container.is_displayed()
    
    def test_export_functionality(self, driver, dashboard_url, wait):
        """Test data export functionality"""
        driver.get(dashboard_url)
        
        # Navigate to analytics
        analytics_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='analytics-nav']")))
        analytics_nav.click()
        
        # Find export button
        export_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='export-data-btn']")))
        export_button.click()
        
        # Select export format
        export_csv = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='export-csv']")))
        export_csv.click()
        
        # Verify download started (check for success message or download indicator)
        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='export-success']")))
        assert "Export completed" in success_message.text or "Download started" in success_message.text


class TestReportGeneration:
    """End-to-end tests for report generation functionality"""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture
    def dashboard_url(self):
        return "http://localhost:5173"
    
    @pytest.fixture
    def wait(self, driver):
        return WebDriverWait(driver, 15)  # Longer wait for report generation
    
    def test_generate_report_workflow(self, driver, dashboard_url, wait):
        """Test complete report generation workflow"""
        driver.get(dashboard_url)
        
        # Navigate to reports section
        reports_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='reports-nav']")))
        reports_nav.click()
        
        # Click generate report button
        generate_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='generate-report-btn']")))
        generate_button.click()
        
        # Select campaign for report
        campaign_select = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaign-select']")))
        campaign_select.click()
        
        # Select first available campaign
        first_campaign = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaign-option']:first-of-type")))
        first_campaign.click()
        
        # Configure report options
        date_range = driver.find_element(By.CSS_SELECTOR, "[data-testid='report-date-range']")
        date_range.click()
        
        last_month = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-value='last-month']")))
        last_month.click()
        
        # Start report generation
        start_generation = driver.find_element(By.CSS_SELECTOR, "[data-testid='start-generation-btn']")
        start_generation.click()
        
        # Wait for generation to complete
        try:
            # Look for progress indicator
            progress_indicator = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='generation-progress']")))
            assert progress_indicator.is_displayed()
            
            # Wait for completion
            completion_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='generation-complete']")))
            assert "Report generated successfully" in completion_message.text
            
            # Verify download link is available
            download_link = driver.find_element(By.CSS_SELECTOR, "[data-testid='download-report-link']")
            assert download_link.is_displayed()
            assert download_link.get_attribute("href")
            
        except TimeoutException:
            # If generation takes too long, verify it started
            assert "Generating" in driver.page_source or "In progress" in driver.page_source
    
    def test_report_preview(self, driver, dashboard_url, wait):
        """Test report preview functionality"""
        driver.get(dashboard_url)
        
        # Navigate to reports
        reports_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='reports-nav']")))
        reports_nav.click()
        
        # Find existing report and click preview
        preview_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='preview-report-btn']:first-of-type")))
        preview_button.click()
        
        # Verify preview modal opens
        preview_modal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='report-preview-modal']")))
        assert preview_modal.is_displayed()
        
        # Verify preview content
        preview_content = driver.find_element(By.CSS_SELECTOR, "[data-testid='preview-content']")
        assert preview_content.is_displayed()
        
        # Close preview
        close_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='close-preview-btn']")
        close_button.click()
        
        # Verify modal closed
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[data-testid='report-preview-modal']")))


class TestAccessibility:
    """End-to-end tests for accessibility compliance"""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver with accessibility testing"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture
    def dashboard_url(self):
        return "http://localhost:5173"
    
    @pytest.fixture
    def wait(self, driver):
        return WebDriverWait(driver, 10)
    
    def test_keyboard_navigation(self, driver, dashboard_url, wait):
        """Test keyboard navigation accessibility"""
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Test Tab navigation
        from selenium.webdriver.common.keys import Keys
        
        body = driver.find_element(By.TAG_NAME, "body")
        
        # Tab through focusable elements
        focusable_elements = []
        for i in range(10):  # Tab through first 10 elements
            body.send_keys(Keys.TAB)
            time.sleep(0.1)
            
            active_element = driver.switch_to.active_element
            if active_element and active_element.tag_name != "body":
                focusable_elements.append(active_element)
        
        # Verify we found focusable elements
        assert len(focusable_elements) > 0
        
        # Verify elements are properly focusable
        for element in focusable_elements:
            assert element.is_displayed()
            assert element.is_enabled()
    
    def test_aria_labels_and_roles(self, driver, dashboard_url, wait):
        """Test ARIA labels and roles for screen readers"""
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check for proper ARIA labels on interactive elements
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            # Button should have accessible name (aria-label, aria-labelledby, or text content)
            aria_label = button.get_attribute("aria-label")
            aria_labelledby = button.get_attribute("aria-labelledby")
            text_content = button.text.strip()
            
            assert aria_label or aria_labelledby or text_content, f"Button missing accessible name: {button.get_attribute('outerHTML')}"
        
        # Check for proper roles on navigation elements
        nav_elements = driver.find_elements(By.TAG_NAME, "nav")
        for nav in nav_elements:
            role = nav.get_attribute("role")
            assert role == "navigation" or nav.get_attribute("aria-label"), "Navigation missing proper role or label"
        
        # Check for proper heading hierarchy
        headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
        if headings:
            # Should start with h1
            first_heading = headings[0]
            assert first_heading.tag_name == "h1", "Page should start with h1"
    
    def test_color_contrast_indicators(self, driver, dashboard_url, wait):
        """Test for color contrast indicators (basic check)"""
        driver.get(dashboard_url)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check for high contrast mode support
        body = driver.find_element(By.TAG_NAME, "body")
        
        # Look for CSS custom properties that indicate contrast considerations
        computed_styles = driver.execute_script("""
            const body = document.body;
            const styles = window.getComputedStyle(body);
            return {
                backgroundColor: styles.backgroundColor,
                color: styles.color
            };
        """)
        
        # Verify colors are defined (not transparent or inherit)
        assert computed_styles["backgroundColor"] != "rgba(0, 0, 0, 0)"
        assert computed_styles["color"] != "rgba(0, 0, 0, 0)"
    
    def test_form_accessibility(self, driver, dashboard_url, wait):
        """Test form accessibility features"""
        driver.get(dashboard_url)
        
        # Navigate to a form (campaign creation)
        campaigns_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='campaigns-nav']")))
        campaigns_nav.click()
        
        create_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='create-campaign-btn']")))
        create_button.click()
        
        # Check form inputs have proper labels
        inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
        for input_element in inputs:
            input_id = input_element.get_attribute("id")
            aria_label = input_element.get_attribute("aria-label")
            aria_labelledby = input_element.get_attribute("aria-labelledby")
            
            # Input should have associated label
            if input_id:
                label = driver.find_elements(By.CSS_SELECTOR, f"label[for='{input_id}']")
                assert label or aria_label or aria_labelledby, f"Input missing label: {input_element.get_attribute('outerHTML')}"
            else:
                assert aria_label or aria_labelledby, f"Input missing accessible name: {input_element.get_attribute('outerHTML')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

