from datetime import datetime
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    content_excerpt = db.Column(db.Text, default="")
    views = db.Column(db.Integer, default=0, nullable=False)
    approved = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    tg_post_url = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # New fields
    price_cents = db.Column(db.Integer, default=0, nullable=False)
    is_per_month = db.Column(db.Boolean, default=False, nullable=False)
    address = db.Column(db.String(255))
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    rooms = db.Column(db.Integer)
    area = db.Column(db.Float)
    floor = db.Column(db.Integer)
    floors_total = db.Column(db.Integer)
    period_days = db.Column(db.Integer)
    lease_term = db.Column(db.String(50))
    images_json = db.Column(db.Text)
    draft = db.Column(db.Boolean, default=False, nullable=False)
    # Marketplace fields (e.g., Куплю-продам)
    subcategory = db.Column(db.String(100))
    deal_type = db.Column(db.String(20))  # buy/sell/exchange
    district = db.Column(db.String(120))

    category = db.relationship('Category', backref=db.backref('announcements', lazy=True))


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_draft = db.Column(db.Boolean, default=False, nullable=False)
    cover_url = db.Column(db.Text)
    tags_json = db.Column(db.Text)
    seo_title = db.Column(db.String(160))
    seo_description = db.Column(db.Text)
    og_image_url = db.Column(db.Text)
    category = db.Column(db.String(120))
    views = db.Column(db.Integer, default=0, nullable=False)


class ArticleComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author_name = db.Column(db.String(120), nullable=False)
    author_email = db.Column(db.String(190))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved = db.Column(db.Boolean, default=True, nullable=False)


class AuthorSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(190), nullable=False)
    token = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = db.Column(db.DateTime)


class TgPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tg_message_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.DateTime, nullable=False)
    text = db.Column(db.Text)
    countries_json = db.Column(db.Text)  # JSON list of country names
    image_urls_json = db.Column(db.Text)  # JSON list of local static URLs
    source_link = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    balance_cents = db.Column(db.Integer, default=0, nullable=False)
    username_changed_at = db.Column(db.DateTime)
    avatar_url = db.Column(db.Text)
    bio = db.Column(db.Text)

    def set_password(self, password: str):
        # Explicit algorithm to avoid environments without hashlib.scrypt
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class TelegramVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    code = db.Column(db.String(6), nullable=False)
    username = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tg_user_id = db.Column(db.String(64))
    avatar_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    verified_at = db.Column(db.DateTime)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # кого оценивают
    reviewer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)  # 1..5
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
