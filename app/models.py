from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, url_for
import uuid

from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(255))
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(255))
    email_verification_expires = db.Column(db.DateTime)
    reset_password_token = db.Column(db.String(255))
    reset_password_expires = db.Column(db.DateTime)
    credits = db.Column(db.Integer, default=0, nullable=False)
    daily_credits_used = db.Column(db.Integer, default=0, nullable=False)
    last_credit_reset = db.Column(db.Date, default=lambda: datetime.utcnow().date(), nullable=False)
    referral_code = db.Column(db.String(10), unique=True)
    referred_by = db.Column(db.String(10))
    stripe_customer_id = db.Column(db.String(255))
    # Rate limiting fields
    api_calls_today = db.Column(db.Integer, default=0, nullable=False)
    last_api_call = db.Column(db.DateTime)
    subscription_tier = db.Column(db.String(20), default='free')  # free, basic, pro, enterprise
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    videos = db.relationship('Video', backref='user', lazy='dynamic')
    credit_transactions = db.relationship('CreditTransaction', backref='user', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_referral_code(self):
        return str(uuid.uuid4())[:8].upper()
    
    def ensure_referral_code(self):
        """Ensure user has a referral code, generate one if missing"""
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
            return True
        return False
    
    def can_generate_video(self, quality='free'):
        """Check if user can generate a video of given quality"""
        # Unlimited credits (-1) means user can always generate videos
        if self.credits == -1:
            return True
        # Calculate credit cost based on quality
        cost = 1 if quality == 'free' else 3
        return self.credits >= cost
    
    def use_credits(self, amount):
        """Deduct credits from user account"""
        # Unlimited credits (-1) means user can always use credits
        if self.credits == -1:
            return True
        if self.credits >= amount:
            self.credits -= amount
            
            # Record the transaction
            if self.id:
                transaction = CreditTransaction(
                    user_id=self.id,
                    amount=amount,
                    transaction_type='debit',
                    source='video_generation'
                )
                db.session.add(transaction)
            
            return True
        return False
    
    def add_credits(self, amount, source='purchase'):
        """Add credits to user account"""
        if self.credits is None:
            self.credits = 0
        self.credits += amount
        
        # Only create transaction if user has an ID (is committed to database)
        if self.id:
            transaction = CreditTransaction(
                user_id=self.id,
                amount=amount,
                transaction_type='credit',
                source=source
            )
            db.session.add(transaction)
    
    def reset_daily_credits(self):
        """Reset daily free credits if it's a new day"""
        today = datetime.utcnow().date()
        if self.last_credit_reset < today:
            self.daily_credits_used = 0
            self.last_credit_reset = today
            # Give daily free credits
            daily_credits = current_app.config.get('DAILY_FREE_CREDITS', 3)
            self.add_credits(daily_credits, 'daily_free')
            return True
        return False
    
    def can_use_daily_free(self):
        """Check if user can use daily free credits"""
        self.reset_daily_credits()  # Reset if needed
        max_daily = current_app.config.get('DAILY_FREE_CREDITS', 3)
        return self.daily_credits_used < max_daily
    
    def use_daily_free_credit(self):
        """Use a daily free credit"""
        if self.can_use_daily_free():
            self.daily_credits_used += 1
            return True
        return False
    
    def reset_api_calls(self):
        """Reset daily API calls if it's a new day"""
        today = datetime.utcnow().date()
        if not self.last_api_call or self.last_api_call.date() < today:
            self.api_calls_today = 0
            return True
        return False
    
    def can_make_api_call(self):
        """Check if user can make an API call based on rate limits"""
        self.reset_api_calls()
        
        # In testing mode, allow much higher limits for testing
        if current_app.config.get('TESTING'):
            # Allow 1000 calls per day in testing
            return self.api_calls_today < 1000
        
        # Get rate limits based on subscription tier
        rate_limits = {
            'free': 10,      # 10 calls per day
            'basic': 100,    # 100 calls per day
            'pro': 1000,     # 1000 calls per day
            'enterprise': -1 # Unlimited
        }
        
        limit = rate_limits.get(self.subscription_tier, 10)
        if limit == -1:  # Unlimited
            return True
        
        return self.api_calls_today < limit
    
    def record_api_call(self):
        """Record an API call for rate limiting"""
        self.reset_api_calls()
        self.api_calls_today += 1
        self.last_api_call = datetime.utcnow()
    
    def get_rate_limit_info(self):
        """Get current rate limit information"""
        self.reset_api_calls()
        
        # In testing mode, show testing limits
        if current_app.config.get('TESTING'):
            limit = 1000  # Testing limit
            remaining = limit - self.api_calls_today
            return {
                'tier': 'development',
                'limit': limit,
                'used': self.api_calls_today,
                'remaining': remaining,
                'reset_time': (self.last_api_call + timedelta(days=1)).isoformat() if self.last_api_call else None
            }
        
        rate_limits = {
            'free': 10,
            'basic': 100,
            'pro': 1000,
            'enterprise': -1
        }
        
        limit = rate_limits.get(self.subscription_tier, 10)
        remaining = limit - self.api_calls_today if limit != -1 else -1
        
        return {
            'tier': self.subscription_tier,
            'limit': limit,
            'used': self.api_calls_today,
            'remaining': remaining,
            'reset_time': (self.last_api_call + timedelta(days=1)).isoformat() if self.last_api_call else None
        }
    
    def get_referral_stats(self):
        """Get referral statistics for the user"""
        # Ensure user has a referral code
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
            db.session.commit()
        
        referred_users = User.query.filter_by(referred_by=self.referral_code).count()
        total_earned = CreditTransaction.query.filter_by(
            user_id=self.id,
            source='referral'
        ).with_entities(db.func.sum(CreditTransaction.amount)).scalar() or 0
        
        return {
            'referral_code': self.referral_code,
            'referred_users': referred_users,
            'total_earned': total_earned,
            'referral_url': f"{current_app.config.get('BASE_URL', 'https://prompttovideo.com')}/ref/{self.referral_code}"
        }
    
    def process_referral_signup(self, referred_user):
        """Process referral when a new user signs up using this user's code"""
        if referred_user.id != self.id:  # Can't refer yourself
            # Give credits to both users
            self.add_credits(5, 'referral')
            referred_user.add_credits(5, 'referral')
            
            # Create referral record
            referral = Referral(
                referrer_id=self.id,
                referred_id=referred_user.id,
                referrer_code=self.referral_code
            )
            db.session.add(referral)
            
            return True
        return False

class Video(db.Model):
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    quality = db.Column(db.String(10), default='free')  # free, premium
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed, content_violation
    veo_job_id = db.Column(db.String(255))
    gcs_url = db.Column(db.String(2000))
    gcs_signed_url = db.Column(db.String(2000))
    thumbnail_gcs_url = db.Column(db.String(2000))  # Direct GCS URL for thumbnail
    thumbnail_url = db.Column(db.String(2000))  # Public URL for thumbnail
    duration = db.Column(db.Integer)  # in seconds
    
    def get_thumbnail_url(self):
        """Get the thumbnail URL, with fallback to dynamic generation."""
        if self.thumbnail_url:
            return self.thumbnail_url
        if not self.gcs_url:
            return None
        from app.gcs_utils import generate_signed_thumbnail_url
        return generate_signed_thumbnail_url(self.gcs_url)

    slug = db.Column(db.String(255), unique=True)
    public = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    title = db.Column(db.String(200))  # SEO-friendly title
    description = db.Column(db.Text)   # SEO description
    tags = db.Column(db.JSON)          # Array of tags for SEO
    share_token = db.Column(db.String(64), unique=True)  # For private sharing
    embed_enabled = db.Column(db.Boolean, default=True)  # Allow embedding
    priority = db.Column(db.Integer, default=0)  # Queue priority (higher = higher priority)
    queued_at = db.Column(db.DateTime, default=datetime.utcnow)  # When added to queue
    started_at = db.Column(db.DateTime)  # When processing started
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        super(Video, self).__init__(**kwargs)
        # Generate a unique temporary slug that will be updated when saved
        if not self.slug:
            import time
            import random
            temp_id = f"temp-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
            self.slug = temp_id
    
    def generate_slug(self):
        """Generate a unique slug for the video"""
        if self.id:
            base_slug = f"{self.id}-{self.prompt[:50].lower().replace(' ', '-')}"
        else:
            base_slug = f"temp-{self.prompt[:50].lower().replace(' ', '-')}"
        return base_slug
    
    def ensure_slug(self):
        """Ensure the video has a proper slug"""
        if not self.slug or self.slug.startswith('temp-'):
            self.slug = self.generate_slug()
    
    def increment_views(self):
        """Increment view count"""
        self.views += 1
    
    def get_share_url(self):
        """Get shareable URL for the video"""
        try:
            if self.public:
                return url_for('main.watch_video', video_id=self.id, slug=self.slug, _external=True)
            else:
                return url_for('main.watch_video_private', token=self.share_token, _external=True)
        except RuntimeError:
            # If no application context, construct URL manually
            if self.public:
                return f"http://localhost:5000/watch/{self.id}-{self.slug}"
            else:
                return f"http://localhost:5000/watch/private/{self.share_token}"
    
    def get_embed_code(self):
        """Get embed code for the video"""
        if not self.embed_enabled:
            return None
        
        share_url = self.get_share_url()
        embed_url = f"{share_url}/embed" if share_url else ""
        return f'<iframe src="{embed_url}" width="640" height="360" frameborder="0" allowfullscreen></iframe>'
    
    def generate_share_token(self):
        """Generate a unique share token for private sharing"""
        import secrets
        self.share_token = secrets.token_urlsafe(32)
        return self.share_token
    
    def set_seo_data(self, title=None, description=None, tags=None):
        """Set SEO data for the video"""
        if title:
            self.title = title
        if description:
            self.description = description
        if tags:
            self.tags = tags if isinstance(tags, list) else [tags]
    
    def get_seo_title(self):
        """Get SEO-friendly title"""
        return self.title or f"AI Generated Video: {self.prompt[:50]}..."
    
    def get_seo_description(self):
        """Get SEO-friendly description"""
        return self.description or f"Watch this AI-generated video created with the prompt: {self.prompt[:100]}..."
    
    def get_seo_tags(self):
        """Get SEO tags"""
        return self.tags or []
    
    def calculate_priority(self):
        """Calculate queue priority based on various factors"""
        priority = 0
        
        # Higher quality videos get higher priority
        if self.quality == '1080p':
            priority += 10
        
        # Premium users get higher priority
        user = User.query.get(self.user_id)
        if user:
            if user.subscription_tier == 'enterprise':
                priority += 50
            elif user.subscription_tier == 'pro':
                priority += 30
            elif user.subscription_tier == 'basic':
                priority += 10
        
        # Videos that have been waiting longer get higher priority
        if self.queued_at:
            wait_time = datetime.utcnow() - self.queued_at
            priority += min(wait_time.total_seconds() / 60, 100)  # Max 100 points for wait time
        
        return int(priority)
    
    def update_priority(self):
        """Update the priority field"""
        self.priority = self.calculate_priority()
    
    def mark_started(self):
        """Mark video as started processing"""
        self.started_at = datetime.utcnow()
        self.status = 'processing'

class CreditTransaction(db.Model):
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # credit, debit
    source = db.Column(db.String(50), nullable=False)  # purchase, daily_free, video_generation, referral
    stripe_payment_intent_id = db.Column(db.String(255))
    stripe_session_id = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PromptPack(db.Model):
    __tablename__ = 'prompt_packs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    prompts = db.Column(db.JSON)  # List of prompt objects
    category = db.Column(db.String(50))
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')  # admin, super_admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ApiUsage(db.Model):
    __tablename__ = 'api_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)  # e.g., 'generate_video', 'video_status'
    method = db.Column(db.String(10), nullable=False)  # GET, POST, etc.
    response_time = db.Column(db.Float)  # Response time in seconds
    status_code = db.Column(db.Integer)  # HTTP status code
    user_agent = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='api_usage')


