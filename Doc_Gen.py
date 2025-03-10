import argparse
import os
import sys
import json
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
from flask import Flask, render_template, render_template_string, url_for
import xml.etree.ElementTree as ET
import textwrap
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('svg-template-generator')

class SVGTemplateGenerator:
    def __init__(self, app_path=None):
        self.app_path = app_path or os.getcwd()
        self.templates_path = os.path.join(self.app_path, 'templates')
        self.static_path = os.path.join(self.app_path, 'static')
        self.svg_path = os.path.join(self.static_path, 'svg')
        
        # Ensure directories exist
        for path in [self.templates_path, self.static_path, self.svg_path]:
            if not os.path.exists(path):
                os.makedirs(path)
                logger.info(f"Created directory: {path}")
        
        # Setup Jinja environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_path),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Initialize a mock Flask app for URL generation
        self.mock_app = Flask(__name__)
        
        # Default SVG templates
        self.svg_templates = {
            'basic': self._get_basic_svg_template,
            'dashboard': self._get_dashboard_svg_template,
            'profile': self._get_profile_svg_template,
            'stats': self._get_stats_svg_template,
            'resume': self._get_resume_svg_template,
            'custom': None  # Will be set when a custom template is provided
        }
    
    def generate_route(self, route_name, template_name, route_path=None):
        """Generate a Flask route for the template"""
        route_path = route_path or f"/{route_name}"
        
        route_template = textwrap.dedent(f'''
        @app.route('{route_path}')
        @login_required
        @monitor_execution_time()
        @catch_errors
        def {route_name}():
            """Serve the {route_name} page"""
            return render_template('{template_name}')
        ''')
        
        return route_template.strip()
    
    def generate_html_template(self, template_name, title, svg_file, with_nav=True, with_widget=True):
        """Generate an HTML template that embeds an SVG"""
        template_content = textwrap.dedent(f'''
        {{% extends "base.html" %}}
        
        {{% block title %}}{title}{{% endblock %}}
        
        {{% block extra_head %}}
        <style>
            .svg-container {{
                width: 100%;
                height: auto;
                position: relative;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                margin-bottom: 20px;
            }}
            
            .svg-container svg {{
                width: 100%;
                height: auto;
                display: block;
            }}
            
            @media (max-width: 768px) {{
                .svg-container {{
                    margin: 10px 0;
                    box-shadow: none;
                }}
            }}
        </style>
        {{% endblock %}}
        
        {{% block content %}}
        <div class="container mt-4">
            <h1>{title}</h1>
            <div class="svg-container">
                <object data="{{ url_for('static', filename='svg/{svg_file}') }}" type="image/svg+xml" width="100%" height="100%">
                    Your browser does not support SVG
                </object>
            </div>
            
            <!-- Additional content can be added here -->
            <div class="card mt-3">
                <div class="card-body">
                    <h5 class="card-title">Interactive Controls</h5>
                    <p class="card-text">This area can be used for interactive controls that modify the SVG above.</p>
                    <div class="d-flex flex-wrap gap-2">
                        <button class="btn btn-primary" id="refresh-svg">Refresh</button>
                        <button class="btn btn-outline-secondary" id="download-svg">Download SVG</button>
                    </div>
                </div>
            </div>
        </div>
        {{% endblock %}}
        
        {{% block scripts %}}
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                // Example JavaScript for interacting with the SVG
                const refreshButton = document.getElementById('refresh-svg');
                const downloadButton = document.getElementById('download-svg');
                
                if (refreshButton) {{
                    refreshButton.addEventListener('click', function() {{
                        const svgObject = document.querySelector('.svg-container object');
                        // Reload the SVG
                        svgObject.data = svgObject.data;
                    }});
                }}
                
                if (downloadButton) {{
                    downloadButton.addEventListener('click', function() {{
                        // Get SVG data and download it
                        const svgURL = "{{ url_for('static', filename='svg/{svg_file}') }}";
                        fetch(svgURL)
                            .then(response => response.text())
                            .then(svgData => {{
                                const blob = new Blob([svgData], {{type: 'image/svg+xml'}});
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = '{svg_file}';
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                URL.revokeObjectURL(url);
                            }});
                    }});
                }}
            }});
        </script>
        {{% endblock %}}
        ''')
        
        # Write the template to the templates directory
        template_path = os.path.join(self.templates_path, template_name)
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        logger.info(f"Generated HTML template: {template_path}")
        return template_path
    
    def generate_svg_file(self, svg_name, template_type='basic', data=None, custom_template=None):
        """Generate an SVG file based on the template type"""
        if template_type == 'custom' and custom_template:
            self.svg_templates['custom'] = lambda: custom_template
        
        svg_content = self.svg_templates[template_type]()
        
        # Replace placeholders with actual data if provided
        if data:
            for key, value in data.items():
                placeholder = f'{{{{ {key} }}}}'
                svg_content = svg_content.replace(placeholder, str(value))
        
        # Save the SVG file
        svg_file_path = os.path.join(self.svg_path, svg_name)
        with open(svg_file_path, 'w') as f:
            f.write(svg_content)
        
        logger.info(f"Generated SVG file: {svg_file_path}")
        return svg_file_path
    
    def _get_basic_svg_template(self):
        """Basic SVG template with a simple layout"""
        return textwrap.dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" width="100%" height="100%">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&amp;display=swap');
                
                text {
                    font-family: 'Roboto', sans-serif;
                }
                
                .title {
                    font-size: 36px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .subtitle {
                    font-size: 24px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .container {
                    fill: #f8f9fa;
                    stroke: #dee2e6;
                    stroke-width: 1;
                    rx: 10;
                    ry: 10;
                }
                
                .button {
                    fill: #007bff;
                    stroke: #0056b3;
                    stroke-width: 1;
                    rx: 5;
                    ry: 5;
                    cursor: pointer;
                }
                
                .button:hover {
                    fill: #0069d9;
                }
                
                .button-text {
                    font-size: 16px;
                    font-weight: 500;
                    fill: white;
                    text-anchor: middle;
                    dominant-baseline: middle;
                    pointer-events: none;
                }
            </style>
            
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>
            
            <!-- Header area -->
            <rect x="20" y="20" width="960" height="80" class="container"/>
            <text x="40" y="70" class="title">{{ title }}</text>
            
            <!-- Main content area -->
            <rect x="20" y="120" width="960" height="440" class="container"/>
            <text x="40" y="160" class="subtitle">{{ subtitle }}</text>
            
            <!-- Sample interactive elements -->
            <g transform="translate(40, 500)">
                <rect width="160" height="40" class="button" onclick="alert('Button clicked!')"/>
                <text x="80" y="20" class="button-text">Click me</text>
            </g>
            
            <g transform="translate(220, 500)">
                <rect width="160" height="40" class="button" onclick="window.parent.location.href='/index'"/>
                <text x="80" y="20" class="button-text">Go to Home</text>
            </g>
            
            <g transform="translate(400, 500)">
                <rect width="160" height="40" class="button" onclick="document.querySelector('object').data = document.querySelector('object').data;"/>
                <text x="80" y="20" class="button-text">Refresh SVG</text>
            </g>
        </svg>
        ''').strip()
    
    def _get_dashboard_svg_template(self):
        """Dashboard SVG template with multiple panels and charts"""
        return textwrap.dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="100%" height="100%">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&amp;display=swap');
                
                text {
                    font-family: 'Roboto', sans-serif;
                }
                
                .title {
                    font-size: 36px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .panel-title {
                    font-size: 24px;
                    font-weight: 500;
                    fill: #333;
                }
                
                .panel {
                    fill: #f8f9fa;
                    stroke: #dee2e6;
                    stroke-width: 1;
                    rx: 10;
                    ry: 10;
                }
                
                .metric {
                    font-size: 48px;
                    font-weight: 700;
                    fill: #007bff;
                    text-anchor: middle;
                }
                
                .metric-label {
                    font-size: 16px;
                    font-weight: 400;
                    fill: #666;
                    text-anchor: middle;
                }
                
                .chart-bar {
                    fill: #007bff;
                    rx: 5;
                    ry: 5;
                }
                
                .chart-line {
                    fill: none;
                    stroke: #28a745;
                    stroke-width: 3;
                    stroke-linecap: round;
                    stroke-linejoin: round;
                }
                
                .chart-area {
                    fill: url(#gradient);
                    opacity: 0.3;
                }
                
                .chart-point {
                    fill: #28a745;
                    stroke: white;
                    stroke-width: 2;
                }
                
                .chart-axis {
                    stroke: #dee2e6;
                    stroke-width: 1;
                }
                
                .chart-label {
                    font-size: 12px;
                    fill: #666;
                    text-anchor: middle;
                }
            </style>
            
            <!-- Gradient for area chart -->
            <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#28a745" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#28a745" stop-opacity="0"/>
                </linearGradient>
            </defs>
            
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>
            
            <!-- Header -->
            <text x="40" y="60" class="title">{{ title }}</text>
            
            <!-- Metrics Panels -->
            <g transform="translate(40, 100)">
                <!-- Panel 1 -->
                <rect width="260" height="160" class="panel"/>
                <text x="130" y="70" class="metric">{{ metric1_value }}</text>
                <text x="130" y="100" class="metric-label">{{ metric1_label }}</text>
                
                <!-- Panel 2 -->
                <g transform="translate(280, 0)">
                    <rect width="260" height="160" class="panel"/>
                    <text x="130" y="70" class="metric">{{ metric2_value }}</text>
                    <text x="130" y="100" class="metric-label">{{ metric2_label }}</text>
                </g>
                
                <!-- Panel 3 -->
                <g transform="translate(560, 0)">
                    <rect width="260" height="160" class="panel"/>
                    <text x="130" y="70" class="metric">{{ metric3_value }}</text>
                    <text x="130" y="100" class="metric-label">{{ metric3_label }}</text>
                </g>
                
                <!-- Panel 4 -->
                <g transform="translate(840, 0)">
                    <rect width="260" height="160" class="panel"/>
                    <text x="130" y="70" class="metric">{{ metric4_value }}</text>
                    <text x="130" y="100" class="metric-label">{{ metric4_label }}</text>
                </g>
            </g>
            
            <!-- Chart Panels -->
            <g transform="translate(40, 280)">
                <!-- Bar Chart Panel -->
                <rect width="550" height="300" class="panel"/>
                <text x="20" y="30" class="panel-title">{{ chart1_title }}</text>
                
                <!-- Example Bar Chart -->
                <g transform="translate(50, 60)">
                    <!-- X-axis -->
                    <line x1="0" y1="200" x2="450" y2="200" class="chart-axis"/>
                    
                    <!-- Y-axis -->
                    <line x1="0" y1="0" x2="0" y2="200" class="chart-axis"/>
                    
                    <!-- Bars -->
                    <rect x="50" y="50" width="40" height="150" class="chart-bar"/>
                    <rect x="120" y="80" width="40" height="120" class="chart-bar"/>
                    <rect x="190" y="20" width="40" height="180" class="chart-bar"/>
                    <rect x="260" y="100" width="40" height="100" class="chart-bar"/>
                    <rect x="330" y="70" width="40" height="130" class="chart-bar"/>
                    
                    <!-- X-axis Labels -->
                    <text x="70" y="220" class="chart-label">Jan</text>
                    <text x="140" y="220" class="chart-label">Feb</text>
                    <text x="210" y="220" class="chart-label">Mar</text>
                    <text x="280" y="220" class="chart-label">Apr</text>
                    <text x="350" y="220" class="chart-label">May</text>
                </g>
            </g>
            
            <!-- Line Chart Panel -->
            <g transform="translate(610, 280)">
                <rect width="550" height="300" class="panel"/>
                <text x="20" y="30" class="panel-title">{{ chart2_title }}</text>
                
                <!-- Example Line Chart -->
                <g transform="translate(50, 60)">
                    <!-- X-axis -->
                    <line x1="0" y1="200" x2="450" y2="200" class="chart-axis"/>
                    
                    <!-- Y-axis -->
                    <line x1="0" y1="0" x2="0" y2="200" class="chart-axis"/>
                    
                    <!-- Line -->
                    <path d="M50,150 L120,100 L190,120 L260,60 L330,90" class="chart-line"/>
                    
                    <!-- Area under the line -->
                    <path d="M50,150 L120,100 L190,120 L260,60 L330,90 L330,200 L50,200 Z" class="chart-area"/>
                    
                    <!-- Points -->
                    <circle cx="50" cy="150" r="5" class="chart-point"/>
                    <circle cx="120" cy="100" r="5" class="chart-point"/>
                    <circle cx="190" cy="120" r="5" class="chart-point"/>
                    <circle cx="260" cy="60" r="5" class="chart-point"/>
                    <circle cx="330" cy="90" r="5" class="chart-point"/>
                    
                    <!-- X-axis Labels -->
                    <text x="50" y="220" class="chart-label">Day 1</text>
                    <text x="120" y="220" class="chart-label">Day 2</text>
                    <text x="190" y="220" class="chart-label">Day 3</text>
                    <text x="260" y="220" class="chart-label">Day 4</text>
                    <text x="330" y="220" class="chart-label">Day 5</text>
                </g>
            </g>
            
            <!-- Footer area for time period selection -->
            <g transform="translate(40, 600)">
                <rect width="1120" height="60" class="panel"/>
                <text x="560" y="30" class="metric-label" text-anchor="middle">{{ footer_text }}</text>
            </g>
        </svg>
        ''').strip()
    
    def _get_profile_svg_template(self):
        """Profile SVG template with user information and activity stats"""
        return textwrap.dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800" width="100%" height="100%">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&amp;display=swap');
                
                text {
                    font-family: 'Roboto', sans-serif;
                }
                
                .title {
                    font-size: 36px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .profile-name {
                    font-size: 32px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .profile-details {
                    font-size: 16px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .section-title {
                    font-size: 24px;
                    font-weight: 500;
                    fill: #333;
                }
                
                .panel {
                    fill: #f8f9fa;
                    stroke: #dee2e6;
                    stroke-width: 1;
                    rx: 10;
                    ry: 10;
                }
                
                .avatar-circle {
                    fill: #e9ecef;
                    stroke: #dee2e6;
                    stroke-width: 2;
                }
                
                .avatar-icon {
                    fill: #adb5bd;
                }
                
                .button {
                    fill: #007bff;
                    stroke: #0056b3;
                    stroke-width: 1;
                    rx: 5;
                    ry: 5;
                    cursor: pointer;
                }
                
                .button:hover {
                    fill: #0069d9;
                }
                
                .button-text {
                    font-size: 16px;
                    font-weight: 500;
                    fill: white;
                    text-anchor: middle;
                    dominant-baseline: middle;
                    pointer-events: none;
                }
                
                .stat-value {
                    font-size: 24px;
                    font-weight: 700;
                    fill: #007bff;
                    text-anchor: middle;
                }
                
                .stat-label {
                    font-size: 14px;
                    font-weight: 400;
                    fill: #666;
                    text-anchor: middle;
                }
                
                .activity-circle {
                    fill: #28a745;
                    opacity: 0.3;
                }
                
                .activity-day {
                    font-size: 12px;
                    fill: #666;
                    text-anchor: middle;
                }
                
                .activity-month {
                    font-size: 14px;
                    font-weight: 500;
                    fill: #333;
                    text-anchor: middle;
                }
            </style>
            
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>
            
            <!-- Header -->
            <text x="40" y="60" class="title">{{ title }}</text>
            
            <!-- Profile Panel -->
            <g transform="translate(40, 100)">
                <rect width="920" height="220" class="panel"/>
                
                <!-- Avatar -->
                <g transform="translate(60, 50)">
                    <circle cx="60" cy="60" r="60" class="avatar-circle"/>
                    <!-- User icon (placeholder) -->
                    <path d="M60,40 C71,40 80,49 80,60 C80,71 71,80 60,80 C49,80 40,71 40,60 C40,49 49,40 60,40 Z M60,90 C80,90 100,100 100,110 L100,120 L20,120 L20,110 C20,100 40,90 60,90 Z" class="avatar-icon"/>
                </g>
                
                <!-- User Info -->
                <g transform="translate(200, 50)">
                    <text class="profile-name">{{ user_name }}</text>
                    <text y="30" class="profile-details">{{ user_email }}</text>
                    <text y="60" class="profile-details">{{ user_role }}</text>
                    <text y="90" class="profile-details">{{ user_joined }}</text>
                </g>
                
                <!-- Edit Profile Button -->
                <g transform="translate(700, 50)">
                    <rect width="160" height="40" class="button" onclick="alert('Edit profile clicked!')"/>
                    <text x="80" y="20" class="button-text">Edit Profile</text>
                </g>
                
                <!-- Change Password Button -->
                <g transform="translate(700, 110)">
                    <rect width="160" height="40" class="button" onclick="alert('Change password clicked!')"/>
                    <text x="80" y="20" class="button-text">Change Password</text>
                </g>
            </g>
            
            <!-- Statistics Panel -->
            <g transform="translate(40, 340)">
                <rect width="920" height="120" class="panel"/>
                <text x="20" y="30" class="section-title">Statistics</text>
                
                <!-- Stat 1 -->
                <g transform="translate(100, 60)">
                    <text class="stat-value">{{ stat1_value }}</text>
                    <text y="30" class="stat-label">{{ stat1_label }}</text>
                </g>
                
                <!-- Stat 2 -->
                <g transform="translate(300, 60)">
                    <text class="stat-value">{{ stat2_value }}</text>
                    <text y="30" class="stat-label">{{ stat2_label }}</text>
                </g>
                
                <!-- Stat 3 -->
                <g transform="translate(500, 60)">
                    <text class="stat-value">{{ stat3_value }}</text>
                    <text y="30" class="stat-label">{{ stat3_label }}</text>
                </g>
                
                <!-- Stat 4 -->
                <g transform="translate(700, 60)">
                    <text class="stat-value">{{ stat4_value }}</text>
                    <text y="30" class="stat-label">{{ stat4_label }}</text>
                </g>
            </g>
            
            <!-- Activity Calendar Panel -->
            <g transform="translate(40, 480)">
                <rect width="920" height="280" class="panel"/>
                <text x="20" y="30" class="section-title">Activity</text>
                
                <!-- Month labels -->
                <g transform="translate(50, 60)">
                    <text class="activity-month">Jan</text>
                    <text x="120" class="activity-month">Feb</text>
                    <text x="240" class="activity-month">Mar</text>
                    <text x="360" class="activity-month">Apr</text>
                    <text x="480" class="activity-month">May</text>
                    <text x="600" class="activity-month">Jun</text>
                    <text x="720" class="activity-month">Jul</text>
                </g>
                
                <!-- Activity heatmap (simplified) -->
                <g transform="translate(50, 90)">
                    <!-- Week 1 -->
                    <circle cx="20" cy="20" r="12" class="activity-circle" opacity="0.2"/>
                    <circle cx="20" cy="60" r="12" class="activity-circle" opacity="0.4"/>
                    <circle cx="20" cy="100" r="12" class="activity-circle" opacity="0.7"/>
                    <circle cx="20" cy="140" r="12" class="activity-circle" opacity="0.9"/>
                    <circle cx="20" cy="180" r="12" class="activity-circle" opacity="0.3"/>
                    
                    <!-- Sample for multiple weeks -->
                    <g transform="translate(40, 0)">
                        <circle cx="20" cy="20" r="12" class="activity-circle" opacity="0.5"/>
                        <circle cx="20" cy="60" r="12" class="activity-circle" opacity="0.6"/>
                        <circle cx="20" cy="100" r="12" class="activity-circle" opacity="0.3"/>
                        <circle cx="20" cy="140" r="12" class="activity-circle" opacity="0.4"/>
                        <circle cx="20" cy="180" r="12" class="activity-circle" opacity="0.8"/>
                    </g>
                    
                    <!-- Continue with more weeks... -->
                    <!-- For brevity, only showing 2 of the weeks -->
                </g>
                
                <!-- Day labels -->
                <g transform="translate(20, 90)">
                    <text y="20" class="activity-day">Mon</text>
                    <text y="60" class="activity-day">Tue</text>
                    <text y="100" class="activity-day">Wed</text>
                    <text y="140" class="activity-day">Thu</text>
                    <text y="180" class="activity-day">Fri</text>
                </g>
            </g>
        </svg>
        ''').strip()
    
    def _get_stats_svg_template(self):
        """Statistics SVG template with various metrics and charts"""
        return textwrap.dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="100%" height="100%">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&amp;display=swap');
                
                text {
                    font-family: 'Roboto', sans-serif;
                }
                
                .title {
                    font-size: 36px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .subtitle {
                    font-size: 20px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .section-title {
                    font-size: 24px;
                    font-weight: 500;
                    fill: #333;
                }
                
                .panel {
                    fill: #f8f9fa;
                    stroke: #dee2e6;
                    stroke-width: 1;
                    rx: 10;
                    ry: 10;
                }
                
                .donut-chart {
                    fill: none;
                    stroke-width: 30;
                    stroke-linecap: round;
                }
                
                .donut-segment-1 {
                    stroke: #007bff;
                }
                
                .donut-segment-2 {
                    stroke: #28a745;
                }
                
                .donut-segment-3 {
                    stroke: #ffc107;
                }
                
                .donut-segment-4 {
                    stroke: #dc3545;
                }
                
                .chart-label {
                    font-size: 14px;
                    fill: #666;
                }
                
                .chart-value {
                    font-size: 24px;
                    font-weight: 700;
                    fill: #333;
                    text-anchor: middle;
                }
                
                .chart-percentage {
                    font-size: 20px;
                    font-weight: 500;
                    fill: #007bff;
                    text-anchor: middle;
                }
                
                .progress-bg {
                    fill: #e9ecef;
                    rx: 5;
                    ry: 5;
                }
                
                .progress-bar {
                    fill: #007bff;
                    rx: 5;
                    ry: 5;
                }
                
                .legend-box {
                    width: 16px;
                    height: 16px;
                    rx: 2;
                    ry: 2;
                }
                
                .legend-text {
                    font-size: 14px;
                    fill: #666;
                    dominant-baseline: middle;
                }
                
                .axis {
                    stroke: #dee2e6;
                    stroke-width: 1;
                }
                
                .grid-line {
                    stroke: #f1f3f5;
                    stroke-width: 1;
                }
                
                .line-chart {
                    fill: none;
                    stroke-width: 3;
                    stroke-linecap: round;
                    stroke-linejoin: round;
                }
                
                .area-chart {
                    opacity: 0.2;
                }
                
                .data-point {
                    stroke: white;
                    stroke-width: 2;
                }
            </style>
            
            <!-- Gradients and Patterns -->
            <defs>
                <linearGradient id="area-gradient-1" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#007bff" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#007bff" stop-opacity="0"/>
                </linearGradient>
                
                <linearGradient id="area-gradient-2" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#28a745" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#28a745" stop-opacity="0"/>
                </linearGradient>
            </defs>
            
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>
            
            <!-- Header -->
            <text x="40" y="60" class="title">{{ title }}</text>
            <text x="40" y="90" class="subtitle">{{ subtitle }}</text>
            
            <!-- Summary Statistics -->
            <g transform="translate(40, 120)">
                <!-- KPI 1 -->
                <rect width="270" height="120" class="panel"/>
                <text x="20" y="30" class="section-title">{{ kpi1_title }}</text>
                <text x="20" y="70" class="chart-value">{{ kpi1_value }}</text>
                <text x="20" y="95" class="chart-label">{{ kpi1_change }}</text>
                
                <!-- KPI 2 -->
                <g transform="translate(290, 0)">
                    <rect width="270" height="120" class="panel"/>
                    <text x="20" y="30" class="section-title">{{ kpi2_title }}</text>
                    <text x="20" y="70" class="chart-value">{{ kpi2_value }}</text>
                    <text x="20" y="95" class="chart-label">{{ kpi2_change }}</text>
                </g>
                
                <!-- KPI 3 -->
                <g transform="translate(580, 0)">
                    <rect width="270" height="120" class="panel"/>
                    <text x="20" y="30" class="section-title">{{ kpi3_title }}</text>
                    <text x="20" y="70" class="chart-value">{{ kpi3_value }}</text>
                    <text x="20" y="95" class="chart-label">{{ kpi3_change }}</text>
                </g>
                
                <!-- KPI 4 -->
                <g transform="translate(870, 0)">
                    <rect width="270" height="120" class="panel"/>
                    <text x="20" y="30" class="section-title">{{ kpi4_title }}</text>
                    <text x="20" y="70" class="chart-value">{{ kpi4_value }}</text>
                    <text x="20" y="95" class="chart-label">{{ kpi4_change }}</text>
                </g>
            </g>
            
            <!-- Main Charts Section -->
            <g transform="translate(40, 260)">
                <!-- Line Chart Panel -->
                <rect width="830" height="320" class="panel"/>
                <text x="20" y="30" class="section-title">{{ line_chart_title }}</text>
                
                <!-- Line Chart -->
                <g transform="translate(50, 60)">
                    <!-- Axes -->
                    <line x1="0" y1="210" x2="740" y2="210" class="axis"/>
                    <line x1="0" y1="0" x2="0" y2="210" class="axis"/>
                    
                    <!-- Grid Lines -->
                    <line x1="0" y1="160" x2="740" y2="160" class="grid-line"/>
                    <line x1="0" y1="110" x2="740" y2="110" class="grid-line"/>
                    <line x1="0" y1="60" x2="740" y2="60" class="grid-line"/>
                    
                    <!-- X-axis Labels -->
                    <text x="100" y="230" class="chart-label" text-anchor="middle">Jan</text>
                    <text x="200" y="230" class="chart-label" text-anchor="middle">Feb</text>
                    <text x="300" y="230" class="chart-label" text-anchor="middle">Mar</text>
                    <text x="400" y="230" class="chart-label" text-anchor="middle">Apr</text>
                    <text x="500" y="230" class="chart-label" text-anchor="middle">May</text>
                    <text x="600" y="230" class="chart-label" text-anchor="middle">Jun</text>
                    <text x="700" y="230" class="chart-label" text-anchor="middle">Jul</text>
                    
                    <!-- Y-axis Labels -->
                    <text x="-10" y="210" class="chart-label" text-anchor="end">0</text>
                    <text x="-10" y="160" class="chart-label" text-anchor="end">25</text>
                    <text x="-10" y="110" class="chart-label" text-anchor="end">50</text>
                    <text x="-10" y="60" class="chart-label" text-anchor="end">75</text>
                    <text x="-10" y="10" class="chart-label" text-anchor="end">100</text>
                    
                    <!-- Line 1 -->
                    <path d="M50,180 L150,150 L250,160 L350,100 L450,120 L550,80 L650,60" class="line-chart" stroke="#007bff"/>
                    <path d="M50,180 L150,150 L250,160 L350,100 L450,120 L550,80 L650,60 L650,210 L50,210 Z" fill="url(#area-gradient-1)" class="area-chart"/>
                    
                    <!-- Line 2 -->
                    <path d="M50,190 L150,170 L250,140 L350,150 L450,130 L550,110 L650,100" class="line-chart" stroke="#28a745"/>
                    <path d="M50,190 L150,170 L250,140 L350,150 L450,130 L550,110 L650,100 L650,210 L50,210 Z" fill="url(#area-gradient-2)" class="area-chart"/>
                    
                    <!-- Data Points Line 1 -->
                    <circle cx="50" cy="180" r="5" fill="#007bff" class="data-point"/>
                    <circle cx="150" cy="150" r="5" fill="#007bff" class="data-point"/>
                    <circle cx="250" cy="160" r="5" fill="#007bff" class="data-point"/>
                    <circle cx="350" cy="100" r="5" fill="#007bff" class="data-point"/>
                    <circle cx="450" cy="120" r="5" fill="#007bff" class="data-point"/>
                    <circle cx="550" cy="80" r="5" fill="#007bff" class="data-point"/>
                    <circle cx="650" cy="60" r="5" fill="#007bff" class="data-point"/>
                    
                    <!-- Data Points Line 2 -->
                    <circle cx="50" cy="190" r="5" fill="#28a745" class="data-point"/>
                    <circle cx="150" cy="170" r="5" fill="#28a745" class="data-point"/>
                    <circle cx="250" cy="140" r="5" fill="#28a745" class="data-point"/>
                    <circle cx="350" cy="150" r="5" fill="#28a745" class="data-point"/>
                    <circle cx="450" cy="130" r="5" fill="#28a745" class="data-point"/>
                    <circle cx="550" cy="110" r="5" fill="#28a745" class="data-point"/>
                    <circle cx="650" cy="100" r="5" fill="#28a745" class="data-point"/>
                    
                    <!-- Legend -->
                    <g transform="translate(500, 20)">
                        <rect width="16" height="16" fill="#007bff" class="legend-box"/>
                        <text x="24" y="8" class="legend-text">{{ line1_legend }}</text>
                        
                        <g transform="translate(120, 0)">
                            <rect width="16" height="16" fill="#28a745" class="legend-box"/>
                            <text x="24" y="8" class="legend-text">{{ line2_legend }}</text>
                        </g>
                    </g>
                </g>
            </g>
            
            <!-- Secondary Charts -->
            <g transform="translate(890, 260)">
                <!-- Donut Chart Panel -->
                <rect width="270" height="320" class="panel"/>
                <text x="20" y="30" class="section-title">{{ donut_chart_title }}</text>
                
                <!-- Donut Chart -->
                <g transform="translate(135, 160)">
                    <!-- Segments -->
                    <circle cx="0" cy="0" r="80" fill="white"/>
                    <circle cx="0" cy="0" r="60" fill="#f8f9fa"/>
                    
                    <!-- Stroke Segments (approximated using individual arcs) -->
                    <!-- Segment 1: 45% -->
                    <path d="M 0,-60 A 60,60 0 0,1 42.4,42.4" class="donut-chart donut-segment-1"/>
                    
                    <!-- Segment 2: 30% -->
                    <path d="M 42.4,42.4 A 60,60 0 0,1 -30,51.96" class="donut-chart donut-segment-2"/>
                    
                    <!-- Segment 3: 15% -->
                    <path d="M -30,51.96 A 60,60 0 0,1 -58.2,-14.2" class="donut-chart donut-segment-3"/>
                    
                    <!-- Segment 4: 10% -->
                    <path d="M -58.2,-14.2 A 60,60 0 0,1 0,-60" class="donut-chart donut-segment-4"/>
                    
                    <!-- Center Percentage -->
                    <text class="chart-percentage" dy="10">{{ main_percentage }}</text>
                </g>
                
                <!-- Legend -->
                <g transform="translate(30, 240)">
                    <rect width="16" height="16" fill="#007bff" class="legend-box"/>
                    <text x="24" y="8" class="legend-text">{{ segment1_label }} ({{ segment1_value }})</text>
                    
                    <g transform="translate(0, 25)">
                        <rect width="16" height="16" fill="#28a745" class="legend-box"/>
                        <text x="24" y="8" class="legend-text">{{ segment2_label }} ({{ segment2_value }})</text>
                    </g>
                    
                    <g transform="translate(0, 50)">
                        <rect width="16" height="16" fill="#ffc107" class="legend-box"/>
                        <text x="24" y="8" class="legend-text">{{ segment3_label }} ({{ segment3_value }})</text>
                    </g>
                    
                    <g transform="translate(0, 75)">
                        <rect width="16" height="16" fill="#dc3545" class="legend-box"/>
                        <text x="24" y="8" class="legend-text">{{ segment4_label }} ({{ segment4_value }})</text>
                    </g>
                </g>
            </g>
            
            <!-- Progress Bars Section -->
            <g transform="translate(40, 600)">
                <rect width="1120" height="180" class="panel"/>
                <text x="20" y="30" class="section-title">{{ progress_title }}</text>
                
                <!-- Progress Bar 1 -->
                <g transform="translate(20, 50)">
                    <text class="chart-label">{{ progress1_label }}</text>
                    <rect x="200" y="0" width="600" height="20" class="progress-bg"/>
                    <rect x="200" y="0" width="510" height="20" class="progress-bar"/>
                    <text x="820" y="10" class="chart-label" dy="5">{{ progress1_value }}</text>
                </g>
                
                <!-- Progress Bar 2 -->
                <g transform="translate(20, 80)">
                    <text class="chart-label">{{ progress2_label }}</text>
                    <rect x="200" y="0" width="600" height="20" class="progress-bg"/>
                    <rect x="200" y="0" width="420" height="20" class="progress-bar"/>
                    <text x="820" y="10" class="chart-label" dy="5">{{ progress2_value }}</text>
                </g>
                
                <!-- Progress Bar 3 -->
                <g transform="translate(20, 110)">
                    <text class="chart-label">{{ progress3_label }}</text>
                    <rect x="200" y="0" width="600" height="20" class="progress-bg"/>
                    <rect x="200" y="0" width="360" height="20" class="progress-bar"/>
                    <text x="820" y="10" class="chart-label" dy="5">{{ progress3_value }}</text>
                </g>
                
                <!-- Progress Bar 4 -->
                <g transform="translate(20, 140)">
                    <text class="chart-label">{{ progress4_label }}</text>
                    <rect x="200" y="0" width="600" height="20" class="progress-bg"/>
                    <rect x="200" y="0" width="300" height="20" class="progress-bar"/>
                    <text x="820" y="10" class="chart-label" dy="5">{{ progress4_value }}</text>
                </g>
            </g>
        </svg>
        ''').strip()
    
    def _get_resume_svg_template(self):
        """Resume SVG template with skills, experience, and education sections"""
        return textwrap.dedent('''
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1600" width="100%" height="100%">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&amp;display=swap');
                
                text {
                    font-family: 'Roboto', sans-serif;
                }
                
                .name {
                    font-size: 48px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .title {
                    font-size: 24px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .section-title {
                    font-size: 28px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .header {
                    fill: #f8f9fa;
                    stroke: #dee2e6;
                    stroke-width: 1;
                }
                
                .section {
                    fill: #ffffff;
                    stroke: #dee2e6;
                    stroke-width: 1;
                }
                
                .contact-label {
                    font-size: 16px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .contact-value {
                    font-size: 16px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .job-title {
                    font-size: 22px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .job-company {
                    font-size: 20px;
                    font-weight: 500;
                    fill: #555;
                }
                
                .job-date {
                    font-size: 16px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .job-description {
                    font-size: 16px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .edu-degree {
                    font-size: 22px;
                    font-weight: 700;
                    fill: #333;
                }
                
                .edu-school {
                    font-size: 20px;
                    font-weight: 500;
                    fill: #555;
                }
                
                .edu-date {
                    font-size: 16px;
                    font-weight: 400;
                    fill: #666;
                }
                
                .skill-name {
                    font-size: 18px;
                    font-weight: 500;
                    fill: #333;
                }
                
                .skill-bar-bg {
                    fill: #e9ecef;
                    rx: 5;
                    ry: 5;
                }
                
                .skill-bar {
                    fill: #007bff;
                    rx: 5;
                    ry: 5;
                }
                
                .bullet {
                    fill: #007bff;
                }
            </style>
            
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>
            
            <!-- Header Section -->
            <rect x="0" y="0" width="1200" height="200" class="header"/>
            <text x="100" y="80" class="name">{{ name }}</text>
            <text x="100" y="120" class="title">{{ job_title }}</text>
            
            <!-- Contact Information -->
            <g transform="translate(100, 150)">
                <text class="contact-label">Email:</text>
                <text x="60" class="contact-value">{{ email }}</text>
                
                <text x="300" class="contact-label">Phone:</text>
                <text x="360" class="contact-value">{{ phone }}</text>
                
                <text x="550" class="contact-label">Location:</text>
                <text x="630" class="contact-value">{{ location }}</text>
                
                <text x="850" class="contact-label">Website:</text>
                <text x="920" class="contact-value">{{ website }}</text>
            </g>
            
            <!-- Summary Section -->
            <g transform="translate(0, 220)">
                <rect x="50" y="0" width="1100" height="150" class="section"/>
                <text x="80" y="40" class="section-title">Professional Summary</text>
                <text x="80" y="80" class="job-description">{{ summary_line1 }}</text>
                <text x="80" y="110" class="job-description">{{ summary_line2 }}</text>
            </g>
            
            <!-- Experience Section -->
            <g transform="translate(0, 400)">
                <rect x="50" y="0" width="1100" height="500" class="section"/>
                <text x="80" y="40" class="section-title">Work Experience</text>
                
                <!-- Job 1 -->
                <g transform="translate(80, 80)">
                    <text class="job-title">{{ job1_title }}</text>
                    <text y="30" class="job-company">{{ job1_company }}</text>
                    <text y="55" class="job-date">{{ job1_dates }}</text>
                    
                    <!-- Job 1 Responsibilities -->
                    <g transform="translate(20, 85)">
                        <circle r="5" class="bullet"/>
                        <text x="15" class="job-description">{{ job1_resp1 }}</text>
                    </g>
                    
                    <g transform="translate(20, 115)">
                        <circle r="5" class="bullet"/>
                        <text x="15" class="job-description">{{ job1_resp2 }}</text>
                    </g>
                    
                    <g transform="translate(20, 145)">
                        <circle r="5" class="bullet"/>
                        <text x="15" class="job-description">{{ job1_resp3 }}</text>
                    </g>
                </g>
                
                <!-- Job 2 -->
                <g transform="translate(80, 260)">
                    <text class="job-title">{{ job2_title }}</text>
                    <text y="30" class="job-company">{{ job2_company }}</text>
                    <text y="55" class="job-date">{{ job2_dates }}</text>
                    
                    <!-- Job 2 Responsibilities -->
                    <g transform="translate(20, 85)">
                        <circle r="5" class="bullet"/>
                        <text x="15" class="job-description">{{ job2_resp1 }}</text>
                    </g>
                    
                    <g transform="translate(20, 115)">
                        <circle r="5" class="bullet"/>
                        <text x="15" class="job-description">{{ job2_resp2 }}</text>
                    </g>
                    
                    <g transform="translate(20, 145)">
                        <circle r="5" class="bullet"/>
                        <text x="15" class="job-description">{{ job2_resp3 }}</text>
                    </g>
                </g>
            </g>
            
            <!-- Education Section -->
            <g transform="translate(0, 930)">
                <rect x="50" y="0" width="1100" height="200" class="section"/>
                <text x="80" y="40" class="section-title">Education</text>
                
                <!-- Degree 1 -->
                <g transform="translate(80, 80)">
                    <text class="edu-degree">{{ degree1 }}</text>
                    <text y="30" class="edu-school">{{ school1 }}</text>
                    <text y="55" class="edu-date">{{ education1_dates }}</text>
                </g>
                
                <!-- Degree 2 (if applicable) -->
                <g transform="translate(600, 80)">
                    <text class="edu-degree">{{ degree2 }}</text>
                    <text y="30" class="edu-school">{{ school2 }}</text>
                    <text y="55" class="edu-date">{{ education2_dates }}</text>
                </g>
            </g>
            
            <!-- Skills Section -->
            <g transform="translate(0, 1160)">
                <rect x="50" y="0" width="1100" height="400" class="section"/>
                <text x="80" y="40" class="section-title">Skills</text>
                
                <!-- Left Column Skills -->
                <g transform="translate(80, 80)">
                    <!-- Skill 1 -->
                    <text class="skill-name">{{ skill1 }}</text>
                    <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                    <rect x="200" y="-10" width="{{ skill1_level }}" height="20" class="skill-bar"/>
                    
                    <!-- Skill 2 -->
                    <g transform="translate(0, 40)">
                        <text class="skill-name">{{ skill2 }}</text>
                        <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                        <rect x="200" y="-10" width="{{ skill2_level }}" height="20" class="skill-bar"/>
                    </g>
                    
                    <!-- Skill 3 -->
                    <g transform="translate(0, 80)">
                        <text class="skill-name">{{ skill3 }}</text>
                        <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                        <rect x="200" y="-10" width="{{ skill3_level }}" height="20" class="skill-bar"/>
                    </g>
                    
                    <!-- Skill 4 -->
                    <g transform="translate(0, 120)">
                        <text class="skill-name">{{ skill4 }}</text>
                        <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                        <rect x="200" y="-10" width="{{ skill4_level }}" height="20" class="skill-bar"/>
                    </g>
                </g>
                
                <!-- Right Column Skills -->
                <g transform="translate(600, 80)">
                    <!-- Skill 5 -->
                    <text class="skill-name">{{ skill5 }}</text>
                    <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                    <rect x="200" y="-10" width="{{ skill5_level }}" height="20" class="skill-bar"/>
                    
                    <!-- Skill 6 -->
                    <g transform="translate(0, 40)">
                        <text class="skill-name">{{ skill6 }}</text>
                        <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                        <rect x="200" y="-10" width="{{ skill6_level }}" height="20" class="skill-bar"/>
                    </g>
                    
                    <!-- Skill 7 -->
                    <g transform="translate(0, 80)">
                        <text class="skill-name">{{ skill7 }}</text>
                        <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                        <rect x="200" y="-10" width="{{ skill7_level }}" height="20" class="skill-bar"/>
                    </g>
                    
                    <!-- Skill 8 -->
                    <g transform="translate(0, 120)">
                        <text class="skill-name">{{ skill8 }}</text>
                        <rect x="200" y="-10" width="300" height="20" class="skill-bar-bg"/>
                        <rect x="200" y="-10" width="{{ skill8_level }}" height="20" class="skill-bar"/>
                    </g>
                </g>
            </g>
        </svg>
        ''').strip()
    
    def create_template(self, template_name, template_type, route_name=None, 
                      title=None, svg_file_name=None, data=None, custom_svg=None):
        """Create a new template with associated route and SVG file"""
        
        # Set default values
        title = title or f"{template_name.replace('_', ' ').title()} Page"
        route_name = route_name or template_name.lower().replace(' ', '_')
        svg_file_name = svg_file_name or f"{template_name.lower().replace(' ', '_')}.svg"
        
        # Generate SVG file
        self.generate_svg_file(svg_file_name, template_type, data, custom_svg)
        
        # Generate HTML template
        html_template_name = f"{template_name.lower().replace(' ', '_')}.html"
        self.generate_html_template(html_template_name, title, svg_file_name)
        
        # Generate route
        route_code = self.generate_route(route_name, html_template_name)
        
        result = {
            'template_name': html_template_name,
            'template_path': os.path.join(self.templates_path, html_template_name),
            'svg_name': svg_file_name,
            'svg_path': os.path.join(self.svg_path, svg_file_name),
            'route_name': route_name,
            'route_code': route_code
        }
        
        logger.info(f"Created template: {result['template_name']}")
        logger.info(f"Created SVG: {result['svg_name']}")
        logger.info(f"Generated route: {result['route_name']}")
        
        return result

def main():
    parser = argparse.ArgumentParser(description='Generate SVG templates and pages for Flask app')
    parser.add_argument('--app-path', help='Path to the Flask application', default=os.getcwd())
    parser.add_argument('--template-name', help='Name of the template to create', required=True)
    parser.add_argument('--template-type', help='Type of SVG template to use', 
                        choices=['basic', 'dashboard', 'profile', 'stats', 'resume', 'custom'], 
                        default='basic')
    parser.add_argument('--title', help='Title for the page', default=None)
    parser.add_argument('--route-name', help='Name for the Flask route', default=None)
    parser.add_argument('--data', help='JSON data for the template placeholders', default=None)
    parser.add_argument('--custom-svg', help='Path to a custom SVG template file', default=None)
    parser.add_argument('--log-level', help='Logging level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        default='INFO')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=getattr(logging, args.log_level),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Parse JSON data if provided
    data = None
    if args.data:
        try:
            with open(args.data, 'r') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading JSON data file: {e}")
            sys.exit(1)
    
    # Load custom SVG if provided
    custom_svg = None
    if args.custom_svg and args.template_type == 'custom':
        try:
            with open(args.custom_svg, 'r') as f:
                custom_svg = f.read()
        except IOError as e:
            logger.error(f"Error loading custom SVG file: {e}")
            sys.exit(1)
    
    try:
        generator = SVGTemplateGenerator(args.app_path)
        result = generator.create_template(
            template_name=args.template_name,
            template_type=args.template_type,
            route_name=args.route_name,
            title=args.title,
            data=data,
            custom_svg=custom_svg
        )
        
        print("\nTemplate generated successfully:")
        print(f"- Template file: {result['template_path']}")
        print(f"- SVG file: {result['svg_path']}")
        print(f"- Route: '{result['route_name']}' (add to your Flask app)")
        print("\nRoute code to add:")
        print(result['route_code'])
        
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()