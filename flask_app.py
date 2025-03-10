from flask import Flask, render_template, redirect, url_for, request, send_from_directory, flash, jsonify, g, got_request_exception
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.base import BaseView, expose
import os
import time
import sys
import traceback
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.exceptions import HTTPException

# Try to import psutil, install if not available
try:
    import psutil
except ImportError:
    print("Warning: psutil is not installed. Memory monitoring will be disabled.")
    print("Run 'pip install psutil' to enable memory monitoring.")
    psutil = None

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Setup different loggers for different types of errors
loggers = {
    'http': logging.getLogger('http_errors'),
    'database': logging.getLogger('database_errors'),
    'performance': logging.getLogger('performance_issues'),
    'security': logging.getLogger('security_issues'),
    'validation': logging.getLogger('validation_errors'),
    'uncaught': logging.getLogger('uncaught_exceptions'),
    'memory': logging.getLogger('memory_usage'),
    'summary': logging.getLogger('error_summary')
}

# Configure each logger
for name, logger in loggers.items():
    logger.setLevel(logging.INFO)
    
    # Create a file handler for each logger
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, f'{name}_log.txt'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)

# Error monitoring decorators
def monitor_execution_time(threshold=1.0):
    """
    Decorator to monitor execution time of functions
    
    Args:
        threshold: Time in seconds above which a warning is logged
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > threshold:
                function_name = f.__qualname__
                loggers['performance'].warning(
                    f"Slow function execution: {function_name} took {execution_time:.2f}s"
                )
                
                # Add to summary log
                loggers['summary'].warning(
                    f"PERFORMANCE: Slow function {function_name} - {execution_time:.2f}s"
                )
            
            return result
        return wrapped
    return decorator

def catch_errors(f):
    """
    Decorator to catch and log any exceptions raised by a function
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            function_name = f.__qualname__
            
            # Get exception details
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
            
            # Log the exception
            loggers['uncaught'].error(
                f"Exception in {function_name}: {str(e)}\n{tb_str}"
            )
            
            # Add to summary log
            loggers['summary'].error(
                f"EXCEPTION: {function_name} - {str(e)}"
            )
            
            # Re-raise the exception
            raise
    
    return wrapped

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login if not authenticated

# User model with proper password hashing
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Message model for storing chat history
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('messages', lazy=True))

# Create admin instance first - was previously at the end
admin = Admin(
    app, 
    name='Application Admin', 
    template_mode='bootstrap4'
)

# Secure Admin views with authentication
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

# Custom Admin index view with authentication
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

# Stats view for admin dashboard
class StatsView(BaseView):
    @expose('/')
    def index(self):
        user_count = User.query.count()
        message_count = Message.query.count()
        return self.render('admin/stats.html', user_count=user_count, message_count=message_count)
    
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