class Referral(db.Model):
    __tablename__ = 'referrals'
    
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referrer_code = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_given')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referrals_received')


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video = db.relationship('Video', backref='chat_messages')
    user = db.relationship('User', backref='chat_messages')
    reactions = db.relationship('ChatReaction', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    replies = db.relationship('ChatReply', backref='parent_message', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_reaction_counts(self):
        """Get reaction counts grouped by emoji"""
        reaction_counts = {}
        for reaction in self.reactions:
            emoji = reaction.emoji
            if emoji not in reaction_counts:
                reaction_counts[emoji] = {
                    'count': 0,
                    'users': []
                }
            reaction_counts[emoji]['count'] += 1
            reaction_counts[emoji]['users'].append({
                'id': reaction.user.id,
                'email': reaction.user.email
            })
        return reaction_counts
    
    def to_dict(self, include_replies=True):
        """Convert message to dictionary for JSON response"""
        return {
            'id': self.id,
            'video_id': self.video_id,
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'avatar': self.user.email[0].upper()
            },
            'content': self.content,
            'edited': self.edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'created_at': self.created_at.isoformat(),
            'reactions': self.get_reaction_counts(),
            'replies': [reply.to_dict() for reply in self.replies] if include_replies else [],
            'reply_count': self.replies.count()
        }


class ChatReaction(db.Model):
    __tablename__ = 'chat_reactions'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=True)
    reply_id = db.Column(db.Integer, db.ForeignKey('chat_replies.id'), nullable=True)  # For reply reactions
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)  # Unicode emoji
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='chat_reactions')
    reply = db.relationship('ChatReply', backref='reactions')
    
    # Ensure either message_id OR reply_id is set, but not both
    __table_args__ = (
        db.CheckConstraint('(message_id IS NOT NULL AND reply_id IS NULL) OR (message_id IS NULL AND reply_id IS NOT NULL)', name='check_reaction_target'),
        db.UniqueConstraint('message_id', 'user_id', 'emoji', name='unique_message_reaction'),
        db.UniqueConstraint('reply_id', 'user_id', 'emoji', name='unique_reply_reaction'),
    )


