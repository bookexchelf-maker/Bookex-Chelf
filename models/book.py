from flask_sqlalchemy import SQLAlchemy
from datetime import date
from datetime import datetime
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm.attributes import flag_modified
from datetime import date
from datetime import datetime


db = SQLAlchemy()

class Shelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shelf_name = db.Column(db.String(100), nullable=False)

    user_id = db.Column(db.String(150), db.ForeignKey("user.email"), nullable=False)

    # Add relationship with cascade delete  
    books = db.relationship(
        "Book",
        backref="shelf",
        cascade="all, delete-orphan"
    )



class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_name = db.Column(db.String(200), nullable=False)
    total_pages = db.Column(db.Integer, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    today_date = db.Column(db.Date, default=date.today)
    # percent compelted is calculated in the html book_page
    #days to finish is calculated in the html book_page
    intention = db.Column(db.Text, nullable=True)
    current_page = db.Column(db.Integer, nullable=True)
    file_path = db.Column(db.String(555), nullable=True)
    external_link = db.Column(db.String(555), nullable=True)
    shelf_id = db.Column(db.Integer, db.ForeignKey("shelf.id"), nullable=False)
    status = db.Column(db.String(50), default="on_shelf", nullable=False)





from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)


     # ADD THIS FIELD
    user_location = db.Column(db.String(10), default='US')  # Stores: US, IN, UK, EU, etc.
    yearly_reading_goal = db.Column(db.Integer, default=12)  # Default goal: 50 books
    yearly_time_spent = db.Column(db.Integer, default=0) 

    # One-to-many: a user has many shelves
    shelves = db.relationship("Shelf", backref="user", cascade="all, delete-orphan")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Premium status (your simple solution)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    
    # Optional: Track subscription dates
    premium_since = db.Column(db.DateTime, nullable=True)
    premium_until = db.Column(db.DateTime, nullable=True)
    
    # For Stripe/Razorpay
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    razorpay_customer_id = db.Column(db.String(100), nullable=True)
    
    # Time tracking (in minutes)
    total_time_spend = db.Column(db.Integer, default=0, nullable=False)  # Total lifetime
    yearly_time_spend = db.Column(db.Integer, default=0, nullable=False)  # Current year (resets Dec 20)
    daily_time_spend = db.Column(db.Integer, default=0, nullable=False)   # Current day (resets daily)
    
    # Track last reset times
    last_daily_reset = db.Column(db.Date, default=date.today)
    last_yearly_reset = db.Column(db.Date, default=date.today)
    
    # Ranking system
    today_ranking = db.Column(db.Integer, default=0, nullable=False)  # Daily leaderboard rank (resets daily)
    total_ranking = db.Column(db.Integer, default=0, nullable=False)  # Cumulative ranking points
    
    # Track session start time
    last_login = db.Column(db.DateTime, nullable=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} Premium: {self.is_premium}>'
    
    # Time tracking methods
    def reset_daily_time_if_needed(self):
        """Reset daily time if a new day has started"""
        if self.last_daily_reset != date.today():
            # Add daily time to both yearly and total before resetting
            self.yearly_time_spend += self.daily_time_spend
            self.total_time_spend += self.daily_time_spend
            self.daily_time_spend = 0
            
            # Add today's ranking to total ranking before resetting
            self.total_ranking += self.today_ranking
            self.today_ranking = 0
            
            self.last_daily_reset = date.today()
            return True
        return False
    
    def reset_yearly_time_if_needed(self):
        """Reset yearly time on December 20th"""
        today = date.today()
        # Check if today is December 20th and we haven't reset this year
        if today.month == 12 and today.day == 20:
            if self.last_yearly_reset.year < today.year:
                # Just reset yearly time (total already updated daily)
                self.yearly_time_spend = 0
                self.last_yearly_reset = today
                return True
        return False
    
    def add_session_time(self, minutes):
        """Add time spent in current session"""
        if minutes > 0:
            self.reset_daily_time_if_needed()
            self.reset_yearly_time_if_needed()
            
            self.daily_time_spend += minutes
            return True
        return False
    
    def get_time_stats(self):
        """Get formatted time statistics"""
        self.reset_daily_time_if_needed()
        self.reset_yearly_time_if_needed()
        
        return {
            'total_hours': self.total_time_spend // 60,
            'total_minutes': self.total_time_spend % 60,
            'yearly_hours': self.yearly_time_spend // 60,
            'yearly_minutes': self.yearly_time_spend % 60,
            'daily_hours': self.daily_time_spend // 60,
            'daily_minutes': self.daily_time_spend % 60
        }
    
    # Helper methods
    def is_premium_user(self):
        """Check if user has active premium access"""
        if not self.is_premium or not self.premium_until:
            return False
        # Check if premium has expired
        if datetime.utcnow() > self.premium_until:
            self.is_premium = False
            return False
        return True
    
    def days_left_in_premium(self):
        """Get remaining days in premium subscription"""
        if not self.is_premium or not self.premium_until:
            return 0
        if datetime.utcnow() > self.premium_until:
            self.is_premium = False
            return 0
        return (self.premium_until - datetime.utcnow()).days






class UserDailyProgress(db.Model):
    __tablename__ = "user_daily_progress"
    
    # Use user_id as primary key
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    
    # Today's tracking
    today_goal_count = db.Column(db.Integer, default=0)
    today_completed_count = db.Column(db.Integer, default=0)
    today_tasks = db.Column(MutableList.as_mutable(db.JSON), default=list)
    today_goal_names = db.Column(MutableList.as_mutable(db.JSON), default=list)
    
    # Date tracking
    today_date = db.Column(db.Date, default=date.today)
    last_evaluated_date = db.Column(db.Date, nullable=True)
    
    # Streak tracking
    current_strike = db.Column(db.Integer, default=0)
    highest_strike = db.Column(db.Integer, default=0)
    
    # Statistics
    total_goals_completed = db.Column(db.Integer, default=0)
    total_goals_attempted = db.Column(db.Integer, default=0)
    
    def reset_for_new_day(self, goal_count, goal_names):
        """Reset for new day after evaluating yesterday"""
        self.evaluate_yesterday_strike()
        self.today_goal_count = goal_count
        self.today_completed_count = 0
        self.today_tasks = [False] * goal_count
        self.today_goal_names = goal_names
        self.today_date = date.today()
    
    def evaluate_yesterday_strike(self):
        """Evaluate if yesterday's goals were completed"""
        if self.last_evaluated_date == date.today():
            return
        
        if self.today_goal_count > 0:
            self.total_goals_attempted += self.today_goal_count
            self.total_goals_completed += self.today_completed_count
            
            if self.today_goal_count == self.today_completed_count:
                self.current_strike += 1
                if self.current_strike > self.highest_strike:
                    self.highest_strike = self.current_strike
            else:
                self.current_strike = 0
        
        self.last_evaluated_date = date.today()
    
    def toggle_task(self, index):
        """Toggle task completion"""
        if 0 <= index < len(self.today_tasks):
            self.today_tasks[index] = not self.today_tasks[index]
            flag_modified(self, "today_tasks")
            self.today_completed_count = sum(1 for task in self.today_tasks if task)
            return True
        return False












class ReferralCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='referral_codes')

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referral_code = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    referrer_reward_given = db.Column(db.Boolean, default=False)
    referred_reward_given = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_made')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referrals_received')




class EmailVerificationOTP(db.Model):
    __tablename__ = 'email_verification_otp'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    attempts = db.Column(db.Integer, default=0)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


















