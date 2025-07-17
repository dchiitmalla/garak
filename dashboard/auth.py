import os
import json
import functools
from flask import request, redirect, url_for, session, jsonify, current_app, render_template
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# Global variables
firebase_app = None
firebase_config = {}

def init_firebase_admin():
    """Initialize Firebase Admin SDK using service account credentials."""
    global firebase_app, firebase_config
    
    # Check if authentication is disabled
    if os.environ.get("DISABLE_AUTH", "").lower() == "true":
        current_app.logger.warning("Authentication is disabled. Set DISABLE_AUTH=false to enable.")
        return None

    # Get the path to the Firebase credentials file (default to firebase-sa.json)
    creds_path = os.environ.get("FIREBASE_CREDENTIALS", "firebase-sa.json")
    
    try:
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_path)
            firebase_app = firebase_admin.initialize_app(cred)
            
            # Extract Firebase config information for client use
            with open(creds_path, 'r') as f:
                sa_info = json.load(f)
                
            # Build Firebase client config
            project_id = sa_info.get('project_id', '')
            firebase_config.update({
                'apiKey': os.environ.get('FIREBASE_API_KEY', ''),
                'authDomain': f"{project_id}.firebaseapp.com",
                'projectId': project_id,
                'storageBucket': f"{project_id}.appspot.com",
                'messagingSenderId': sa_info.get('client_id', ''),
                'appId': os.environ.get('FIREBASE_APP_ID', '')
            })
            
            current_app.logger.info("Firebase Admin SDK initialized successfully")
            return firebase_app
        else:
            current_app.logger.info("Firebase Admin SDK already initialized")
            return firebase_admin.get_app()
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Firebase: {str(e)}")
        return None

def get_firebase_config():
    """Get Firebase configuration for client-side initialization"""
    return firebase_config

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
    
    @app.route('/login')
    def login():
        """Serve the login page."""
        # Skip login if authentication is disabled
        if os.environ.get("DISABLE_AUTH", "").lower() == "true":
            return redirect(url_for('index'))
        
        # If already logged in, redirect to home
        if session.get('user_id'):
            return redirect(url_for('index'))
            
        # Render login template with Firebase config
        return render_template(
            'login.html',
            firebase_config=get_firebase_config()
        )
