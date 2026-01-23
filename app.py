from models.book import db, User, Shelf, Book, ReferralCode, Referral, EmailVerificationOTP, UserDailyProgress


from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
from functools import wraps
import os
from config import Config
from models.book import db, User, Shelf, Book
from models.book import UserDailyProgress
from decorator import premium_required, api_premium_required
from dotenv import load_dotenv
import razorpay
import hmac
import hashlib
from datetime import date
from sqlalchemy.orm.attributes import flag_modified
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm.attributes import flag_modified
import json
from urllib.request import urlopen
from urllib.error import URLError
from datetime import timedelta
from decorator import premium_required, api_premium_required
# Add these imports at the top of app.py (with existing imports)
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urlparse, parse_qs
import uuid
import random
import string
from flask_mail import Mail, Message
import random
import string
from datetime import timedelta
import json



# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")  # Use fallback for development

# Initialize Razorpay (India payments only)
razorpay_client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID", "rzp_test_dummy"),
    os.getenv("RAZORPAY_KEY_SECRET", "dummy_secret")
))

# Initialize Flask-Mail
mail = Mail(app)

db.init_app(app)

with app.app_context():
    db.create_all()

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# helper function to check allowed file extensions
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in app.config.get("ALLOWED_EXTENSIONS", {"pdf", "txt", "epub", "docx"})
    )

# sanity check prints
print("Database path:", os.path.abspath("app.db"))
print("DATABASE URI:", app.config["SQLALCHEMY_DATABASE_URI"])

# login required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("signin"))
        return f(*args, **kwargs)
    return decorated

# Helper function to check if user has active premium access
def get_user_premium_status(user_id):
    """Get current premium status and days left"""
    user = db.session.get(User, user_id)
    if not user:
        return False, 0
    
    # Check if premium has expired
    if user.premium_until and datetime.utcnow() > user.premium_until:
        user.is_premium = False
        db.session.commit()
        return False, 0
    
    if user.is_premium and user.premium_until:
        days_left = (user.premium_until - datetime.utcnow()).days
        return True, max(days_left, 0)
    
    return False, 0

# Decorator to check premium status
def premium_check_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("signin"))
        
        is_premium, days_left = get_user_premium_status(session["user_id"])
        
        if not is_premium:
            return render_template("pricing.html", 
                                 error="This feature requires premium access. Please upgrade your account.",
                                 is_premium=False,
                                 days_left=0)
        
        # Pass premium info to the function
        kwargs['is_premium'] = is_premium
        kwargs['days_left'] = days_left
        return f(*args, **kwargs)
    return decorated


