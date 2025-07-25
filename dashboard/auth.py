import os
import json
import functools
from flask import request, redirect, url_for, session, jsonify, current_app, render_template
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# Import GCP Secret Manager (optional)
try:
    from google.cloud import secretmanager
    HAS_SECRET_MANAGER = True
except ImportError:
    HAS_SECRET_MANAGER = False

# Global variables
firebase_app = None
firebase_config = {}

def get_secret_from_gcp(secret_name, project_id=None):
    """Fetch a secret from GCP Secret Manager"""
    if not HAS_SECRET_MANAGER:
        return None
    
    try:
        # Use project ID from environment if not provided
        if not project_id:
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT_ID')
        
        if not project_id:
            return None
            
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        current_app.logger.warning(f"Failed to fetch secret {secret_name} from GCP Secret Manager: {str(e)}")
        return None

def init_firebase_admin():
    """Initialize Firebase Admin SDK using service account credentials."""
    global firebase_app, firebase_config
    
    # Check if authentication is disabled
    if os.environ.get("DISABLE_AUTH", "").lower() == "true":
        current_app.logger.warning("Authentication is disabled. Set DISABLE_AUTH=false to enable.")
        return None

    # Load Firebase configuration from environment variables
    firebase_config.update({
        'apiKey': os.environ.get('FIREBASE_API_KEY', ''),
        'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN', ''),
        'projectId': os.environ.get('FIREBASE_PROJECT_ID', ''),
        'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', ''),
        'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID', ''),
        'appId': os.environ.get('FIREBASE_APP_ID', '')
    })
    
    # Validate required Firebase configuration
    required_fields = ['apiKey', 'projectId']
    missing_fields = [field for field in required_fields if not firebase_config.get(field)]
    
    if missing_fields:
        current_app.logger.error(f"Missing required Firebase configuration fields: {', '.join(missing_fields)}")
        current_app.logger.error("Please set the following environment variables:")
        for field in missing_fields:
            env_var = f"FIREBASE_{field.upper()}" if field != 'apiKey' else 'FIREBASE_API_KEY'
            current_app.logger.error(f"  - {env_var}")
        return None
    
    # Log the Firebase config for debugging (without sensitive values)
    safe_config = {k: (v[:10] + '...' if k == 'apiKey' and v else v) for k, v in firebase_config.items()}
    current_app.logger.info(f'Using Firebase client config from environment: {json.dumps(safe_config)}')
    
    # Try to get Firebase service account from GCP Secret Manager first
    service_account_json = None
    secret_name = os.environ.get('FIREBASE_SECRET_NAME', 'garak-firebase-service-account')
    
    # Attempt to fetch from Secret Manager
    service_account_json = get_secret_from_gcp(secret_name)
    
    if service_account_json:
        current_app.logger.info(f"Using Firebase service account from GCP Secret Manager: {secret_name}")
        try:
            # Parse JSON and create credentials
            service_account_info = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_info)
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Invalid JSON in secret {secret_name}: {str(e)}")
            return None
    else:
        # Fallback to file-based credentials
        sa_path = os.environ.get('FIREBASE_CREDENTIALS', '/app/firebase-sa.json')
        current_app.logger.info(f"Looking for Firebase service account file at: {sa_path}")
        
        # Check if service account file exists
        if not os.path.exists(sa_path):
            current_app.logger.error(f"Could not find Firebase service account file at: {sa_path}")
            current_app.logger.error("To fix this issue:")
            current_app.logger.error("1. Set up GCP Secret Manager with secret name: garak-firebase-service-account")
            current_app.logger.error("2. Or create a Firebase project at https://console.firebase.google.com")
            current_app.logger.error("3. Generate a service account key in Project Settings > Service Accounts")
            current_app.logger.error(f"4. Save the key file to: {sa_path}")
            current_app.logger.error("5. Or set FIREBASE_CREDENTIALS environment variable to point to your key file")
            current_app.logger.error("6. Alternatively, set DISABLE_AUTH=true to bypass authentication for development")
            return None
        
        current_app.logger.info(f"Loading Firebase service account from file: {sa_path}")
        cred = credentials.Certificate(sa_path)
    
    try:
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            firebase_app = firebase_admin.initialize_app(cred)
            current_app.logger.info("Firebase Admin SDK initialized successfully")
            return firebase_app
        else:
            current_app.logger.info("Firebase Admin SDK already initialized")
            return firebase_admin.get_app()
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Firebase: {str(e)}")
        current_app.logger.error("Common causes:")
        current_app.logger.error("- Invalid service account key format or permissions")
        current_app.logger.error("- Network connectivity issues")
        current_app.logger.error("- Project ID mismatch between credentials and environment variables")
        current_app.logger.error("- Missing required Firebase APIs enabled in GCP project")
        return None

def get_firebase_config():
    """Get Firebase configuration for client-side initialization"""
    return firebase_config