class ChatReply(db.Model):
    __tablename__ = 'chat_replies'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='chat_replies')
    
    def get_reaction_counts(self):
        """Get reaction counts grouped by emoji"""
        reaction_counts = {}
        for reaction in self.reactions:
            emoji = reaction.emoji
            if emoji not in reaction_counts:
                reaction_counts[emoji] = {
                    'count': 0,
                    'users': []
                }
            reaction_counts[emoji]['count'] += 1
            reaction_counts[emoji]['users'].append({
                'id': reaction.user.id,
                'email': reaction.user.email
            })
        return reaction_counts
    
    def to_dict(self):
        """Convert reply to dictionary for JSON response"""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'avatar': self.user.email[0].upper()
            },
            'content': self.content,
            'edited': self.edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'created_at': self.created_at.isoformat(),
            'reactions': self.get_reaction_counts()
        }


class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def increment_usage(self):
        """Increment tag usage count"""
        self.usage_count += 1
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'usage_count': self.usage_count
        }


class VideoTag(db.Model):
    __tablename__ = 'video_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    video = db.relationship('Video', backref='video_tags')
    tag = db.relationship('Tag', backref='video_tags')
    
    __table_args__ = (
        db.UniqueConstraint('video_id', 'tag_id', name='unique_video_tag'),
    )


