# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""
MiroFish Backend - Flask Application Factory
"""

import os
import warnings

# Suppress multiprocessing resource_tracker warnings (from third-party libraries like transformers)
# Must be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure JSON encoding: ensure Chinese displays directly (not as \uXXXX)
    # Flask >= 2.3 uses app.json.ensure_ascii, older versions use JSON_AS_ASCII config
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    # Setup logging
    logger = setup_logger('mirofish')

    # Only print startup info in reloader subprocess (avoid printing twice in debug mode)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish-Offline Backend starting...")
        logger.info("=" * 50)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}})

    # --- Initialize Neo4jStorage singleton (DI via app.extensions) ---
    from .storage import Neo4jStorage
    try:
        neo4j_storage = Neo4jStorage()
        app.extensions['neo4j_storage'] = neo4j_storage
        if should_log_startup:
            logger.info("Neo4jStorage initialized (connected to %s)", Config.NEO4J_URI)
    except Exception as e:
        logger.error("Neo4jStorage initialization failed: %s", e)
        # Store None so endpoints can return 503 gracefully
        app.extensions['neo4j_storage'] = None

    # Register simulation process cleanup function (ensure all simulation processes terminate on server shutdown)
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Simulation process cleanup function registered")

    from .simlab.api import bp as simlab_bp
    app.register_blueprint(simlab_bp, url_prefix='/api/simlab')
    from .simlab.journeys.api import bp as journeys_bp
    app.register_blueprint(journeys_bp, url_prefix='/api/simlab/journeys')

    @app.before_request
    def local_access_only():
        from urllib.parse import urlparse
        if request.host.split(':')[0] not in {'localhost', '127.0.0.1'}:
            return {'success': False, 'error': 'This lab accepts localhost requests only.'}, 403
        origin = request.headers.get('Origin')
        if origin and origin not in {'http://localhost:3000', 'http://127.0.0.1:3000',
                                      'http://localhost:5001', 'http://127.0.0.1:5001'}:
            return {'success': False, 'error': 'Cross-origin access is blocked for the local lab.'}, 403

    # Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Request: {request.method} {request.path}")

    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"Response: {response.status_code}")
        return response

    # Register blueprints
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish-Offline Backend'}

    if should_log_startup:
        logger.info("MiroFish-Offline Backend startup complete")

    return app