def parse_goodreads_rss(rss_url):
    """
    Parse Goodreads RSS feed and extract book data
    Returns list of book dictionaries with normalized data
    """
    try:
        # Add user-agent header to avoid 403 Forbidden from Goodreads
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch RSS feed
        response = requests.get(rss_url, timeout=10, headers=headers)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Goodreads uses these namespaces
        ns = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'gr': 'http://www.goodreads.com/gr/rss/'
        }
        
        books = []
        
        # Extract all items (each is a book)
        for item in root.findall('.//item'):
            try:
                # Extract basic info
                title = item.findtext('title', '').strip()
                
                # Author is inside a description tag, extract from HTML
                description = item.findtext('description', '')
                
                # Get total pages from Goodreads XML
                num_pages = item.findtext('gr:num_pages', '')
                try:
                    total_pages = int(num_pages) if num_pages and num_pages.strip() else None
                except:
                    total_pages = None
                
                # If no page number, default to 1
                if not total_pages or total_pages <= 0:
                    total_pages = 1
                
                # Get Goodreads shelves to determine status
                user_shelves = item.findtext('gr:user_shelves', '')
                
                print(f"Book: {title}, Shelves: {user_shelves}, Pages: {total_pages}")
                
                status = 'on_shelf'  # default
                current_page = 0
                
                # Logic to determine status based on shelf
                if user_shelves:
                    shelves_lower = user_shelves.lower()
                    
                    if 'currently-reading' in shelves_lower:
                        status = 'active'
                        current_page = 0
                    elif 'read' in shelves_lower and 'to-read' not in shelves_lower:
                        # Book is in "read" shelf (not "to-read")
                        status = 'on_shelf'
                        current_page = total_pages  # Mark as completed
                    elif 'to-read' in shelves_lower:
                        status = 'on_shelf'
                        current_page = 0
                    else:
                        status = 'on_shelf'
                        current_page = 0
                else:
                    # No shelf info, default to unread
                    status = 'on_shelf'
                    current_page = 0
                
                # Only add if title exists
                if title:
                    books.append({
                        'book_name': title,
                        'total_pages': total_pages,
                        'status': status,
                        'current_page': current_page,
                        'description': description
                    })
            
            except Exception as e:
                print(f"Error parsing book item: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return books, None
    
    except requests.exceptions.RequestException as e:
        return None, f"Failed to fetch RSS feed: {str(e)}"
    except ET.ParseError as e:
        return None, f"Invalid RSS feed format: {str(e)}"
    except Exception as e:
        return None, f"Error parsing feed: {str(e)}"



# landing main page
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")



# log in page
@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # Set login time and check for daily/yearly resets
            user.last_login = datetime.utcnow()
            user.reset_daily_time_if_needed()
            user.reset_yearly_time_if_needed()
            db.session.commit()
            
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["login_time"] = datetime.utcnow().isoformat()  # Track session start
            return redirect(url_for("dashboard"))
        return render_template("signin.html", error="Invalid email or password")
    return render_template("signin.html")





# ============================================
# UPDATED SIGNUP ROUTES (Replace in app.py)
# ============================================

# ============================================
# FIXED OTP VERIFICATION SYSTEM FOR app.py
# Replace the entire signup section with this
# ============================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Sign up with OTP verification - only sends OTP, doesn't create account yet"""
    if request.method == 'POST':
        name = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        terms_accepted = request.form.get('terms_accepted')
        referral_code = request.form.get('referral_code', '').strip()
        
        # Validate inputs
        if not name or not email or not password:
            return jsonify(success=False, error='All fields are required'), 400
        
        if not terms_accepted:
            return jsonify(success=False, error='You must agree to Terms and Conditions'), 400
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify(success=False, error='Please enter a valid email address'), 400
        
        # Check if email already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify(success=False, error='Email already registered. Please sign in instead.'), 400
        
        try:
            # Delete old OTP records if they exist
            old_otp = EmailVerificationOTP.query.filter_by(email=email).first()
            if old_otp:
                db.session.delete(old_otp)
                db.session.commit()
            
            # Generate 6-digit OTP
            otp_code = generate_otp()
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            
            # Save OTP to database
            otp_record = EmailVerificationOTP(
                email=email,
                otp_code=otp_code,
                expires_at=expires_at,
                attempts=0
            )
            db.session.add(otp_record)
            db.session.commit()
            
            # Store signup data in session temporarily
            session['signup_data'] = {
                'username': name,
                'email': email,
                'password': password,
                'referral_code': referral_code,
                'terms_accepted': terms_accepted
            }
            session.permanent = True
            
            # Send OTP email
            email_sent = send_otp_email(email, otp_code, name)
            
            if email_sent:
                print(f"✅ OTP sent successfully to {email}")
                return jsonify(success=True, message='OTP sent to your email'), 200
            else:
                # Delete OTP if email sending failed
                db.session.delete(otp_record)
                db.session.commit()
                session.pop('signup_data', None)
                print(f"❌ Failed to send OTP email to {email}")
                return jsonify(success=False, error='Failed to send verification code. Please try again.'), 500
        
        except Exception as e:
            print(f"❌ Error in signup: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            session.pop('signup_data', None)
            return jsonify(success=False, error='An error occurred. Please try again.'), 500
    
    # GET request - render signup page
    referral_code = request.args.get('ref', '')
    return render_template('signup.html', referral_code=referral_code)


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and create account with referral handling"""
    
    if 'signup_data' not in session:
        return jsonify(success=False, error='Session expired. Please sign up again.'), 400
    
    try:
        signup_data = session['signup_data']
        email = signup_data['email']
        otp_input = request.form.get('otp_code', '').strip()
        
        if not otp_input:
            return jsonify(success=False, error='Please enter the verification code'), 400
        
        # Validate OTP format
        if len(otp_input) != 6 or not otp_input.isdigit():
            return jsonify(success=False, error='Please enter a valid 6-digit code'), 400
        
        # Get OTP record
        otp_record = EmailVerificationOTP.query.filter_by(email=email).first()
        
        if not otp_record:
            print(f"❌ No OTP record found for {email}")
            return jsonify(success=False, error='No verification code found. Please sign up again.'), 404
        
        # Check if expired
        if otp_record.is_expired():
            print(f"⏰ OTP expired for {email}")
            db.session.delete(otp_record)
            db.session.commit()
            session.pop('signup_data', None)
            return jsonify(success=False, error='Verification code expired. Please request a new one.'), 400
        
        # Check attempts
        if otp_record.attempts >= 5:
            print(f"❌ Too many failed attempts for {email}")
            db.session.delete(otp_record)
            db.session.commit()
            session.pop('signup_data', None)
            return jsonify(success=False, error='Too many failed attempts. Please sign up again.'), 400
        
        # Check if OTP matches
        if otp_record.otp_code != otp_input:
            otp_record.attempts += 1
            db.session.commit()
            remaining = 5 - otp_record.attempts
            print(f"⚠️ Wrong OTP attempt #{otp_record.attempts} for {email}")
            return jsonify(success=False, error=f'Invalid code. {remaining} attempts remaining'), 400
        
        # ✅ OTP is correct - create user account
        print(f"✅ OTP verified for {email}. Creating account...")
        
        name = signup_data['username']
        password = signup_data['password']
        referral_code = signup_data.get('referral_code')
        
        # Create user
        user = User(name=name, email=email)
        user.set_password(password)
        user.is_email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.is_premium = True
        user.premium_since = datetime.utcnow()
        user.premium_until = datetime.utcnow() + timedelta(days=30)
        
        db.session.add(user)
        db.session.flush()  # Get user ID without committing
        
        # Handle referral - ONLY if email is verified
        if referral_code:
            print(f"🎁 Processing referral code: {referral_code}")
            referral_code_obj = ReferralCode.query.filter_by(referral_code=referral_code).first()
            
            if referral_code_obj and referral_code_obj.user_id != user.id:
                referral = Referral(
                    referrer_id=referral_code_obj.user_id,
                    referred_id=user.id,
                    referral_code=referral_code,
                    status='completed'
                )
                db.session.add(referral)
                
                # Give referrer bonus (30 days premium)
                referrer = db.session.get(User, referral_code_obj.user_id)
                if referrer:
                    referrer.is_premium = True
                    if not referrer.premium_until or referrer.premium_until < datetime.utcnow():
                        referrer.premium_until = datetime.utcnow() + timedelta(days=30)
                    else:
                        referrer.premium_until += timedelta(days=30)
                    referral.referrer_reward_given = True
                    referral.referred_reward_given = True
                    print(f"🎁 Referrer {referrer.name} gets 30 days bonus")
        
        # Generate referral code for new user
        new_referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        new_referral_code_obj = ReferralCode(
            user_id=user.id,
            referral_code=new_referral_code
        )
        db.session.add(new_referral_code_obj)
        
        # Mark OTP as verified
        otp_record.is_verified = True
        db.session.commit()
        
        print(f"✅ User account created: {user.email} (ID: {user.id})")
        
        # Clear session data
        session.pop('signup_data', None)
        
        # Log user in
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['login_time'] = datetime.utcnow().isoformat()
        
        return jsonify(success=True, message='Email verified! Logging you in...'), 200
    
    except Exception as e:
        print(f"❌ Error in verify_otp: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify(success=False, error='An error occurred. Please try again.'), 500


@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP to email"""
    
    if 'signup_data' not in session:
        return jsonify(success=False, error='Session expired. Please sign up again.'), 400
    
    try:
        signup_data = session['signup_data']
        email = signup_data['email']
        username = signup_data['username']
        
        # Delete old OTP
        old_otp = EmailVerificationOTP.query.filter_by(email=email).first()
        if old_otp:
            db.session.delete(old_otp)
            db.session.commit()
        
        # Generate new OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        otp_record = EmailVerificationOTP(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at,
            attempts=0  # Reset attempts
        )
        db.session.add(otp_record)
        db.session.commit()
        
        # Send OTP email
        email_sent = send_otp_email(email, otp_code, username)
        
        if email_sent:
            print(f"✅ Resent OTP to {email}")
            return jsonify(success=True, message='New code sent to your email!'), 200
        else:
            db.session.delete(otp_record)
            db.session.commit()
            print(f"❌ Failed to resend OTP to {email}")
            return jsonify(success=False, error='Failed to send code. Please try again.'), 500
    
    except Exception as e:
        print(f"❌ Error in resend_otp: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify(success=False, error='An error occurred. Please try again.'), 500


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp_code, username):
    """Send OTP email to user using Flask-Mail"""
    try:
        msg = Message(
            subject='🔐 Your BookEx Chelf Email Verification Code',
            recipients=[email],
            html=f"""
            <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f9f9f9; border-radius: 8px; border: 1px solid #e0e0e0;">
                        
                        <!-- Header -->
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #667eea; margin: 0; font-size: 28px;">📚 BookEx Chelf</h1>
                            <p style="color: #666; margin: 5px 0 0 0; font-size: 14px;">Your Personal Reading Companion</p>
                        </div>
                        
                        <!-- Main Content -->
                        <div style="background: white; padding: 30px; border-radius: 8px;">
                            <h2 style="color: #333; margin-top: 0;">Hi <strong>{username}</strong>,</h2>
                            
                            <p style="color: #555; font-size: 16px;">
                                Welcome to BookEx Chelf! To complete your registration, please verify your email address using the code below:
                            </p>
                            
                            <!-- OTP Code Display -->
                            <div style="text-align: center; margin: 30px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 8px;">
                                <p style="margin: 0; color: #fff; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Your Verification Code</p>
                                <p style="font-size: 48px; font-weight: bold; color: white; letter-spacing: 8px; margin: 15px 0; font-family: 'Courier New', monospace;">
                                    {otp_code}
                                </p>
                            </div>
                            
                            <!-- Info -->
                            <div style="background: #f0f4ff; border-left: 4px solid #667eea; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                                <p style="color: #667eea; margin: 0; font-weight: 600;">⏰ This code expires in 10 minutes</p>
                            </div>
                            
                            <p style="color: #666; font-size: 14px; line-height: 1.8;">
                                • Don't share this code with anyone<br>
                                • If you didn't request this code, you can safely ignore this email<br>
                                • Each code can only be used once
                            </p>
                            
                            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;">
                            
                            <!-- Footer -->
                            <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                                BookEx Chelf Team<br>
                                <a href="https://bookexchelf.com" style="color: #667eea; text-decoration: none;">Visit our website</a>
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
        )
        
        mail.send(msg)
        print(f"✅ OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending OTP email: {e}")
        import traceback
        traceback.print_exc()
        return False
# At the end of your signup route, before session['user_id'] = user.id, add:








from flask import Flask, request
import requests


@app.route('/import-goodreads', methods=['POST'])
@login_required
def import_goodreads():
    """
    Import books from Goodreads RSS feed
    """
    try:
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify(success=False, error="User not found"), 401
        
        data = request.get_json()
        rss_url = data.get('rss_url', '').strip()
        
        if not rss_url:
            return jsonify(success=False, error="RSS URL is required"), 400
        
        # Validate URL
        try:
            result = urlparse(rss_url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
        except:
            return jsonify(success=False, error="Invalid RSS URL format"), 400
        
        # Parse RSS feed
        books_data, error = parse_goodreads_rss(rss_url)
        
        if error:
            return jsonify(success=False, error=error), 400
        
        if not books_data:
            return jsonify(success=False, error="No books found in RSS feed"), 400
        
        # Get or create "Imported" shelf
        imported_shelf = Shelf.query.filter_by(
            shelf_name="Imported",
            user_id=user_id
        ).first()
        
        if not imported_shelf:
            imported_shelf = Shelf(
                shelf_name="Imported",
                user_id=user_id
            )
            db.session.add(imported_shelf)
            db.session.commit()
        
        # Check premium status for book limit
        is_premium, _ = get_user_premium_status(user_id)
        
        # Get current total books count
        current_books_count = Book.query.join(Shelf).filter(
            Shelf.user_id == user_id
        ).count()
        
        books_imported = 0
        books_skipped = 0
        
        # Import books
        for book_data in books_data:
            # Check book limit for free users
            if not is_premium and (current_books_count + books_imported) >= 12:
                books_skipped += 1
                continue
            
            # Check if book already exists in user's library
            existing_book = Book.query.join(Shelf).filter(
                Shelf.user_id == user_id,
                Book.book_name == book_data['book_name']
            ).first()
            
            if existing_book:
                books_skipped += 1
                continue
            
            # Create new book
            new_book = Book(
                book_name=book_data['book_name'],
                shelf_id=imported_shelf.id,
                status=book_data['status'],
                total_pages=book_data['total_pages'],
                current_page=book_data['current_page'],
                intention=book_data.get('description', '')[:500]  # Limit description length
            )
            
            db.session.add(new_book)
            books_imported += 1
        
        # Commit all new books
        if books_imported > 0:
            db.session.commit()
        
        return jsonify(
            success=True,
            books_imported=books_imported,
            books_skipped=books_skipped,
            message=f"Successfully imported {books_imported} books"
        ), 200
    
    except Exception as e:
        print(f"Error in import_goodreads: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500




# ============================================
# STEP 1: Get User's Country from IP
# ============================================
def get_user_location():
    """
    Detect user's country from their IP address
    Returns: Country code (e.g., 'US', 'IN', 'GB', 'EU')
    """
    try:
        # Get user's real IP address
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            ip = request.headers.get('X-Real-IP')
        else:
            ip = request.remote_addr
        
        # For local development (127.0.0.1), get real public IP
        if ip == '127.0.0.1' or ip.startswith('192.168') or ip.startswith('10.'):
            print("Local IP detected, fetching public IP...")
            response = requests.get('https://api.ipify.org?format=json', timeout=3)
            ip = response.json()['ip']
        
        print(f"Detecting location for IP: {ip}")
        
        # Get country from IP using free API
        response = requests.get(
            f'http://ip-api.com/json/{ip}',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                country_code = data['countryCode']  # e.g., 'US', 'IN', 'DE'
                
                # Convert EU countries to 'EU'
                eu_countries = ['DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'IE', 
                               'PT', 'FI', 'SE', 'DK', 'PL', 'CZ', 'HU', 'RO', 'GR']
                
                if country_code in eu_countries:
                    country_code = 'EU'
                
                print(f"Location detected: {country_code}")
                return country_code
    
    except Exception as e:
        print(f"Error detecting location: {e}")
    
    # Default to US if detection fails
    print("Location detection failed, defaulting to US")
    return 'US'




# logout session
@app.route("/logout")
def logout():
    # Track session time before logging out
    if "user_id" in session and "login_time" in session:
        try:
            user = db.session.get(User, session["user_id"])
            login_time = datetime.fromisoformat(session["login_time"])
            session_duration_minutes = int((datetime.utcnow() - login_time).total_seconds() / 60)
            
            if user and session_duration_minutes > 0:
                user.add_session_time(session_duration_minutes)
                db.session.commit()
        except Exception as e:
            print(f"Error tracking session time: {e}")
    
    session.clear()  # 🔥 clears user_id, username, everything
    return redirect("/")  # go back to landing page

# API endpoint to track time in real-time
@app.route("/api/track-time", methods=["POST"])
@login_required
def track_time():
    """Update session time periodically while user is active"""
    try:
        if "user_id" not in session or "login_time" not in session:
            return jsonify(success=False, error="Not logged in"), 401
        
        user = db.session.get(User, session["user_id"])
        if not user:
            return jsonify(success=False, error="User not found"), 404
        
        login_time = datetime.fromisoformat(session["login_time"])
        session_duration_minutes = int((datetime.utcnow() - login_time).total_seconds() / 60)
        
        if session_duration_minutes > 0:
            # Reset login time to track incremental time
            session["login_time"] = datetime.utcnow().isoformat()
            user.add_session_time(session_duration_minutes)
            db.session.commit()
            
            # Return updated stats
            stats = user.get_time_stats()
            return jsonify(success=True, stats=stats)
        
        return jsonify(success=True)
    except Exception as e:
        print(f"Error in track_time: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route("/api/reading-statistics")
@login_required
def reading_statistics():
    """Get comprehensive reading statistics for the dashboard chart"""
    try:
        user_id = session["user_id"]
        
        # Get all shelves for this user
        shelves = Shelf.query.filter_by(user_id=user_id).all()
        
        # Collect all books from user's shelves
        all_books = []
        for shelf in shelves:
            all_books.extend(shelf.books)
        
        # Calculate statistics
        total_books = len(all_books)
        completed_books = 0
        active_books = 0
        unread_books = 0
        total_pages_read = 0
        total_pages_in_books = 0
        
        for book in all_books:
            # Check if book is completed (current_page == total_pages)
            if book.total_pages and book.current_page and book.current_page >= book.total_pages:
                completed_books += 1
            
            # Check if book is active (status is "active")
            if book.status == "active" or book.status == "reading":
                active_books += 1
            
            # Check if book is unread (current_page is 0 or null)
            if not book.current_page or book.current_page == 0:
                unread_books += 1
            
            # Add to total pages read
            if book.current_page:
                total_pages_read += book.current_page
            
            # Add to total pages in books
            if book.total_pages:
                total_pages_in_books += book.total_pages
        
        # Calculate average pages per book
        books_with_pages = [b for b in all_books if b.total_pages and b.total_pages > 0]
        average_pages_per_book = (
            sum(b.total_pages for b in books_with_pages) // len(books_with_pages) 
            if books_with_pages else 0
        )
        
        # Calculate completion rate
        completion_rate = (completed_books / total_books * 100) if total_books > 0 else 0
        
        # Get current reading streak from UserDailyProgress
        progress = db.session.get(UserDailyProgress, user_id)
        current_streak = progress.current_strike if progress else 0
        highest_streak = progress.highest_strike if progress else 0
        
        # Calculate average reading time per day
        user = db.session.get(User, user_id)
        average_daily_reading_minutes = (
            user.daily_time_spend if user else 0
        )
        
        return jsonify(
            success=True,
            statistics={
                'total_books': total_books,
                'completed_books': completed_books,
                'active_books': active_books,
                'unread_books': unread_books,
                'total_pages_read': total_pages_read,
                'total_pages_in_books': total_pages_in_books,
                'average_pages_per_book': average_pages_per_book,
                'completion_rate': round(completion_rate, 2),
                'current_streak': current_streak,
                'highest_streak': highest_streak,
                'average_daily_reading_minutes': average_daily_reading_minutes,
                'completed_percentage': round((completed_books / total_books * 100) if total_books > 0 else 0, 2),
                'active_percentage': round((active_books / total_books * 100) if total_books > 0 else 0, 2),
                'unread_percentage': round((unread_books / total_books * 100) if total_books > 0 else 0, 2),
            }
        )
    except Exception as e:
        print(f"Error in reading_statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500



@app.route('/profile')
def profile():
    if "user_id" not in session:
        return redirect("/signin")
    
    user_id = session["user_id"]
    user = db.session.get(User, user_id)
    
    if user is None:
        session.clear()
        return redirect("/signin")
    
    # Get premium status
    is_premium = user.is_premium
    days_left = 0
    if user.is_premium and user.premium_until:
        today = datetime.utcnow()
        if user.premium_until > today:
            days_left = (user.premium_until - today).days
    
    # Get user's referral code
    referral_code = ReferralCode.query.filter_by(user_id=user_id).first()
    referral_code_str = referral_code.referral_code if referral_code else None
    
    # Get referral stats
    referrals = Referral.query.filter_by(referrer_id=user_id).all()
    completed_referrals = len([r for r in referrals if r.status == 'completed'])
    
    # Generate shareable link
    referral_link = f"{request.host_url}signup?ref={referral_code_str}" if referral_code_str else None
    
    # Yearly leaderboard data
    yearly_leaderboard = User.query.order_by(User.yearly_time_spend.desc()).limit(10).all()
    leaderboard_data = []
    user_yearly_rank = None
    
    for idx, leader in enumerate(yearly_leaderboard, 1):
        is_leader_premium = leader.is_premium_user() if leader else False
        yearly_hours = leader.yearly_time_spend // 60
        yearly_minutes = leader.yearly_time_spend % 60
        
        leaderboard_data.append({
            'rank': idx,
            'name': leader.name,
            'yearly_hours': yearly_hours,
            'yearly_minutes': yearly_minutes,
            'is_current_user': leader.id == user_id,
            'is_premium': is_leader_premium
        })
        
        if leader.id == user_id:
            user_yearly_rank = idx
    
    # If current user not in top 10, calculate their rank
    if user_yearly_rank is None:
        all_users = User.query.order_by(User.yearly_time_spend.desc()).all()
        for idx, ranked_user in enumerate(all_users, 1):
            if ranked_user.id == user_id:
                user_yearly_rank = idx
                break
    
    yearly_hours = user.yearly_time_spend // 60 if user else 0
    yearly_minutes = user.yearly_time_spend % 60 if user else 0
    
    return render_template('profile.html',
                         user=user,
                         is_premium=is_premium,
                         days_left=days_left,
                         referral_code=referral_code_str,
                         referral_link=referral_link,
                         total_referrals=len(referrals),
                         completed_referrals=completed_referrals,
                         yearly_leaderboard=leaderboard_data,
                         user_yearly_rank=user_yearly_rank,
                         yearly_hours=yearly_hours,
                         yearly_minutes=yearly_minutes)








def validate_passwords(current_password, new_password, confirm_password, user):
    if not user.check_password(current_password):
        return "Current password is incorrect"
    if new_password != confirm_password:
        return "New passwords do not match"
    if not new_password or len(new_password) < 6:
        return "Password must be at least 6 characters long"
    return None

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    user = db.session.get(User, session["user_id"])
    if not user:
        return redirect("/signin")

    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    error = validate_passwords(current_password, new_password, confirm_password, user)
    if error:
        return render_template("profile.html", user=user, message=error)

    user.set_password(new_password)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template("profile.html", user=user, message="An error occurred. Please try again.")

    return render_template("profile.html", user=user, message="Password updated successfully")

def calculate_reading_stats(user_id):
    """Calculate reading statistics from existing book data"""
    # Get user to access email (since Shelf.user_id references User.email)
    user = db.session.get(User, user_id)
    if not user:
        return {
            'total_books': 0,
            'completed_count': 0,
            'completed_percentage': 0,
            'active_count': 0,
            'active_percentage': 0,
            'incomplete_count': 0,
            'incomplete_percentage': 0,
            'unread_count': 0
        }
    all_books = Book.query.join(Shelf).filter(Shelf.user_id == user.email).all()
    
    total_books = len(all_books)
    completed_books = [b for b in all_books if b.total_pages and b.current_page and b.current_page >= b.total_pages]
    active_books = [b for b in all_books if b.status == "active"]
    unread_books = [b for b in all_books if not b.current_page or b.current_page == 0]
    
    # Incomplete = books that are not completed and not active
    completed_ids = {b.id for b in completed_books}
    active_ids = {b.id for b in active_books}
    incomplete_books = [b for b in all_books if b.id not in completed_ids and b.id not in active_ids]
    
    return {
        'total_books': total_books,
        'completed_count': len(completed_books),
        'completed_percentage': round((len(completed_books) / total_books * 100) if total_books > 0 else 0, 1),
        'active_count': len(active_books),
        'active_percentage': round((len(active_books) / total_books * 100) if total_books > 0 else 0, 1),
        'incomplete_count': len(incomplete_books),
        'incomplete_percentage': round((len(incomplete_books) / total_books * 100) if total_books > 0 else 0, 1),
        'unread_count': len(unread_books)
    }



@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/signin")
    
    user_id = session["user_id"]
    user = db.session.get(User, user_id)
    
    if user is None:  # Safety check
        session.clear()
        return redirect("/signin")
    
    # Calculate days remaining
    is_premium = user.is_premium
    days_left = 0
    if user.is_premium and user.premium_until:
        today = datetime.utcnow()
        if user.premium_until > today:
            days_left = (user.premium_until - today).days


    
    # Get time stats
    time_stats = user.get_time_stats() if user else {}
    
    # Get leaderboard data - top users by daily reading time
    top_users = User.query.order_by(User.daily_time_spend.desc()).limit(6).all()
    leaderboard = []
    user_rank = None
    
    for idx, leader_user in enumerate(top_users, 1):
        # Check if leader user has active premium access
        is_leader_premium = leader_user.is_premium_user() if leader_user else False
        
        leaderboard.append({
            'rank': idx,
            'name': leader_user.name,
            'daily_hours': leader_user.daily_time_spend // 60,
            'daily_minutes': leader_user.daily_time_spend % 60,
            'is_current_user': leader_user.id == user_id,
            'is_premium': is_leader_premium
        })
        if leader_user.id == user_id:
            user_rank = idx
    
    # If current user is not in top 6, calculate their rank
    if user_rank is None and user:
        all_users = User.query.order_by(User.daily_time_spend.desc()).all()
        for idx, ranked_user in enumerate(all_users, 1):
            if ranked_user.id == user_id:
                user_rank = idx
                break
    
    # Update today's ranking for current user
    if user and user_rank:
        user.today_ranking = user_rank
        db.session.commit()
    # Show only shelves belonging to this user
    shelves = Shelf.query.filter_by(user_id=user_id).all()
    
    # Calculate reading statistics
    reading_stats = calculate_reading_stats(user_id) if user else {}
    
    error_message = None
    success_message = None
    
    if request.method == "POST":
        shelf_name = request.form.get("shelf_name")
        if shelf_name:
            # Check shelf limit for free users
            if not is_premium and len(shelves) >= 3:
                error_message = "Free users can create up to 3 shelves. Upgrade to Premium for unlimited shelves!"
            else:
                new_shelf = Shelf(shelf_name=shelf_name, user_id=user_id)
                db.session.add(new_shelf)
                db.session.commit()
                shelves = Shelf.query.filter_by(user_id=user_id).all()
                success_message = "Shelf created successfully!"
        return render_template("dashboard.html", 
                             shelves=shelves, 
                             is_premium=is_premium, 
                             days_left=days_left,
                             time_stats=time_stats,
                             leaderboard=leaderboard,
                             user_rank=user_rank,
                             reading_stats=reading_stats,
                             error=error_message,
                             success=success_message)
    
    return render_template("dashboard.html", 
                         shelves=shelves, 
                         is_premium=is_premium, 
                         days_left=days_left,
                         time_stats=time_stats,
                         leaderboard=leaderboard,
                         user_rank=user_rank,
                         reading_stats=reading_stats,
                         user=user)



@app.route("/active_reading", methods=["GET", "POST"])
@login_required
def active_reading():

    if "user_id" not in session:
        return redirect("/signin")

    user_id = session["user_id"]
    # In active_reading route, change:
    user_id = session.get('user_id')
    is_premium, days_left = get_user_premium_status(user_id) if user_id else (False, 0)

    if request.method == "POST":
        # Handle adding new book
            # Get current user and premium status
        book_name = request.form.get("book_name")
        if book_name:
            user = db.session.get(User, user_id)
            is_premium, _ = get_user_premium_status(user_id)
            # Count total books for this user
            total_books = Book.query.join(Shelf).filter(Shelf.user_id == user_id).count()
            
            # Check book limit for free users
            if not is_premium and total_books >= 12:
                # Redirect back with error
                shelves = Shelf.query.filter_by(user_id=user_id).all()
                active_books = []
                for shelf in shelves:
                    active_books.extend([book for book in shelf.books if book.status == "active"])
                
                # Calculate daily goals
                daily_goal_books = []
                today = date.today()
                for book in active_books:
                    current_page = book.current_page or 0
                    total_page = book.total_pages or 0
                    unread_page = max(total_page - current_page, 0)
                    if unread_page > 0:
                        target_date = book.target_date
                        days_left = (target_date - today).days if target_date else 1
                        days_left = max(days_left, 1)
                        daily_goal_pages = int(unread_page / days_left)
                        daily_goal_pages = max(daily_goal_pages, 1)
                        daily_goal_pages = min(daily_goal_pages, unread_page)
                        end_page = current_page + daily_goal_pages
                        if end_page > total_page:
                            end_page = total_page
                        daily_goal_books.append({
                            "id": book.id,
                            "title": book.book_name,
                            "start_page": current_page,
                            "end_page": end_page,
                            "pages_to_read": end_page - current_page
                        })
                
                progress = ensure_today_progress(user_id, len(daily_goal_books))
                
                return render_template("active_reading.html", 
                                     active_books=active_books,
                                     daily_goal_books=daily_goal_books,
                                     progress=progress,
                                     error="Free users can add up to 12 books. Upgrade to Premium for unlimited books!")
            
            try:
                shelf = Shelf.query.filter_by(user_id=user_id).first()
                if not shelf:
                    shelf = Shelf(shelf_name="Active Reading", user_id=user_id)
                    db.session.add(shelf)
                    db.session.commit()

                new_book = Book(book_name=book_name, shelf_id=shelf.id, status="active")
                db.session.add(new_book)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error adding book: {str(e)}")
                return redirect(url_for("active_reading"))
        
        return redirect(url_for("active_reading"))

    # Get active books for this user
    shelves = Shelf.query.filter_by(user_id=user_id).all()
    active_books = []
    for shelf in shelves:
        active_books.extend([book for book in shelf.books if book.status == "active"])

    # Calculate daily goals
    daily_goal_books = []
    today = date.today()

    daily_goal_books = []
    goal_names = []  # ← Initialize here
    today = date.today()    


    for book in active_books:
        current_page = book.current_page or 0
        total_page = book.total_pages or 0
        unread_page = max(total_page - current_page, 0)

        if unread_page > 0:
            target_date = book.target_date
            days_left = (target_date - today).days if target_date else 1
            days_left = max(days_left, 1)

            daily_goal_pages = int(unread_page / days_left)
            daily_goal_pages = max(daily_goal_pages, 1)
            daily_goal_pages = min(daily_goal_pages, unread_page)

            end_page = current_page + daily_goal_pages
            if end_page > total_page:
                end_page = total_page

            daily_goal_books.append({
                "id": book.id,
                "title": book.book_name,
                "start_page": current_page,
                "end_page": end_page,
                "pages_to_read": end_page - current_page
            })
            goal_names.append(book.book_name) 

    # Get or create daily progress
    progress = ensure_today_progress(user_id, len(daily_goal_books), goal_names)

    return render_template(
        "active_reading.html",
        active_books=active_books,
        daily_goal_books=daily_goal_books,
        is_premium=is_premium,
        days_left=days_left,
        progress=progress
    )


@app.route("/toggle-task", methods=["POST"])
@login_required
def toggle_task():
    try:
        user_id = session["user_id"]
        data = request.json
        index = int(data.get("index", -1))
        
        progress = db.session.get(UserDailyProgress, user_id)
        if not progress:
            return jsonify(success=False, error="No progress found"), 404
        
        if progress.toggle_task(index):
            db.session.commit()
            
            return jsonify(
                success=True,
                completed=progress.today_tasks[index],
                current_today_goals=progress.today_completed_count,
                total_goals=progress.today_goal_count,
                completion_percentage=int((progress.today_completed_count / progress.today_goal_count * 100) if progress.today_goal_count > 0 else 0),
                current_streak=progress.current_strike
            )
        
        return jsonify(success=False, error="Invalid index"), 400
        
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
# stike counting 



def ensure_today_progress(user_id, goal_count, goal_names=None):
    """Ensure user has progress record for today"""
    progress = db.session.get(UserDailyProgress, user_id)
    
    if goal_names is None:
        goal_names = []
    
    if not progress:
        progress = UserDailyProgress(
            user_id=user_id,
            today_date=date.today(),
            today_goal_count=goal_count,
            today_completed_count=0,
            today_tasks=[False] * goal_count,
            today_goal_names=goal_names,
            last_evaluated_date=date.today()
        )
        db.session.add(progress)
        db.session.commit()
        return progress
    
    # New day - evaluate and reset
    if progress.today_date != date.today():
        progress.reset_for_new_day(goal_count, goal_names)
        db.session.commit()
    elif progress.today_goal_count != goal_count:
        # Goals changed during day
        old_tasks = progress.today_tasks or []
        progress.today_goal_count = goal_count
        progress.today_goal_names = goal_names
        
        new_tasks = [False] * goal_count
        for i in range(min(len(old_tasks), goal_count)):
            new_tasks[i] = old_tasks[i]
        
        progress.today_tasks = new_tasks
        flag_modified(progress, "today_tasks")
        progress.today_completed_count = sum(1 for task in new_tasks if task)
        db.session.commit()
    
    return progress




def evaluate_all_users_daily():
    """Evaluate all users' streaks at midnight"""
    with app.app_context():
        try:
            all_progress = UserDailyProgress.query.all()
            for progress in all_progress:
                if progress.today_date != date.today():
                    progress.evaluate_yesterday_strike()
            db.session.commit()
            print(f"✅ Evaluated {len(all_progress)} users")
        except Exception as e:
            print(f"❌ Evaluation error: {e}")
            db.session.rollback()

# Start scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=evaluate_all_users_daily,
    trigger=CronTrigger(hour=0, minute=1),  # 12:01 AM
    id='daily_evaluation',
    replace_existing=True
)
scheduler.start()




def evaluate_strike(user_id):
    progress = db.session.get(UserDailyProgress, user_id)

    # Only evaluate once per day
    if progress.last_updated_date != date.today():
        if progress.today_goal_count == progress.today_completed_count:
            # ✅ All tasks completed
            progress.current_strike += 1

            if progress.current_strike > progress.highest_strike:
                progress.highest_strike = progress.current_strike
        else:
            # ❌ Any task missed
            progress.current_strike = 0

        # Reset today data for new day
        progress.today_goal_count = 0
        progress.today_completed_count = 0
        progress.today_tasks = []
        progress.last_updated_date = date.today()

        db.session.commit()







@app.route("/rename_shelf", methods=["POST"])
@login_required
def rename_shelf():
    try:
        data = request.get_json()
        if not data:
            return jsonify(success=False, error="No JSON data received"), 400
            
        shelf_id = data.get("id")
        new_name = data.get("name")
        
        if not shelf_id or not new_name:
            return jsonify(success=False, error="Missing id or name"), 400
        
        print(f"Rename shelf - ID: {shelf_id}, Session User: {session.get('user_id')}")
        shelf = db.session.get(Shelf, shelf_id)
        
        if not shelf:
            print(f"Shelf not found: {shelf_id}")
            return jsonify(success=False, error="Shelf not found"), 404
        
        print(f"Shelf user_id: {shelf.user_id}, Session user_id: {session.get('user_id')}")
        
        # Verify ownership - convert to string to handle type mismatch
        if str(shelf.user_id) != str(session.get('user_id')):
            return jsonify(success=False, error="Not authorized"), 403
        
        shelf.shelf_name = new_name
        db.session.commit()
        return jsonify(success=True)
        
    except Exception as e:
        print(f"Error renaming shelf: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route("/rename_book", methods=["POST"])
@login_required
def rename_book():
    try:
        data = request.get_json()
        if not data:
            return jsonify(success=False, error="No JSON data received"), 400
            
        book_id = data.get("id")
        new_name = data.get("name")
        
        if not book_id or not new_name:
            return jsonify(success=False, error="Missing id or name"), 400
        
        book = db.session.get(Book, book_id)
        
        # Verify ownership
        if not book or book.shelf.user_id != session.get('user_id'):
            return jsonify(success=False, error="Not authorized"), 403
        
        book.book_name = new_name
        db.session.commit()
        return jsonify(success=True)
        
    except Exception as e:
        print(f"Error renaming book: {e}")
        return jsonify(success=False, error=str(e)), 500



# ============================================
# REPLACE THE BOOK_PAGE ROUTE IN app.py
# ============================================
@app.route("/book/<int:book_id>", methods=["GET", "POST"])
def book_page(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Get current user and check premium status
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None
    is_premium, days_left = get_user_premium_status(user_id) if user_id else (False, 0)
    
    print(f"\n{'='*60}")
    print(f"📖 BOOK PAGE DEBUG")
    print(f"{'='*60}")
    print(f"User ID: {user_id}")
    print(f"User: {user.name if user else 'None'}")
    print(f"Is Premium: {is_premium}")
    print(f"Days Left: {days_left}")
    print(f"{'='*60}\n")
    
    if request.method == "POST":
        print(f"📝 POST Request received")
        
        # Book name
        book.book_name = request.form.get("title") or book.book_name
        
        # Integer fields
        total_pages = request.form.get("total_pages")
        current_page = request.form.get("current_page")
        book.total_pages = int(total_pages) if total_pages else None
        book.current_page = int(current_page) if current_page else None
        
        # Text fields
        book.intention = request.form.get("intention") or book.intention
        book.external_link = request.form.get("external_link") or book.external_link
        
        # Date fields
        start_date_str = request.form.get("start_date")
        target_date_str = request.form.get("target_date")
        if start_date_str:
            book.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if target_date_str:
            book.target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        
        # ============================================
        # FILE UPLOAD - STRICT PREMIUM CHECK
        # ============================================
        file = request.files.get("file")
        
        print(f"File in request: {file is not None}")
        if file:
            print(f"File filename: {file.filename}")
            print(f"File size: {len(file.read()) if file.filename else 'No file'}")
            file.seek(0)  # Reset file pointer
        
        # Check if file was actually provided (not just empty input)
        if file and file.filename and file.filename.strip():
            print(f"✋ File upload attempt detected!")
            print(f"Premium status: {is_premium}")
            
            # CRITICAL: Block file upload for non-premium users
            if not is_premium:
                print(f"❌ FILE UPLOAD BLOCKED - User is not premium!")
                db.session.commit()  # Save other changes
                return render_template(
                    "book.html", 
                    book=book,
                    is_premium=is_premium,
                    days_left=days_left,
                    error="❌ File upload is a premium feature. Please upgrade to Premium to upload files!"
                )
            
            # User is premium - proceed with file upload
            print(f"✅ User is premium, allowing file upload")
            
            if allowed_file(file.filename):
                import time
                filename = secure_filename(file.filename)
                filename = f"{int(time.time())}_{filename}"
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                
                file.save(filepath)
                book.file_path = filename
                print(f"✅ File saved: {filename}")
            else:
                print(f"❌ File type not allowed: {file.filename}")
                db.session.commit()
                return render_template(
                    "book.html", 
                    book=book,
                    is_premium=is_premium,
                    days_left=days_left,
                    error="❌ Invalid file type. Allowed: PDF, DOC, DOCX, TXT, EPUB"
                )
        else:
            print(f"ℹ️  No file provided or file is empty")
        
        # Commit all changes
        db.session.commit()
        print(f"✅ All changes saved!")
        return redirect(url_for("book_page", book_id=book.id))
    
    # GET request - render page
    print(f"📄 GET Request - Rendering book page")
    return render_template(
        "book.html", 
        book=book,
        is_premium=is_premium,
        days_left=days_left
    )






@app.route("/start_reading/<int:book_id>", methods=["POST"])
def start_reading(book_id):
    if "user_id" not in session:
        return redirect("/signin")
    
    book = Book.query.get_or_404(book_id)
    book.status = "active"
    db.session.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete_book", methods=["POST"])
@login_required
def delete_book():
    print("=" * 50)
    print("🔥 DELETE_BOOK DEBUG START")
    print(f"Session user_id: {session.get('user_id')}")
    
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        
        book_id = data.get('id')
        print(f"Book ID to delete: {book_id}")
        
        # Get current user
        current_user_id = session['user_id']
        current_user = db.session.get(User, current_user_id)
        print(f"Current user: {current_user.name} ({current_user.email})")
        
        # Find the book
        book = db.session.get(Book, book_id)
        if not book:
            print(f"❌ Book {book_id} not found in database")
            return jsonify(success=False, error="Book not found"), 404
        
        print(f"✅ Book found: '{book.book_name}' (ID: {book.id})")
        print(f"Book shelf_id: {book.shelf_id}")
        print(f"Book status: {book.status}")
        
        # Find the shelf
        shelf = db.session.get(Shelf, book.shelf_id)
        if not shelf:
            print(f"❌ Shelf {book.shelf_id} not found!")
            return jsonify(success=False, error="Shelf not found"), 404
        
        print(f"✅ Shelf found: '{shelf.shelf_name}' (ID: {shelf.id})")
        print(f"Shelf user_id: {shelf.user_id}")
        
        # Get shelf owner details
        shelf_owner = db.session.get(User, shelf.user_id)
        if shelf_owner:
            print(f"Shelf owner: {shelf_owner.name} ({shelf_owner.email})")
        
        # Check ownership
        if str(shelf.user_id) != str(current_user_id):
            print("❌ PERMISSION DENIED!")
            print(f"Current user ID: {current_user_id}")
            print(f"Shelf owner ID: {shelf.user_id}")
            print(f"Match: {str(shelf.user_id) == str(current_user_id)}")
            return jsonify(success=False, error="Permission denied"), 403
        
        print("✅ Permission granted! User owns this book")
        
        # Delete the book
        db.session.delete(book)
        db.session.commit()
        print(f"✅ Book '{book.book_name}' deleted successfully")
        print("=" * 50)
        
        return jsonify(success=True)
        
    except Exception as e:
        print(f"💥 Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 50)
        return jsonify(success=False, error=str(e)), 500


@app.route("/delete_shelf", methods=["POST"])
@login_required
def delete_shelf():
    try:
        data = request.json
        shelf_id = data.get("id")
        
        if not shelf_id:
            return jsonify(success=False, error="Missing shelf id"), 400
        
        print(f"Delete shelf - ID: {shelf_id}, Session User: {session.get('user_id')}")
        shelf = db.session.get(Shelf, shelf_id)
        
        if not shelf:
            print(f"Shelf not found: {shelf_id}")
            return jsonify(success=False, error="Shelf not found"), 404
        
        print(f"Shelf user_id: {shelf.user_id}, Session user_id: {session.get('user_id')}")
        
        # Verify ownership - convert to string to handle type mismatch
        if str(shelf.user_id) != str(session.get("user_id")):
            return jsonify(success=False, error="Not authorized"), 403
        
        db.session.delete(shelf)  # cascade deletes all books
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error deleting shelf: {e}")
        return jsonify(success=False, error=str(e)), 500







def get_yearly_leaderboard(limit=10):
    """
    Get top users by yearly reading time - calculated on-the-fly
    No stored ranking data - always fresh!
    """
    from datetime import datetime
    
    # Get current year
    current_year = datetime.now().year
    
    # Get all users ordered by yearly_time_spent (descending)
    users = User.query.order_by(User.yearly_time_spent.desc()).limit(limit).all()
    
    leaderboard = []
    for rank, user in enumerate(users, start=1):
        hours = user.yearly_time_spent // 60
        minutes = user.yearly_time_spent % 60
        
        leaderboard.append({
            'rank': rank,
            'name': user.name,
            'yearly_hours': hours,
            'yearly_minutes': minutes,
            'total_minutes': user.yearly_time_spent,
            'is_current_user': user.id == session.get('user_id'),
            'is_premium': user.is_premium
        })
    
    return leaderboard

def get_user_yearly_rank(user_id):
    """
    Get specific user's rank in yearly leaderboard
    Calculated dynamically - no stored data
    """
    user = db.session.get(User, user_id)
    if not user:
        return None
    
    # Count how many users have more yearly time
    higher_ranked_count = User.query.filter(
        User.yearly_time_spent > user.yearly_time_spent
    ).count()
    
    # Rank is count + 1
    return higher_ranked_count + 1


    

@app.route("/shelf/<int:shelf_id>", methods=["GET", "POST"])
def shelf_page(shelf_id):
    shelf = Shelf.query.get_or_404(shelf_id)

        # Get current user and premium status
    user_id = session.get('user_id')
    is_premium, days_left = get_user_premium_status(user_id) if user_id else (False, 0)
        
    if request.method == "POST":
        # get the book name from the form
        book_name = request.form.get("book_name")
        if book_name:
            user_id = shelf.user_id
            is_premium, _ = get_user_premium_status(user_id)
            
            # Count total books for this user
            total_books = Book.query.join(Shelf).filter(Shelf.user_id == user_id).count()
            
            # Check book limit for free users
            if not is_premium and total_books >= 12:
                books = Book.query.filter_by(shelf_id=shelf.id, status="on_shelf").all()
                return render_template("shelf.html", 
                                     shelf=shelf, 
                                     books=books,
                                     error="Free users can add up to 12 books. Upgrade to Premium for unlimited books!")
            
            new_book = Book(book_name=book_name, shelf_id=shelf.id)
            db.session.add(new_book)
            db.session.commit()  # 🔥 THIS IS THE KEY FIX
        return redirect(url_for("shelf_page", shelf_id=shelf.id))
    
    # fetch all books for this shelf with status on_shelf
    books = Book.query.filter_by(shelf_id=shelf.id, status="on_shelf").all()
    return render_template("shelf.html", shelf=shelf, books=books)

@app.route("/shelf/<int:shelf_id>/collection_books")
def collection_books(shelf_id):
    # Get current user and premium status
    user_id = session.get('user_id')
    is_premium, days_left = get_user_premium_status(user_id) if user_id else (False, 0)
    books = Book.query.filter_by(shelf_id=shelf_id).all()
    shelf = Shelf.query.get_or_404(shelf_id)
    return render_template("collection_books.html", books=books, shelf=shelf, is_premium=is_premium, days_left=days_left)

@app.route("/view_active_reading")

def view_active_reading():
        # Get current user and premium status
    user_id = session.get('user_id')
    is_premium, days_left = get_user_premium_status(user_id) if user_id else (False, 0)

    if "user_id" not in session:
        return redirect("/signin")
    
    user_id = session["user_id"]
    
    # get all active books for this user
    active_books = (
        Book.query
        .join(Shelf)
        .filter(
            Shelf.user_id == user_id,
            Book.status == "active"
        )
        .all()
    )
    
    return render_template("view_active_reading.html", books=active_books, is_premium=is_premium, days_left=days_left)



@app.route("/stop_reading/<int:book_id>", methods=["POST"])
def stop_reading(book_id):
    if "user_id" not in session:
        return jsonify(success=False), 401
    
    book = Book.query.get_or_404(book_id)
    book.status = "on_shelf"
    db.session.commit()
    return jsonify(success=True)

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    # rename the function
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



@app.route('/update_reading_goal', methods=['POST'])
def update_reading_goal():
    if 'user_id' not in session:
        return redirect('/signin')
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    new_goal = request.form.get('yearly_goal', type=int)
    
    if new_goal and 1 <= new_goal <= 365:
        user.yearly_reading_goal = new_goal
        db.session.commit()
    
    return redirect('/profile')












with app.app_context():
    for rule in app.url_map.iter_rules():
        print(f"{' '.join(rule.methods):20} {rule.rule:40} -> {rule.endpoint}")
print("=================================\n")





#terms and condition route
@app.route("/terms")
def terms():
    return render_template("terms.html")

# In app.py, replace the existing privacy route with:

# Privacy Policy - Public (No Login Required)
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")






# Add this to app.py
@app.context_processor
def utility_processor():
    def is_premium():
        if 'user_id' in session:
            user = db.session.get(User, session['user_id'])
            return user.is_premium if user else False
        return False
    
    def get_premium_days_left():
        if 'user_id' in session:
            user = db.session.get(User, session['user_id'])
            return user.days_left_in_premium() if user else 0
        return 0
    
    return dict(is_premium=is_premium, get_premium_days_left=get_premium_days_left)


@app.route('/upgrade', methods=['POST'])
def upgrade_to_premium():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, user_id)
    
    # For testing, you can create a simple upgrade
    if app.debug:
        user.is_premium = True
        user.premium_since = datetime.utcnow()
        user.premium_until = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
        db.session.commit()
        flash('Premium activated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    # Real payment with Stripe
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': 'Book Chelf Premium',
                    },
                    'unit_amount': 29900,  # ₹299
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', _external=True),
            cancel_url=url_for('pricing', _external=True),
            metadata={
                'user_id': user.id
            }
        )
        return redirect(checkout_session.url)
    except Exception as e:
        flash('Payment error: ' + str(e), 'error')
        return redirect(url_for('pricing'))

@app.route('/payment/success')
def payment_success():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    # Mark as premium
    user.is_premium = True
    user.premium_since = datetime.utcnow()
    user.premium_until = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
    db.session.commit()
    
    flash('🎉 Welcome to Book Chelf Premium!', 'success')
    return redirect(url_for('dashboard'))



@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400
    
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        checkout_session = event['data']['object']
        
        try:
            # Update user to premium
            user_id = int(checkout_session['metadata']['user_id'])
            user = db.session.get(User, user_id)
            
            if user:
                user.is_premium = True
                user.premium_since = datetime.utcnow()
                user.premium_until = datetime.utcnow() + timedelta(days=365)
                db.session.commit()
        except Exception as e:
            print(f"Error processing Stripe webhook: {str(e)}")
    
    return jsonify({'status': 'success'})








@app.route('/upgrade/manual', methods=['POST'])
def manual_upgrade_request():
    """Handle manual upgrade requests"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    
    # In reality, you'd save payment details and process manually
    # For now, we'll just redirect to instructions
    return render_template('manual_payment.html', user=user)





# Pricing configuration
PRICING = {
    'IN': {
        'currency': 'INR',
        'amount': 3500,  # ₹35 in paise
        'display': '₹35',
        'days': 30
    },
    'US': {
        'currency': 'USD',
        'amount': 199,  # $1.99 in cents
        'display': '$1.99',
        'days': 30
    },
    'GB': {
        'currency': 'GBP',
        'amount': 159,  # £1.59 in pence
        'display': '£1.59',
        'days': 30
    },
    'DEFAULT': {
        'currency': 'USD',
        'amount': 199,
        'display': '$1.99',
        'days': 30
    }
}


def get_user_ip():
    """Get user's IP address"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    
    # For localhost
    if ip == '127.0.0.1' or ip == 'localhost':
        return None
    
    return ip


def get_country_from_ip(ip_address):
    """Get country from IP using free API - no pip install needed"""
    if not ip_address:
        return None
    
    try:
        # Using ip-api.com (free, no key needed)
        url = f'http://ip-api.com/json/{ip_address}?fields=status,countryCode'
        
        with urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            
            if data.get('status') == 'success':
                return data.get('countryCode')  # Returns 'IN', 'US', 'GB', etc.
        
        return None
        
    except (URLError, Exception) as e:
        print(f"Error detecting country: {e}")
        return None


def get_pricing_for_country(country_code):
    """Get pricing based on country code"""
    if country_code in PRICING:
        return PRICING[country_code]
    return PRICING['DEFAULT']


# Route to get pricing
@app.route('/get-pricing', methods=['POST'])
def get_pricing():
    """API endpoint to get pricing based on location"""
    try:
        data = request.json
        country = data.get('country')  # From frontend
        
        # If frontend didn't send country, try IP detection
        if not country or country == 'DEFAULT':
            ip = get_user_ip()
            country = get_country_from_ip(ip)
        
        # Get pricing
        pricing = get_pricing_for_country(country)
        
        return jsonify(pricing)
        
    except Exception as e:
        print(f"Error in get_pricing: {e}")
        return jsonify(PRICING['DEFAULT'])


# Updated pricing page
@app.route("/pricing")
@login_required
def pricing():
    user = db.session.get(User, session["user_id"])
    is_premium, days_left = get_user_premium_status(session["user_id"])

    free_features = [
        "Up to 10 books",
        "Up to 3 shelves",
        "Basic reading tracker",
        "Daily goals",
        "File uploads"
    ]

    premium_features = [
        "Unlimited books & shelves",
        "Advanced analytics",
        "PDF annotation",
        "Data export",
        "Custom themes",
        "Priority support"
    ]

    # Try to detect country for initial display
    ip = get_user_ip()
    country = get_country_from_ip(ip)
    initial_pricing = get_pricing_for_country(country)

    return render_template(
        "pricing.html", 
        user=user,
        free_features=free_features,
        premium_features=premium_features,
        pricing=initial_pricing,
        is_premium=is_premium,
        days_left=days_left
    )


# Updated Razorpay order creation
@app.route('/create-razorpay-order', methods=['POST'])
@login_required
def create_razorpay_order():
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return jsonify(success=False, error="User not found"), 401
        
        # Get country from request
        data = request.json or {}
        country = data.get('country')
        
        # Fallback to IP detection
        if not country:
            ip = get_user_ip()
            country = get_country_from_ip(ip)
        
        # Get pricing
        user_pricing = get_pricing_for_country(country)
        
        # Only use Razorpay for India
        if user_pricing['currency'] != 'INR':
            return jsonify(
                success=False, 
                error="Razorpay only for Indian users"
            ), 400
        
        razorpay_key = os.getenv("RAZORPAY_KEY_ID")
        razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")
        
        if not razorpay_key or not razorpay_secret:
            return jsonify(success=False, error="Payment not configured"), 500
        
        razorpay_client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
        
        order_data = {
            'amount': user_pricing['amount'],
            'currency': user_pricing['currency'],
            'receipt': f'premium_{user.id}_{int(datetime.utcnow().timestamp())}',
            'notes': {
                'user_id': user.id,
                'email': user.email,
                'days': user_pricing['days']
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'key': razorpay_key,
            'days': user_pricing['days']
        })
        
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return jsonify(success=False, error=str(e)), 500


# Updated payment verification
@app.route('/verify-razorpay-payment', methods=['POST'])
@login_required
def verify_razorpay_payment():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify(success=False, error="User not found"), 401
    
    try:
        data = request.json
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        days = data.get('days', 30)  # Get days from payment
        
        # Verify signature
        message = f'{razorpay_order_id}|{razorpay_payment_id}'
        secret = os.getenv("RAZORPAY_KEY_SECRET", "")
        
        generated_signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature == razorpay_signature:
            # Activate premium for correct duration
            user.is_premium = True
            user.premium_since = datetime.utcnow()
            user.premium_until = datetime.utcnow() + timedelta(days=int(days))
            
            db.session.commit()
            
            return jsonify(
                success=True, 
                message=f"Premium activated for {days} days!",
                days=days
            )
        else:
            return jsonify(success=False, error="Verification failed"), 400
            
    except Exception as e:
        print(f"Error verifying payment: {e}")
        return jsonify(success=False, error=str(e)), 400











# Add these two routes to app.py (near other book management routes)

@app.route('/get-user-shelves', methods=['GET'])
@login_required
def get_user_shelves():
    """
    Get all shelves for the current user
    Returns shelf info including book count
    """
    try:
        user_id = session.get('user_id')
        print(f"🔍 Getting shelves for user_id: {user_id}")
        
        # Get user object to access both ID and email
        user = db.session.get(User, user_id)
        if not user:
            print(f"❌ User not found: {user_id}")
            return jsonify(success=False, error="User not found"), 404
        
        print(f"👤 User: {user.name}, Email: {user.email}, ID: {user.id}")
        
        # Query shelves - try both email (string) and integer ID
        # Some shelves might be stored with email, others with integer ID
        shelves = Shelf.query.filter(
            (Shelf.user_id == user.email) | 
            (Shelf.user_id == str(user.id))
        ).all()
        
        print(f"📚 Found {len(shelves)} shelves")
        
        shelves_data = []
        for shelf in shelves:
            # Count books in this shelf
            book_count = Book.query.filter_by(shelf_id=shelf.id).count()
            print(f"  📖 Shelf '{shelf.shelf_name}' (ID: {shelf.id}): {book_count} books, user_id stored as: {shelf.user_id}")
            
            shelves_data.append({
                'id': shelf.id,
                'shelf_name': shelf.shelf_name,
                'book_count': book_count
            })
        
        print(f"✅ Returning {len(shelves_data)} shelves")
        return jsonify(
            success=True,
            shelves=shelves_data
        ), 200
    
    except Exception as e:
        print(f"🔴 Error in get_user_shelves: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/move-book-to-shelf', methods=['POST'])
@login_required
def move_book_to_shelf():
    """
    Move a book from one shelf to another
    """
    try:
        user_id = session.get('user_id')
        print(f"🔍 Moving book for user_id: {user_id}")
        
        data = request.get_json()
        print(f"📦 Request data: {data}")
        
        book_id = data.get('book_id')
        new_shelf_id = data.get('new_shelf_id')
        
        if not book_id or not new_shelf_id:
            print(f"❌ Missing parameters - book_id: {book_id}, new_shelf_id: {new_shelf_id}")
            return jsonify(success=False, error="Missing book_id or new_shelf_id"), 400
        
        # Get the book
        book = db.session.get(Book, book_id)
        if not book:
            print(f"❌ Book not found: {book_id}")
            return jsonify(success=False, error="Book not found"), 404
        
        print(f"📖 Book found: {book.book_name}, current shelf_id: {book.shelf_id}")
        
        # Get the current shelf (to verify ownership)
        current_shelf = db.session.get(Shelf, book.shelf_id)
        if not current_shelf:
            print(f"❌ Current shelf not found: {book.shelf_id}")
            return jsonify(success=False, error="Current shelf not found"), 404
        
        print(f"📍 Current shelf: {current_shelf.shelf_name}, user_id: {current_shelf.user_id}")
        
        # Get user to verify ownership
        user = db.session.get(User, user_id)
        if not user:
            print(f"❌ User not found: {user_id}")
            return jsonify(success=False, error="User not found"), 404
        
        # Verify user owns the current shelf (compare with both email and ID)
        if str(current_shelf.user_id) != str(user.email) and str(current_shelf.user_id) != str(user.id):
            print(f"❌ Authorization failed! Shelf user_id: {current_shelf.user_id}, User email: {user.email}, User ID: {user.id}")
            return jsonify(success=False, error="Not authorized to move this book"), 403
        
        print(f"✅ Authorization passed!")
        
        # Get the new shelf
        new_shelf = db.session.get(Shelf, new_shelf_id)
        if not new_shelf:
            print(f"❌ New shelf not found: {new_shelf_id}")
            return jsonify(success=False, error="Target shelf not found"), 404
        
        print(f"🎯 New shelf: {new_shelf.shelf_name}, user_id: {new_shelf.user_id}")
        
        # Verify user owns the new shelf
        if str(new_shelf.user_id) != str(user.email) and str(new_shelf.user_id) != str(user.id):
            print(f"❌ Authorization failed for new shelf! New shelf user_id: {new_shelf.user_id}, User email: {user.email}, User ID: {user.id}")
            return jsonify(success=False, error="Not authorized to move to this shelf"), 403
        
        # Move the book
        book.shelf_id = new_shelf_id
        db.session.commit()
        print(f"✅ Book moved successfully from shelf {current_shelf.id} to shelf {new_shelf_id}")
        
        return jsonify(
            success=True,
            message=f"Book moved to {new_shelf.shelf_name}"
        ), 200
    
    except Exception as e:
        print(f"🔴 Error in move_book_to_shelf: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500




@app.route('/mark-book-completed', methods=['POST'])
@login_required
def mark_book_completed():
    """
    Mark a book as completed
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        book_id = data.get('book_id')
        
        if not book_id:
            return jsonify(success=False, error="Missing book_id"), 400
        
        # Get the book
        book = db.session.get(Book, book_id)
        if not book:
            return jsonify(success=False, error="Book not found"), 404
        
        # Verify ownership
        shelf = db.session.get(Shelf, book.shelf_id)
        if not shelf or (str(shelf.user_id) != str(user_id) and str(shelf.user_id) != str(db.session.get(User, user_id).email)):
            return jsonify(success=False, error="Not authorized"), 403
        
        # Mark as completed
        book.status = "completed"
        book.current_page = book.total_pages
        db.session.commit()
        
        return jsonify(
            success=True,
            message="Book marked as completed"
        ), 200
    
    except Exception as e:
        print(f"Error in mark_book_completed: {e}")
        return jsonify(success=False, error=str(e)), 500




import secrets
import string

@app.route('/referral')
@login_required
def referral():
    """Show referral page with user's referral code and stats"""
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    # Get or create referral code
    referral_code_obj = ReferralCode.query.filter_by(user_id=user_id).first()
    
    if not referral_code_obj:
        # Generate unique referral code
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        referral_code_obj = ReferralCode(user_id=user_id, referral_code=code)
        db.session.add(referral_code_obj)
        db.session.commit()
    
    # Get referral stats
    total_referrals = Referral.query.filter_by(referrer_id=user_id, status='completed').count()
    pending_referrals = Referral.query.filter_by(referrer_id=user_id, status='pending').count()
    
    # Calculate rewards
    referrer_rewards = Referral.query.filter_by(
        referrer_id=user_id, 
        status='completed',
        referrer_reward_given=True
    ).count()
    
    referral_url = f"https://bookexchelf.com/signup?ref={referral_code_obj.referral_code}"
    
    return render_template('referral.html', 
                         user=user,
                         referral_code=referral_code_obj.referral_code,
                         referral_url=referral_url,
                         total_referrals=total_referrals,
                         pending_referrals=pending_referrals,
                         referrer_rewards=referrer_rewards)



@app.route('/api/check-referral-code', methods=['POST'])
def check_referral_code():
    """API endpoint to validate referral code"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify(success=False, error='Referral code required')
        
        referral_code_obj = ReferralCode.query.filter_by(referral_code=code).first()
        
        if not referral_code_obj:
            return jsonify(success=False, error='Invalid referral code')
        
        referrer = db.session.get(User, referral_code_obj.user_id)
        
        return jsonify(
            success=True,
            referrer_name=referrer.name,
            message=f"You'll both get 30 days premium when you sign up!"
        )
    
    except Exception as e:
        return jsonify(success=False, error=str(e))


@app.route('/referral-stats')
@login_required
def referral_stats():
    """Get referral statistics (JSON)"""
    user_id = session['user_id']
    
    referrals = Referral.query.filter_by(referrer_id=user_id).all()
    
    stats = {
        'total': len(referrals),
        'completed': len([r for r in referrals if r.status == 'completed']),
        'pending': len([r for r in referrals if r.status == 'pending']),
        'rewards_earned': len([r for r in referrals if r.referrer_reward_given])
    }
    
    return jsonify(success=True, stats=stats)



@app.route('/test-email', methods=['GET'])
def test_email():
    """Test email sending"""
    try:
        msg = Message(
            subject='Test Email - BookEx Chelf',
            recipients=['bookexchelf@gmail.com'],
            body='This is a test email from BookEx Chelf'
        )
        mail.send(msg)
        return jsonify(success=True, message='Test email sent successfully!')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500







#---------------------------------------------------------------------
#
#monthly report generation route
#----------------------------------------------------------------------

# Add these routes to app.py

@app.route('/monthly-report')
@login_required
def monthly_report():
    """Show comprehensive monthly reading report"""
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return redirect('/signin')
    
    # Calculate days since signup
    days_since_signup = (datetime.utcnow() - user.created_at).days
    
    # Check if premium is expiring soon (within 7 days)
    is_premium = user.is_premium
    days_left = 0
    show_report = False
    
    if user.is_premium and user.premium_until:
        days_left = (user.premium_until - datetime.utcnow()).days
        # Show report when premium is about to expire (7 days before)
        if 0 <= days_left <= 7:
            show_report = True
    
    # Also show if it's been exactly 30 days since signup
    if days_since_signup >= 28 and days_since_signup <= 32:
        show_report = True
    
    # Calculate comprehensive statistics
    report_data = generate_monthly_report(user_id, user)
    
    return render_template(
        'monthly_report.html',
        user=user,
        report=report_data,
        is_premium=is_premium,
        days_left=days_left,
        days_since_signup=days_since_signup,
        show_report=show_report
    )


def generate_monthly_report(user_id, user):
    """Generate comprehensive monthly reading report"""
    
    # Get all user's shelves and books
    shelves = Shelf.query.filter_by(user_id=user_id).all()
    all_books = []
    for shelf in shelves:
        all_books.extend(shelf.books)
    
    # Calculate book statistics
    total_books = len(all_books)
    completed_books = [b for b in all_books if b.total_pages and b.current_page and b.current_page >= b.total_pages]
    active_books = [b for b in all_books if b.status == "active"]
    
    # Calculate pages read
    total_pages_read = sum(book.current_page or 0 for book in all_books)
    
    # Calculate reading time statistics
    time_stats = user.get_time_stats()
    total_reading_minutes = user.total_time_spend
    total_reading_hours = total_reading_minutes // 60
    total_reading_minutes_remainder = total_reading_minutes % 60
    
    # Get daily progress data
    progress = db.session.get(UserDailyProgress, user_id)
    current_streak = progress.current_strike if progress else 0
    highest_streak = progress.highest_strike if progress else 0
    total_goals_completed = progress.total_goals_completed if progress else 0
    total_goals_attempted = progress.total_goals_attempted if progress else 0
    
    # Calculate completion rate
    completion_rate = 0
    if total_goals_attempted > 0:
        completion_rate = round((total_goals_completed / total_goals_attempted) * 100, 1)
    
    # Calculate average daily reading time (in minutes)
    days_active = (datetime.utcnow() - user.created_at).days
    if days_active == 0:
        days_active = 1
    avg_daily_minutes = total_reading_minutes // days_active
    
    # Calculate reading speed (pages per hour)
    reading_speed = 0
    if total_reading_hours > 0:
        reading_speed = round(total_pages_read / total_reading_hours, 1)
    
    # Get leaderboard ranking
    all_users = User.query.order_by(User.yearly_time_spend.desc()).all()
    user_rank = 0
    for idx, ranked_user in enumerate(all_users, 1):
        if ranked_user.id == user_id:
            user_rank = idx
            break
    
    total_users = User.query.count()
    percentile = 0
    if total_users > 0:
        percentile = round(((total_users - user_rank) / total_users) * 100, 1)
    
    # Calculate improvement metrics (compare first week vs last week)
    first_week_pages = 0
    last_week_pages = 0
    
    # Books added in last 30 days
    recent_books = [b for b in all_books if b.today_date and (date.today() - b.today_date).days <= 30]
    
    # Calculate habits formed
    habits_formed = []
    
    if current_streak >= 7:
        habits_formed.append({
            'icon': '🔥',
            'title': 'Consistent Reader',
            'description': f'{current_streak}-day reading streak!'
        })
    
    if total_books >= 10:
        habits_formed.append({
            'icon': '📚',
            'title': 'Book Collector',
            'description': f'Added {total_books} books to your library'
        })
    
    if len(completed_books) >= 3:
        habits_formed.append({
            'icon': '✅',
            'title': 'Finisher',
            'description': f'Completed {len(completed_books)} books'
        })
    
    if total_reading_hours >= 10:
        habits_formed.append({
            'icon': '⏰',
            'title': 'Time Investor',
            'description': f'{total_reading_hours}+ hours invested in reading'
        })
    
    if completion_rate >= 80:
        habits_formed.append({
            'icon': '🎯',
            'title': 'Goal Achiever',
            'description': f'{completion_rate}% goal completion rate'
        })
    
    # Milestones achieved
    milestones = []
    
    if total_pages_read >= 1000:
        milestones.append({'icon': '📖', 'text': '1,000+ pages read'})
    elif total_pages_read >= 500:
        milestones.append({'icon': '📖', 'text': '500+ pages read'})
    
    if len(completed_books) >= 5:
        milestones.append({'icon': '🏆', 'text': '5+ books completed'})
    elif len(completed_books) >= 3:
        milestones.append({'icon': '🏆', 'text': '3+ books completed'})
    
    if highest_streak >= 14:
        milestones.append({'icon': '⭐', 'text': '14-day streak achieved'})
    elif highest_streak >= 7:
        milestones.append({'icon': '⭐', 'text': '7-day streak achieved'})
    
    # What you'll lose message
    features_at_risk = []
    
    if total_books > 12:
        books_to_lose = total_books - 12
        features_at_risk.append(f'Access to {books_to_lose} books (only 12 allowed on free plan)')
    
    if len(shelves) > 3:
        shelves_to_lose = len(shelves) - 3
        features_at_risk.append(f'{shelves_to_lose} custom shelves (only 3 allowed on free plan)')
    
    features_at_risk.extend([
        'Detailed reading analytics and charts',
        'Your reading history and progress tracking',
        'File upload capability for your books',
        'Priority support and future premium features'
    ])
    
    return {
        # Books
        'total_books': total_books,
        'completed_books': len(completed_books),
        'active_books': len(active_books),
        'recent_books': len(recent_books),
        
        # Pages
        'total_pages_read': total_pages_read,
        'reading_speed': reading_speed,
        
        # Time
        'total_hours': total_reading_hours,
        'total_minutes': total_reading_minutes_remainder,
        'avg_daily_minutes': avg_daily_minutes,
        'avg_daily_hours': avg_daily_minutes // 60,
        'avg_daily_minutes_remainder': avg_daily_minutes % 60,
        
        # Streaks & Goals
        'current_streak': current_streak,
        'highest_streak': highest_streak,
        'total_goals_completed': total_goals_completed,
        'total_goals_attempted': total_goals_attempted,
        'completion_rate': completion_rate,
        
        # Rankings
        'user_rank': user_rank,
        'total_users': total_users,
        'percentile': percentile,
        
        # Habits & Achievements
        'habits_formed': habits_formed,
        'milestones': milestones,
        
        # What's at risk
        'features_at_risk': features_at_risk,
        'total_shelves': len(shelves),
        
        # Improvement
        'days_active': days_active
    }


@app.route('/api/check-monthly-report')
@login_required
def check_monthly_report_status():
    """Check if user should see monthly report notification"""
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify(success=False)
    
    days_since_signup = (datetime.utcnow() - user.created_at).days
    
    show_notification = False
    message = ""
    
    # Check if premium is expiring soon
    if user.is_premium and user.premium_until:
        days_left = (user.premium_until - datetime.utcnow()).days
        if 0 <= days_left <= 7:
            show_notification = True
            message = f"Your premium expires in {days_left} days! See what you've accomplished."
    
    # Check if it's been ~30 days since signup
    if days_since_signup >= 28 and days_since_signup <= 32:
        show_notification = True
        message = "🎉 It's been a month! See your amazing reading progress."
    
    return jsonify(
        success=True,
        show_notification=show_notification,
        message=message,
        days_since_signup=days_since_signup
    )



# Add these functions to app.py

def send_monthly_report_email(user, report_data):
    """Send monthly report email to user"""
    try:
        days_left = 0
        if user.premium_until:
            days_left = (user.premium_until - datetime.utcnow()).days
        
        msg = Message(
            subject='📊 Your Monthly Reading Report - BookEx Chelf',
            recipients=[user.email],
            html=f"""
            <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        
                        <!-- Header -->
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0 0 10px 0; font-size: 32px;">🎉 Your Monthly Report</h1>
                            <p style="margin: 0; font-size: 16px; opacity: 0.95;">You've made incredible progress this month!</p>
                        </div>
                        
                        <!-- Stats Grid -->
                        <div style="padding: 30px;">
                            <h2 style="color: #333; margin: 0 0 20px 0; font-size: 24px;">Your Reading Stats</h2>
                            
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 30px;">
                                <div style="background: #f0f8ff; padding: 20px; border-radius: 12px; text-align: center;">
                                    <div style="font-size: 36px; font-weight: bold; color: #667eea;">{report_data['total_books']}</div>
                                    <div style="font-size: 14px; color: #666; margin-top: 5px;">Books Added</div>
                                </div>
                                
                                <div style="background: #f0f8ff; padding: 20px; border-radius: 12px; text-align: center;">
                                    <div style="font-size: 36px; font-weight: bold; color: #667eea;">{report_data['completed_books']}</div>
                                    <div style="font-size: 14px; color: #666; margin-top: 5px;">Completed</div>
                                </div>
                                
                                <div style="background: #f0f8ff; padding: 20px; border-radius: 12px; text-align: center;">
                                    <div style="font-size: 36px; font-weight: bold; color: #667eea;">{report_data['total_pages_read']}</div>
                                    <div style="font-size: 14px; color: #666; margin-top: 5px;">Pages Read</div>
                                </div>
                                
                                <div style="background: #f0f8ff; padding: 20px; border-radius: 12px; text-align: center;">
                                    <div style="font-size: 36px; font-weight: bold; color: #667eea;">{report_data['total_hours']}h</div>
                                    <div style="font-size: 14px; color: #666; margin-top: 5px;">Reading Time</div>
                                </div>
                            </div>
                            
                            <!-- Achievements -->
                            <h3 style="color: #333; margin: 30px 0 15px 0; font-size: 20px;">🏆 Your Achievements</h3>
                            <ul style="list-style: none; padding: 0; margin: 0;">
                                <li style="padding: 12px; background: #f9f9f9; margin-bottom: 8px; border-radius: 8px; border-left: 4px solid #667eea;">
                                    <strong>🔥 {report_data['highest_streak']}-day streak</strong> - Your best reading streak!
                                </li>
                                <li style="padding: 12px; background: #f9f9f9; margin-bottom: 8px; border-radius: 8px; border-left: 4px solid #667eea;">
                                    <strong>🎯 {report_data['completion_rate']}% success rate</strong> - You're crushing your goals!
                                </li>
                                <li style="padding: 12px; background: #f9f9f9; margin-bottom: 8px; border-radius: 8px; border-left: 4px solid #667eea;">
                                    <strong>📊 Top {report_data['percentile']}%</strong> - You're among the best readers!
                                </li>
                            </ul>
                            
                            <!-- Warning if premium expiring -->
                            {f'''
                            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); color: white; padding: 25px; border-radius: 12px; margin: 30px 0; text-align: center;">
                                <h3 style="margin: 0 0 10px 0; font-size: 22px;">⚠️ Your Premium Expires in {days_left} Days!</h3>
                                <p style="margin: 0 0 20px 0; font-size: 16px; opacity: 0.95;">
                                    Don't lose access to your {report_data['total_books']} books and all your progress data!
                                </p>
                                <a href="https://bookexchelf.com/pricing" style="display: inline-block; background: white; color: #ff6b6b; padding: 15px 40px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 16px;">
                                    Renew Premium Now →
                                </a>
                            </div>
                            ''' if days_left <= 7 else ''}
                            
                            <!-- CTA Button -->
                            <div style="text-align: center; margin-top: 30px;">
                                <a href="https://bookexchelf.com/monthly-report" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 16px;">
                                    View Full Report →
                                </a>
                            </div>
                            
                            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 30px;">
                                Keep up the great work! 📚<br>
                                - BookEx Chelf Team
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
        )
        
        mail.send(msg)
        print(f"✅ Monthly report email sent to {user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending monthly report email: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_and_send_monthly_reports():
    """Check all users and send monthly reports if needed"""
    with app.app_context():
        try:
            from models.book import MonthlyReportSent
            
            users = User.query.all()
            emails_sent = 0
            
            for user in users:
                if not user.email:
                    continue
                
                days_since_signup = (datetime.utcnow() - user.created_at).days
                
                # Send report if:
                # 1. It's been 28-32 days since signup (first month)
                # 2. Premium is expiring in 5 days
                should_send = False
                report_type = None
                
                # First month report (only send once)
                if 28 <= days_since_signup <= 32:
                    already_sent = MonthlyReportSent.query.filter_by(
                        user_id=user.id,
                        report_type='first_month'
                    ).first()
                    
                    if not already_sent:
                        should_send = True
                        report_type = 'first_month'
                
                # Premium expiring report
                if user.is_premium and user.premium_until:
                    days_left = (user.premium_until - datetime.utcnow()).days
                    
                    # Send at 7 days, 3 days, and 1 day before expiry
                    if days_left in [7, 3, 1]:
                        today = date.today()
                        already_sent_today = MonthlyReportSent.query.filter_by(
                            user_id=user.id,
                            report_type=f'premium_expiring_{days_left}d'
                        ).filter(
                            db.func.date(MonthlyReportSent.sent_at) == today
                        ).first()
                        
                        if not already_sent_today:
                            should_send = True
                            report_type = f'premium_expiring_{days_left}d'
                
                if should_send and report_type:
                    # Generate report
                    report_data = generate_monthly_report(user.id, user)
                    
                    # Send email
                    if send_monthly_report_email(user, report_data):
                        # Track that we sent this report
                        report_sent = MonthlyReportSent(
                            user_id=user.id,
                            report_type=report_type
                        )
                        db.session.add(report_sent)
                        db.session.commit()
                        
                        emails_sent += 1
                        print(f"✅ Sent {report_type} report to {user.email}")
            
            print(f"✅ Total monthly reports sent: {emails_sent}")
            
        except Exception as e:
            print(f"❌ Error in check_and_send_monthly_reports: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()


# Add this scheduled job to your existing scheduler
scheduler.add_job(
    func=check_and_send_monthly_reports,
    trigger=CronTrigger(hour=9, minute=0),  # 9:00 AM daily
    id='monthly_reports',
    replace_existing=True
)


@app.route('/api/track-report-view', methods=['POST'])
@login_required
def track_report_view():
    """Track when user views their monthly report"""
    try:
        user_id = session.get('user_id')
        # You could add a table to track report views if needed
        # For now, just return success
        print(f"User {user_id} viewed monthly report")
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500





































if __name__ == "__main__":
    app.run(debug=True)