def get_auth_status():
    """Get the current authentication system status for debugging/user feedback"""
    status = {
        'auth_enabled': os.environ.get("DISABLE_AUTH", "").lower() != "true",
        'firebase_initialized': firebase_app is not None,
        'config_valid': False,
        'service_account_exists': False,
        'errors': [],
        'setup_instructions': []
    }
    
    # Check if authentication is disabled
    if not status['auth_enabled']:
        status['errors'].append("Authentication is disabled via DISABLE_AUTH environment variable")
        return status
    
    # Check Firebase configuration
    required_fields = ['apiKey', 'projectId']
    missing_fields = [field for field in required_fields if not firebase_config.get(field)]
    
    if missing_fields:
        status['errors'].append(f"Missing Firebase configuration: {', '.join(missing_fields)}")
        status['setup_instructions'].extend([
            "Set the following environment variables:",
            "- FIREBASE_API_KEY: Your Firebase API key",
            "- FIREBASE_PROJECT_ID: Your Firebase project ID",
            "- FIREBASE_AUTH_DOMAIN: Your auth domain (project-id.firebaseapp.com)",
            "- FIREBASE_STORAGE_BUCKET: Your storage bucket (project-id.appspot.com)",
            "- FIREBASE_MESSAGING_SENDER_ID: Your messaging sender ID",
            "- FIREBASE_APP_ID: Your Firebase app ID"
        ])
    else:
        status['config_valid'] = True
    
    # Check service account file
    sa_path = os.environ.get('FIREBASE_CREDENTIALS', '/app/firebase-sa.json')
    if os.path.exists(sa_path):
        status['service_account_exists'] = True
    else:
        status['errors'].append(f"Firebase service account file missing: {sa_path}")
        status['setup_instructions'].extend([
            "To set up Firebase service account:",
            "1. Go to https://console.firebase.google.com",
            "2. Select your project",
            "3. Go to Project Settings > Service Accounts",
            "4. Click 'Generate new private key'",
            f"5. Save the downloaded file as: {sa_path}",
            "6. Or set FIREBASE_CREDENTIALS environment variable to your key file path"
        ])
    
    return status

def login_required(view_func):
    """
    Decorator to protect routes that require authentication.
    Checks for either a valid session or a valid Firebase ID token.
    """
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        # Skip authentication if disabled
        if os.environ.get("DISABLE_AUTH", "").lower() == "true":
            return view_func(*args, **kwargs)
        
        # Check if user is authenticated in session
        if session.get('user_id'):
            return view_func(*args, **kwargs)
        
        # Check for Bearer token in Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            try:
                # Verify the ID token
                decoded_token = firebase_auth.verify_id_token(token)
                
                # Create session for the user
                session['user_id'] = decoded_token['uid']
                session['user_email'] = decoded_token.get('email', '')
                
                return view_func(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Token verification failed: {str(e)}")
        
        # Handle API routes differently (return 401 instead of redirect)
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Authentication required'}), 401
        
        # Redirect to login page if not authenticated
        return redirect(url_for('login'))
    
    return wrapped_view

def register_auth_routes(app):
    """Register authentication routes with the Flask app."""
    
    @app.route('/auth/verify-token', methods=['POST'])
    def verify_token():
        """Verify Firebase ID token and create session."""
        # Skip if authentication is disabled
        if os.environ.get("DISABLE_AUTH", "").lower() == "true":
            return jsonify({'success': True, 'message': 'Authentication disabled'})
        
        try:
            data = request.json
            id_token = data.get('idToken')
            
            if not id_token:
                return jsonify({'error': 'No token provided'}), 400
            
            # Verify the ID token
            decoded_token = firebase_auth.verify_id_token(id_token)
            
            # Create session for the user
            session['user_id'] = decoded_token['uid']
            session['user_email'] = decoded_token.get('email', '')
            
            return jsonify({
                'success': True,
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email', '')
            })
        except Exception as e:
            current_app.logger.error(f"Token verification failed: {str(e)}")
            return jsonify({'error': str(e)}), 401
    
    @app.route('/auth/check-session')
    def check_session():
        """Check if the user has a valid session."""
        if os.environ.get("DISABLE_AUTH", "").lower() == "true":
            return jsonify({'valid': True, 'message': 'Authentication disabled'})
        
        if session.get('user_id'):
            return jsonify({
                'valid': True,
                'user_id': session.get('user_id'),
                'email': session.get('user_email', '')
            })
        
        return jsonify({'valid': False}), 401
    
    @app.route('/auth/logout')
    def logout():
        """Clear user session for logout."""
        # Clear session
        session.pop('user_id', None)
        session.pop('user_email', None)
        session.clear()
        
        return jsonify({'success': True})
    
    @app.route('/auth/status')
    def auth_status():
        """Get authentication system status for debugging"""
        return jsonify(get_auth_status())
    
    @app.route('/login')
    def login():
        """Serve the login page."""
        # Skip login if authentication is disabled
        if os.environ.get("DISABLE_AUTH", "").lower() == "true":
            return redirect(url_for('index'))
        
        # If already logged in, redirect to home
        if session.get('user_id'):
            return redirect(url_for('index'))
        
        # Get auth status for better error handling
        auth_status = get_auth_status()
        
        # Render login template with Firebase config and status
        return render_template(
            'login.html',
            firebase_config=get_firebase_config(),
            auth_status=auth_status
        )
