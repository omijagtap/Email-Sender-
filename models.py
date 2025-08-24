from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class EmailCampaign(db.Model):
    __tablename__ = 'email_campaigns'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey(User.id), nullable=False)
    subject = db.Column(db.String, nullable=False)
    template_filename = db.Column(db.String, nullable=False)
    csv_filename = db.Column(db.String, nullable=False)
    mode = db.Column(db.String, nullable=False)  # 'personalized' or 'bulk'
    total_emails = db.Column(db.Integer, default=0)
    sent_emails = db.Column(db.Integer, default=0)
    failed_emails = db.Column(db.Integer, default=0)
    status = db.Column(db.String, default='draft')  # draft, sending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship(User, backref='campaigns')

class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey(EmailCampaign.id), nullable=False)
    recipient_email = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)  # sent, failed
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.now)
    
    campaign = db.relationship(EmailCampaign, backref='email_logs')
