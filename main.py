import sys
import logging
from app import app, app_logger, debug

# Ensure unbuffered output for immediate logging
sys.stdout.reconfigure(line_buffering=True)

# Suppress Werkzeug server logs in production mode
logging.getLogger('werkzeug').setLevel(logging.ERROR)

if __name__ == "__main__":
    # Application startup banner
    app_logger.info("=====================================")
    app_logger.info("    Application Starting Up")
    app_logger.info("    Debug Mode: Enabled")
    app_logger.info("    Visit: http://localhost:5000")
    app_logger.info("=====================================")
    
    # Start the Flask development server
    app.run(host="0.0.0.0", port=5000, debug=True)