# Error Monitor class
class ErrorMonitor:
    """
    A comprehensive error monitoring system for Flask applications.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the error monitoring with a Flask app"""
        self.app = app
        
        # Register error handlers
        app.register_error_handler(Exception, self._handle_exception)
        app.register_error_handler(500, self._handle_server_error)
        
        # Register before and after request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Register signal for uncaught exceptions
        got_request_exception.connect(self._log_exception, app)
        
        # Monitor database connections if possible
        try:
            if hasattr(app, 'extensions') and 'sqlalchemy' in app.extensions:
                import sqlalchemy.event
                self._setup_sqlalchemy_monitoring(sqlalchemy)
        except ImportError:
            app.logger.warning("SQLAlchemy event system not available. Database monitoring disabled.")
        
        # Start memory usage monitoring if psutil is available
        if psutil:
            self._setup_memory_monitoring(app)
        
        app.logger.info("Error monitoring system initialized")
    
    def _before_request(self):
        """Executed before each request"""
        g.start_time = time.time()
        g.request_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(int(time.time() * 1000) % 1000)
        
        # Log the request
        loggers['http'].info(f"[{g.request_id}] Request: {request.method} {request.path} from {request.remote_addr}")
        
        # Validate input parameters
        self._validate_input(request)
    
    def _after_request(self, response):
        """Executed after each request"""
        # Calculate request duration
        duration = time.time() - g.start_time
        
        # Log slow requests (more than 1 second)
        if duration > 1.0:
            loggers['performance'].warning(
                f"[{g.request_id}] Slow request: {request.method} {request.path} took {duration:.2f}s"
            )
        
        # Check for suspicious status codes
        if 400 <= response.status_code < 500:
            loggers['http'].warning(
                f"[{g.request_id}] Client error: {response.status_code} for {request.method} {request.path}"
            )
        elif response.status_code >= 500:
            loggers['http'].error(
                f"[{g.request_id}] Server error: {response.status_code} for {request.method} {request.path}"
            )
        
        # Add request ID to response headers for debugging
        response.headers['X-Request-ID'] = g.request_id
        
        return response
    
    def _handle_exception(self, e):
        """Handle any uncaught exceptions"""
        # Get exception details
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        # Log the exception
        loggers['uncaught'].error(
            f"[{g.get('request_id', 'N/A')}] Uncaught exception: {str(e)}\n{tb_str}"
        )
        
        # Add to summary log
        loggers['summary'].error(
            f"[{g.get('request_id', 'N/A')}] UNCAUGHT EXCEPTION: {str(e)} - {request.path}"
        )
        
        # Return the error to Flask's default handler
        return self.app.handle_exception(e)
    
    def _handle_server_error(self, e):
        """Handle 500 Internal Server Error"""
        loggers['http'].error(
            f"[{g.get('request_id', 'N/A')}] Internal Server Error: {str(e)}"
        )
        
        # Add to summary log
        loggers['summary'].error(
            f"[{g.get('request_id', 'N/A')}] SERVER ERROR 500: {request.path}"
        )
        
        # Return the error to Flask's default handler
        return self.app.handle_http_exception(e)
    
    def _log_exception(self, sender, exception, **extra):
        """Callback for the got_request_exception signal"""
        if isinstance(exception, HTTPException):
            # Already handled by error handlers
            return
        
        # Log the uncaught exception
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        loggers['uncaught'].error(
            f"[{g.get('request_id', 'N/A')}] Exception caught by signal: {str(exception)}\n{tb_str}"
        )
    
    def _validate_input(self, req):
        """Validate request input parameters"""
        # Check for SQL injection attempts in request parameters
        for key, value in req.values.items():
            if isinstance(value, str) and self._check_sql_injection(value):
                loggers['security'].warning(
                    f"[{g.request_id}] Possible SQL injection attempt detected in parameter '{key}': {value}"
                )
                
                # Add to summary log
                loggers['summary'].warning(
                    f"[{g.request_id}] SECURITY: Possible SQL injection in parameter '{key}' - {req.path}"
                )
        
        # Validate content type for POST/PUT requests
        if req.method in ('POST', 'PUT') and req.content_type:
            if 'application/json' in req.content_type and not req.is_json:
                loggers['validation'].warning(
                    f"[{g.request_id}] Content-Type is application/json but no valid JSON was provided"
                )
    
    def _check_sql_injection(self, value):
        """Simple check for SQL injection patterns"""
        suspicious_patterns = [
            "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", 
            "UNION", "OR 1=1", "' OR '", "1' OR '1'='1", 
            "--", "/*", "*/", "EXEC", "EXECUTE"
        ]
        
        value_upper = value.upper()
        for pattern in suspicious_patterns:
            if pattern.upper() in value_upper:
                return True
        return False
    
    def _setup_sqlalchemy_monitoring(self, sqlalchemy_module):
        """Monitor SQLAlchemy database operations"""
        # Track database connection issues
        @sqlalchemy_module.event.listens_for(db.engine, 'connect')
        def connect(dbapi_connection, connection_record):
            loggers['database'].info("Database connection established")
        
        @sqlalchemy_module.event.listens_for(db.engine, 'checkout')
        def checkout(dbapi_connection, connection_record, connection_proxy):
            loggers['database'].debug("Database connection retrieved from pool")
        
        @sqlalchemy_module.event.listens_for(db.engine, 'checkin')
        def checkin(dbapi_connection, connection_record):
            loggers['database'].debug("Database connection returned to pool")
    
    def _setup_memory_monitoring(self, app):
        """Setup periodic memory usage monitoring"""
        def monitor_memory():
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                rss_mb = memory_info.rss / 1024 / 1024  # Convert to MB
                
                loggers['memory'].info(f"Memory usage: {rss_mb:.2f} MB")
                
                # Log high memory usage
                if rss_mb > 500:  # Warning if over 500MB
                    loggers['memory'].warning(f"High memory usage detected: {rss_mb:.2f} MB")
                    loggers['summary'].warning(f"HIGH MEMORY USAGE: {rss_mb:.2f} MB")
            except Exception as e:
                app.logger.error(f"Error monitoring memory: {str(e)}")
        
        # Register a function to be called after each request
        @app.after_request
        def after_request_memory_check(response):
            # Only check occasionally (every 10th request based on time)
            if int(time.time()) % 10 == 0:
                monitor_memory()
            return response


# Initialize error monitoring
error_monitor = ErrorMonitor(app)