class CommunityChallenge(db.Model):
    __tablename__ = 'community_challenges'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    theme = db.Column(db.String(100), nullable=False)
    prompt_guidelines = db.Column(db.Text)  # Guidelines for prompts
    status = db.Column(db.String(20), default='upcoming')  # upcoming, active, voting, completed
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    voting_end_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Prize configuration
    credit_prize_first = db.Column(db.Integer, default=50)
    credit_prize_second = db.Column(db.Integer, default=25)
    credit_prize_third = db.Column(db.Integer, default=10)
    
    # Stats
    submission_count = db.Column(db.Integer, default=0)
    total_votes = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='challenges_created')
    winner = db.relationship('User', foreign_keys=[winner_id], backref='challenges_won')
    submissions = db.relationship('ChallengeSubmission', backref='challenge', lazy='dynamic', cascade='all, delete-orphan')
    votes = db.relationship('ChallengeVote', backref='challenge', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_current_status(self):
        """Get current status based on dates"""
        now = datetime.utcnow()
        if now < self.start_date:
            return 'upcoming'
        elif now <= self.end_date:
            return 'active'
        elif now <= self.voting_end_date:
            return 'voting'
        else:
            return 'completed'
    
    def get_top_submissions(self, limit=10):
        """Get top submissions by vote count"""
        return self.submissions.join(ChallengeVote).group_by(ChallengeSubmission.id).order_by(
            db.func.count(ChallengeVote.id).desc()
        ).limit(limit).all()
    
    def to_dict(self, include_submissions=False):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'theme': self.theme,
            'status': self.get_current_status(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'voting_end_date': self.voting_end_date.isoformat(),
            'submission_count': self.submission_count,
            'total_votes': self.total_votes,
            'creator': {
                'id': self.creator.id,
                'email': self.creator.email,
                'username': self.creator.username
            },
            'submissions': [s.to_dict() for s in self.get_top_submissions()] if include_submissions else []
        }


class ChallengeSubmission(db.Model):
    __tablename__ = 'challenge_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('community_challenges.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    vote_count = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)  # Final ranking after voting
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='challenge_submissions')
    video = db.relationship('Video', backref='challenge_submission', uselist=False)
    votes = db.relationship('ChallengeVote', backref='submission', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'user_id', name='unique_user_challenge_submission'),
    )
    
    def update_vote_count(self):
        """Update cached vote count"""
        self.vote_count = self.votes.count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'title': self.title,
            'description': self.description,
            'vote_count': self.vote_count,
            'rank': self.rank,
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'username': self.user.username
            },
            'video': {
                'id': self.video.id,
                'title': self.video.title,
                'thumbnail_url': self.video.thumbnail_url,
                'gcs_signed_url': self.video.gcs_signed_url
            },
            'created_at': self.created_at.isoformat()
        }


