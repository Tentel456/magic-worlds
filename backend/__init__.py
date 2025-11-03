from flask import Flask
from dotenv import load_dotenv
from .config import config_by_name
from .extensions import db, migrate, login_manager, cors
from sqlalchemy import text


def create_app(config_name: str = "development") -> Flask:
    # Load .env once at startup
    load_dotenv()
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Flask-Login setup
    from .models import User  # local import to avoid cycles

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    login_manager.login_view = "serve_login"

    # Blueprints
    from .routes_public import public_bp
    app.register_blueprint(public_bp)

    from .routes_admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Create tables and seed minimal data on first run
    with app.app_context():
        db.create_all()
        # lightweight SQLite migration: add new columns if missing
        try:
            insp = db.session.execute(text("PRAGMA table_info('user')")).all()
            cols = {row[1] for row in insp}  # (cid, name, type, ...)
            if 'balance_cents' not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN balance_cents INTEGER NOT NULL DEFAULT 0"))
                db.session.commit()
            # announcement.user_id
            insp_a = db.session.execute(text("PRAGMA table_info('announcement')")).all()
            cols_a = {row[1] for row in insp_a}
            if 'user_id' not in cols_a:
                db.session.execute(text("ALTER TABLE announcement ADD COLUMN user_id INTEGER"))
                db.session.commit()
            # user.username_changed_at
            if 'username_changed_at' not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN username_changed_at DATETIME"))
                db.session.commit()
            # user.avatar_url
            if 'avatar_url' not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN avatar_url TEXT"))
                db.session.commit()
            # user.bio
            if 'bio' not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN bio TEXT"))
                db.session.commit()
            # user.is_banned
            if 'is_banned' not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT 0"))
                db.session.commit()
            # telegram_verification.avatar_url
            insp_tv = db.session.execute(text("PRAGMA table_info('telegram_verification')")).all()
            cols_tv = {row[1] for row in insp_tv}
            if 'avatar_url' not in cols_tv:
                db.session.execute(text("ALTER TABLE telegram_verification ADD COLUMN avatar_url TEXT"))
                db.session.commit()
            # article.user_id
            insp_art = db.session.execute(text("PRAGMA table_info('article')")).all()
            cols_art = {row[1] for row in insp_art}
            if 'user_id' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN user_id INTEGER"))
                db.session.commit()
            if 'is_draft' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN is_draft BOOLEAN NOT NULL DEFAULT 0"))
                db.session.commit()
            if 'cover_url' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN cover_url TEXT"))
                db.session.commit()
            if 'tags_json' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN tags_json TEXT"))
                db.session.commit()
            if 'seo_title' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN seo_title VARCHAR(160)"))
                db.session.commit()
            if 'seo_description' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN seo_description TEXT"))
                db.session.commit()
            if 'og_image_url' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN og_image_url TEXT"))
                db.session.commit()
            if 'category' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN category VARCHAR(120)"))
                db.session.commit()
            if 'views' not in cols_art:
                db.session.execute(text("ALTER TABLE article ADD COLUMN views INTEGER NOT NULL DEFAULT 0"))
                db.session.commit()
            # announcement advanced fields
            insp_ann = db.session.execute(text("PRAGMA table_info('announcement')")).all()
            cols_ann = {row[1] for row in insp_ann}
            def add_col(name, ddl):
                if name not in cols_ann:
                    db.session.execute(text(f"ALTER TABLE announcement ADD COLUMN {ddl}"))
                    db.session.commit()
            add_col('price_cents', "price_cents INTEGER NOT NULL DEFAULT 0")
            add_col('is_per_month', "is_per_month BOOLEAN NOT NULL DEFAULT 0")
            add_col('address', "address VARCHAR(255)")
            add_col('location_lat', "location_lat REAL")
            add_col('location_lng', "location_lng REAL")
            add_col('rooms', "rooms INTEGER")
            add_col('area', "area REAL")
            add_col('floor', "floor INTEGER")
            add_col('floors_total', "floors_total INTEGER")
            add_col('period_days', "period_days INTEGER")
            add_col('lease_term', "lease_term VARCHAR(50)")
            add_col('images_json', "images_json TEXT")
            add_col('draft', "draft BOOLEAN NOT NULL DEFAULT 0")
            add_col('subcategory', "subcategory VARCHAR(100)")
            add_col('deal_type', "deal_type VARCHAR(20)")
            add_col('district', "district VARCHAR(120)")
        except Exception:
            db.session.rollback()
        try:
            from .models import Category, Announcement, User
            if Category.query.count() == 0:
                c = Category(name="Общее", slug="general")
                db.session.add(c)
                db.session.commit()
            if Announcement.query.count() == 0:
                cat = Category.query.first()
                a = Announcement(title="Пример объявления",
                                  content_excerpt="Короткое описание из Телеграм-поста...",
                                  category_id=cat.id if cat else None,
                                  tg_post_url="https://t.me/Magic_Worlds_Travels")
                db.session.add(a)
                db.session.commit()
            # Ensure default admin exists
            admin = User.query.filter_by(username="admin").first()
            if not admin:
                admin = User(username="admin", is_admin=True, balance_cents=2000)
                admin.set_password("admin12345")
                db.session.add(admin)
                db.session.commit()
            else:
                # Make sure flags are correct; optionally reset password via env
                changed = False
                if not admin.is_admin:
                    admin.is_admin = True
                    changed = True
                if os.environ.get("FORCE_RESET_ADMIN", "0") == "1":
                    admin.set_password("admin12345")
                    changed = True
                if changed:
                    db.session.commit()
        except Exception:
            pass

    return app