# Function to generate summary report
def generate_summary_report():
    """
    Generate a summary report of all errors and issues
    """
    report = []
    report.append("=" * 80)
    report.append("ERROR MONITORING SUMMARY REPORT")
    report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # Count errors by type
    error_counts = {}
    for name in loggers.keys():
        if name != 'summary':
            log_file = os.path.join(logs_dir, f'{name}_log.txt')
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    content = f.read()
                    error_count = content.count(' ERROR ')
                    warning_count = content.count(' WARNING ')
                    error_counts[name] = (error_count, warning_count)
    
    # Add error statistics to report
    report.append("\nERROR STATISTICS:")
    report.append("-" * 40)
    for name, (error_count, warning_count) in error_counts.items():
        report.append(f"{name.upper()}: {error_count} errors, {warning_count} warnings")
    
    # Add most recent errors from summary log
    report.append("\nMOST RECENT ISSUES:")
    report.append("-" * 40)
    summary_log = os.path.join(logs_dir, 'summary_log.txt')
    if os.path.exists(summary_log):
        with open(summary_log, 'r') as f:
            # Get last 20 lines
            lines = f.readlines()
            recent_lines = lines[-20:] if len(lines) > 20 else lines
            for line in recent_lines:
                report.append(line.strip())
    
    # Write report to file
    report_path = os.path.join(logs_dir, f'summary_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    with open(report_path, 'w') as f:
        f.write('\n'.join(report))
    
    return report_path

# Add CLI command to generate error reports
@app.cli.command("generate-error-report")
def error_report_command():
    """Generate a summary report of all errors"""
    report_path = generate_summary_report()
    print(f"Error report generated at: {report_path}")

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes - Now decorated with error monitoring
@app.route('/index')
@monitor_execution_time()
@catch_errors
def home():
    return render_template('index.html')

@app.route('/')
@monitor_execution_time()
@catch_errors
def resume():
    """Serve the resume.html page at the root URL"""
    return render_template('resume.html')

@app.route('/resume.svg')
@monitor_execution_time()
def serve_resume_svg():
    """Serve the SVG file directly"""
    return send_from_directory(".", "resume.svg", mimetype="image/svg+xml")

@app.route('/register', methods=['GET', 'POST'])
@monitor_execution_time()
@catch_errors
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not username or not password or not confirm_password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@monitor_execution_time(threshold=0.5)  # Lower threshold for login (should be fast)
@catch_errors
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        
        # Log failed login attempts
        loggers['security'].warning(f"Failed login attempt for username: {username}")
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
@monitor_execution_time()
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/user-profile')
@login_required
@monitor_execution_time()
@catch_errors
def user_profile():
    """User profile page"""
    return render_template('user_profile.html')

@app.route('/chat')
@login_required
@monitor_execution_time()
@catch_errors
def chat():
    """Chat page for users"""
    # Get the most recent messages (e.g., last 50)
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    messages.reverse()  # Show oldest messages first
    return render_template('chat.html', messages=messages)

@app.route('/check-new-messages')
@login_required
@monitor_execution_time()
@catch_errors
def check_new_messages():
    """API endpoint to check for new unread messages"""
    # This is a simplified example. In a real app, you would:
    # 1. Track when a user last read messages
    # 2. Count messages newer than that timestamp
    
    # For demo purposes, just count messages in the last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    count = Message.query.filter(Message.timestamp > one_hour_ago).count()
    
    return jsonify({'count': count})

@app.route('/change-password', methods=['POST'])
@login_required
@monitor_execution_time()
@catch_errors
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        flash('All fields are required', 'danger')
        return redirect(url_for('user_profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('user_profile'))
    
    # Check current password
    if not current_user.check_password(current_password):
        # Log failed password change attempts
        loggers['security'].warning(f"Failed password change attempt for user: {current_user.username}")
        
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('user_profile'))
    
    # Set new password
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('user_profile'))

# Command to create admin user
@app.cli.command("create-admin")
def create_admin():
    """Create admin user from environment variables or default values"""
    with app.app_context():
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', 'admin_password')
        
        admin = User.query.filter_by(username=username).first()
        if admin:
            admin.is_admin = True
            admin.set_password(password)
            db.session.commit()
            print(f"Existing user {username} updated to admin with new password")
        else:
            admin = User(username=username, is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user {username} created successfully")

# Initialize database
@app.before_first_request
def create_tables():
    db.create_all()
    loggers['summary'].info("Database tables created/verified")

# Socket.IO functionality is moved to a dedicated route with polling
# since WebSockets can be problematic on some PythonAnywhere plans
@app.route('/poll-messages', methods=['GET'])
@monitor_execution_time()
@catch_errors
def poll_messages():
    """Simple long-polling endpoint to replace WebSockets"""
    # Get the latest messages (last 20)
    messages = Message.query.order_by(Message.timestamp.desc()).limit(20).all()
    return jsonify([{
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'username': User.query.get(msg.user_id).username if msg.user_id else 'Anonymous'
    } for msg in reversed(messages)])

@app.route('/send-message', methods=['POST'])
@login_required
@monitor_execution_time()
@catch_errors
def send_message():
    """Endpoint to send a new message"""
    content = request.json.get('message', '')
    if content:
        new_message = Message(content=content, user_id=current_user.id)
        db.session.add(new_message)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Empty message'}), 400

# Set up Admin views
admin.add_view(SecureModelView(User, db.session))
admin.add_view(SecureModelView(Message, db.session))
admin.add_view(StatsView(name='Statistics', endpoint='stats'))

# Log application startup
loggers['summary'].info("============= APPLICATION STARTED =============")

# For local development only
if __name__ == '__main__':
    app.run(debug=True)