class ChallengeVote(db.Model):
    __tablename__ = 'challenge_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('community_challenges.id'), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey('challenge_submissions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='challenge_votes')
    
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'user_id', name='unique_user_challenge_vote'),
    )


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    display_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(500))
    location = db.Column(db.String(100))
    website_url = db.Column(db.String(500))
    social_links = db.Column(db.JSON)  # Dict of social platform: username
    
    # Stats
    total_videos = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    follower_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    challenge_wins = db.Column(db.Integer, default=0)
    
    # Settings
    profile_public = db.Column(db.Boolean, default=True)
    allow_follows = db.Column(db.Boolean, default=True)
    email_notifications = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    
    def update_stats(self):
        """Update cached statistics"""
        self.total_videos = self.user.videos.filter_by(status='completed').count()
        self.total_views = db.session.query(db.func.sum(Video.views)).filter_by(user_id=self.user_id, status='completed').scalar() or 0
        self.follower_count = UserFollow.query.filter_by(followed_id=self.user_id).count()
        self.following_count = UserFollow.query.filter_by(follower_id=self.user_id).count()
        self.challenge_wins = ChallengeSubmission.query.filter_by(user_id=self.user_id, rank=1).count()
    
    def to_dict(self, include_stats=True):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'display_name': self.display_name or self.user.username or self.user.email,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'location': self.location,
            'website_url': self.website_url,
            'social_links': self.social_links or {},
            'profile_public': self.profile_public
        }
        
        if include_stats:
            data.update({
                'total_videos': self.total_videos,
                'total_views': self.total_views,
                'follower_count': self.follower_count,
                'following_count': self.following_count,
                'challenge_wins': self.challenge_wins
            })
        
        return data


class UserFollow(db.Model):
    __tablename__ = 'user_follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    followed = db.relationship('User', foreign_keys=[followed_id], backref='followers')
    
    __table_args__ = (
        db.UniqueConstraint('follower_id', 'followed_id', name='unique_user_follow'),
        db.CheckConstraint('follower_id != followed_id', name='no_self_follow'),
    )


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # follow, challenge_win, video_featured, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.JSON)  # Additional data like user_id, video_id, etc.
    read = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read = True
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'data': self.data or {},
            'read': self.read,
            'created_at': self.created_at.isoformat()
        } 