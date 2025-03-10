# Flask Web Application with Error Monitoring

## Overview

This is a fully-featured Flask web application that includes user authentication, chat functionality, and a comprehensive error monitoring system. The application is designed with security and performance in mind, offering extensive logging and monitoring capabilities.

## Features

- **User Authentication System**
  - Secure login and registration
  - Password hashing using Werkzeug
  - User profiles with password change functionality
  
- **Admin Dashboard**
  - User management
  - Message monitoring
  - Statistics view
  
- **Chat System**
  - Real-time message updates using polling
  - Message history
  - User-to-user communication

- **Comprehensive Error Monitoring**
  - HTTP error logging
  - Database error tracking
  - Performance monitoring
  - Security issue detection
  - Validation error logging
  - Memory usage monitoring (requires psutil)
  - Detailed error reporting

## Installation

1. Clone the repository
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required dependencies:
   ```bash
   pip install flask flask-sqlalchemy flask-login flask-admin psutil
   ```
4. Set up environment variables (optional):
   ```bash
   export SECRET_KEY="your-secure-secret-key"
   export DATABASE_URL="sqlite:///app.db"  # or your preferred database URL
   export ADMIN_USERNAME="admin"
   export ADMIN_PASSWORD="secure_password"
   ```

## Running the Application

### Local Development

```bash
# Create admin user
flask create-admin

# Run the development server
flask run
# Or
python app.py
```

### Production Deployment

For production deployment, consider using Gunicorn or uWSGI with a proper web server like Nginx or Apache.

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

## Error Monitoring

This application includes a sophisticated error monitoring system that tracks:

- Slow function execution
- HTTP errors
- Database issues
- Security concerns (like potential SQL injection attempts)
- Validation errors
- Memory usage (if psutil is installed)

All logs are stored in the `logs` directory with separate files for different error types.

### Generating Error Reports

To generate a comprehensive error report:

```bash
flask generate-error-report
```

This will create a summary report of all errors and issues in the `logs` directory.

## CLI Commands

- `flask create-admin`: Create an admin user
- `flask generate-error-report`: Generate a summary error report

## Project Structure

- `/templates`: HTML templates
- `/static`: Static files (CSS, JavaScript)
- `/logs`: Application logs and error reports

## Security Features

- Password hashing
- SQL injection detection
- Input validation
- Secure admin access
- Authentication requirements for sensitive routes

## Performance Monitoring

The application monitors:
- Function execution time
- Request processing duration
- Memory usage (if psutil is installed)

## License

MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Contributions are welcome! If you'd like to contribute, please:

1. Fork the repository
2. Create a new branch for your feature
3. Add your changes
4. Submit a pull request

Please make sure to update tests as appropriate.
