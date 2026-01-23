# decorator.py
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, current_app
from models.book import User  # Import from your models
# decorator.py - Complete fix
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, current_app
from models.book import User, db  # Make sure to import correctly


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

# decorator.py
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify

def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect('/signin')  # Use direct URL or url_for('signin')
        
        # Import User inside the function to avoid circular imports
        try:
            from models.book import User
            user = User.query.get(session['user_id'])
        except ImportError as e:
            flash('System error. Please try again.', 'error')
            print(f"Import error: {e}")
            return redirect('/signin')
        
        if not user:
            flash('User not found', 'error')
            return redirect('/signin')
        
        # Check premium status
        if not user.is_premium:
            flash('🔒 This feature requires a Premium subscription', 'warning')
            return redirect('/pricing')  # Redirect to the /pricing route
        
        return f(*args, **kwargs)
    return decorated_function

def api_premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_premium:
            return jsonify({
                'error': 'Premium feature',
                'message': 'Upgrade to premium to access this feature',
                'upgrade_url': '/pricing'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function











