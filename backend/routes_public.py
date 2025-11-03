import os
from flask import Blueprint, jsonify, request, send_from_directory, abort, redirect, Response
import secrets
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, current_user
from .extensions import db
from .models import Announcement, User, TelegramVerification, Article, Review

public_bp = Blueprint("public", __name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------- Static site routes --------
@public_bp.get("/")
def serve_index():
    return send_from_directory(PROJECT_ROOT, "index.html")


@public_bp.get("/index.html")
def serve_index_html():
    return send_from_directory(PROJECT_ROOT, "index.html")


@public_bp.get("/category.html")
def serve_category_html():
    return send_from_directory(PROJECT_ROOT, "category.html")


@public_bp.get("/country-<slug>.html")
def serve_country_slug(slug):
    filename = f"country-{slug}.html"
    return send_from_directory(PROJECT_ROOT, filename)


@public_bp.get("/announcement.html")
def serve_announcement_html():
    return send_from_directory(PROJECT_ROOT, "announcement.html")


@public_bp.get("/article.html")
def serve_article_html():
    return send_from_directory(PROJECT_ROOT, "article.html")


@public_bp.get("/article")
def serve_article():
    return send_from_directory(PROJECT_ROOT, "article.html")


@public_bp.get("/assets/<path:filename>")
def serve_assets(filename):
    assets_dir = os.path.join(PROJECT_ROOT, "assets")
    if not os.path.commonpath([assets_dir, os.path.abspath(os.path.join(assets_dir, filename))]).startswith(assets_dir):
        abort(404)
    return send_from_directory(assets_dir, filename)


@public_bp.get("/uploads/<path:filename>")
def serve_uploads(filename):
    if not os.path.commonpath([UPLOAD_DIR, os.path.abspath(os.path.join(UPLOAD_DIR, filename))]).startswith(UPLOAD_DIR):
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename)


@public_bp.get("/robots.txt")
def robots_txt():
    host = request.host_url.rstrip('/')
    content = f"""User-agent: *
Allow: /
Sitemap: {host}/sitemap.xml
Sitemap: {host}/image-sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@public_bp.get("/sitemap.xml")
def sitemap_xml():
    host = request.host_url.rstrip('/')
    items = Announcement.query.order_by(Announcement.created_at.desc()).limit(5000).all()
    urlset = [
        f"<url><loc>{host}/preview?id={a.id}</loc><lastmod>{a.created_at.date().isoformat()}</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>"
        for a in items
    ]
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
          "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" \
          + ''.join(urlset) + "</urlset>"
    return Response(xml, mimetype="application/xml")


@public_bp.get("/image-sitemap.xml")
def image_sitemap_xml():
    host = request.host_url.rstrip('/')
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ns_img = "http://www.google.com/schemas/sitemap-image/1.1"
    items = Announcement.query.order_by(Announcement.created_at.desc()).limit(5000).all()
    urls = []
    for a in items:
        try:
            images = json.loads(a.images_json) if a.images_json else []
        except Exception:
            images = []
        img_tags = ''.join([f"<image:image><image:loc>{host}{u}</image:loc></image:image>" for u in images if isinstance(u, str)])
        urls.append(f"<url><loc>{host}/preview?id={a.id}</loc>{img_tags}</url>")
    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"{ns}\" xmlns:image=\"{ns_img}\">" + ''.join(urls) + "</urlset>"
    return Response(xml, mimetype="application/xml")


@public_bp.get("/login")
def serve_login():
    return send_from_directory(PROJECT_ROOT, "login.html")


@public_bp.get("/register")
def serve_register():
    return send_from_directory(PROJECT_ROOT, "register.html")


@public_bp.get("/create")
def serve_create_ad():
    return send_from_directory(PROJECT_ROOT, "create.html")


@public_bp.get("/profile")
def serve_profile():
    if not current_user.is_authenticated:
        return redirect("/login")
    return send_from_directory(PROJECT_ROOT, "profile.html")


@public_bp.get("/preview")
def serve_preview():
    return send_from_directory(PROJECT_ROOT, "preview.html")


@public_bp.get("/admin")
def serve_admin():
    if not current_user.is_authenticated:
        return redirect("/login")
    if not getattr(current_user, 'is_admin', False):
        return abort(403)
    return send_from_directory(PROJECT_ROOT, "admin.html")


@public_bp.get("/admin/editor")
def serve_admin_editor():
    if not current_user.is_authenticated:
        return redirect("/login")
    if not getattr(current_user, 'is_admin', False):
        return abort(403)
    return send_from_directory(PROJECT_ROOT, "editor.html")


# -------- Admin APIs --------
def _require_admin():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    if not getattr(current_user, 'is_admin', False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    return None


@public_bp.get("/api/admin/summary")
def api_admin_summary():
    maybe = _require_admin()
    if maybe: return maybe
    users_count = User.query.count()
    anns_total = Announcement.query.count()
    anns_drafts = Announcement.query.filter_by(draft=True).count()
    anns_published = anns_total - anns_drafts
    latest = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    return jsonify({
        "ok": True,
        "users": users_count,
        "announcements": anns_total,
        "published": anns_published,
        "drafts": anns_drafts,
        "latest": [
            {"id": a.id, "title": a.title, "created_at": a.created_at.isoformat(), "draft": bool(a.draft)}
            for a in latest
        ]
    })


@public_bp.get("/api/articles")
def api_public_articles_list():
    try:
        limit = min(max(int(request.args.get('limit', 5)), 1), 50)
    except Exception:
        limit = 5
    q = Article.query.filter_by(is_draft=False).order_by(Article.created_at.desc())
    author = (request.args.get('author') or '').strip()
    if author:
        u = User.query.filter(User.username.ilike(author)).first()
        if u:
            q = q.filter(Article.user_id == u.id)
        else:
            return jsonify({"ok": True, "items": []})
    items = q.limit(limit).all()
    return jsonify({
        "ok": True,
        "items": [
            {"id": a.id, "title": a.title, "cover_url": a.cover_url or "", "created_at": a.created_at.isoformat()}
            for a in items
        ]
    })


@public_bp.get("/api/articles/<int:aid>/comments")
def api_public_article_comments(aid: int):
    a = Article.query.get_or_404(aid)
    if a.is_draft and not (current_user.is_authenticated and getattr(current_user, 'is_admin', False)):
        # In drafts, do not expose comments publicly
        return jsonify({"ok": True, "items": []})
    from .models import ArticleComment
    rows = (ArticleComment.query
            .filter_by(article_id=aid, approved=True)
            .order_by(ArticleComment.created_at.asc()).all())
    return jsonify({
        "ok": True,
        "items": [
            {"id": c.id, "author_name": c.author_name, "content": c.content, "created_at": c.created_at.isoformat()} for c in rows
        ]
    })


@public_bp.post("/api/articles/<int:aid>/comments")
def api_public_article_comment_create(aid: int):
    a = Article.query.get_or_404(aid)
    if a.is_draft and not (current_user.is_authenticated and getattr(current_user, 'is_admin', False)):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip() or "Аноним"
    email = (data.get('email') or '').strip() or None
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({"ok": False, "error": "empty"}), 400
    from .models import ArticleComment
    c = ArticleComment(article_id=aid, user_id=(current_user.id if current_user.is_authenticated else None), author_name=name, author_email=email, content=content, approved=True)
    db.session.add(c)
    db.session.commit()
    return jsonify({"ok": True, "id": c.id})


@public_bp.post("/api/articles/<int:aid>/view")
def api_public_article_view(aid: int):
    a = Article.query.get_or_404(aid)
    if a.is_draft and not (current_user.is_authenticated and getattr(current_user, 'is_admin', False)):
        return jsonify({"ok": False}), 200
    a.views = (a.views or 0) + 1
    db.session.commit()
    return jsonify({"ok": True, "views": int(a.views or 0)})


@public_bp.post("/api/subscribe/author")
def api_subscribe_author():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    author_id = data.get('author_id')
    if not email or not author_id:
        return jsonify({"ok": False, "error": "missing"}), 400
    from .models import AuthorSubscription
    import secrets
    token = secrets.token_urlsafe(24)
    sub = AuthorSubscription(author_id=int(author_id), email=email, token=token)
    db.session.add(sub)
    db.session.commit()
    confirm_url = f"{request.host_url.rstrip('/')}/confirm-subscription?token={token}"
    # Email sending can be integrated here; for now, return confirm_url for client display
    return jsonify({"ok": True, "confirm_url": confirm_url})


@public_bp.get("/confirm-subscription")
def api_confirm_subscription():
    from .models import AuthorSubscription
    token = request.args.get('token') or ''
    sub = AuthorSubscription.query.filter_by(token=token).first()
    if not sub:
        return Response("Invalid token", status=400)
    if not sub.confirmed_at:
        sub.confirmed_at = datetime.utcnow()
        db.session.commit()
    return Response("Подписка подтверждена. Спасибо!", mimetype='text/plain')


@public_bp.get("/api/admin/announcements")
def api_admin_ann_list():
    maybe = _require_admin()
    if maybe: return maybe
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per = min(max(int(request.args.get("per", 20)), 1), 100)
    except Exception:
        page, per = 1, 20
    q = Announcement.query.order_by(Announcement.created_at.desc())
    draft = request.args.get("draft")
    if draft in ("0","1"):
        q = q.filter_by(draft=(draft=="1"))
    # Filters: q (search), category_id, author (username ilike)
    qstr = (request.args.get('q') or '').strip()
    if qstr:
        like = f"%{qstr}%"
        q = q.filter((Announcement.title.ilike(like)) | (Announcement.content_excerpt.ilike(like)))
    cat = request.args.get('category_id')
    try:
        if cat is not None and cat != '':
            q = q.filter(Announcement.category_id == int(cat))
    except Exception:
        pass
    author = (request.args.get('author') or '').strip()
    if author:
        from .models import User
        match_ids = [u.id for u in User.query.filter(User.username.ilike(f"%{author}%")).all()]
        if match_ids:
            q = q.filter(Announcement.user_id.in_(match_ids))
        else:
            q = q.filter(False)
    total = q.count()
    items = q.offset((page-1)*per).limit(per).all()
    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "per": per,
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "created_at": a.created_at.isoformat(),
                "draft": bool(a.draft),
                "user_id": a.user_id,
                "category_id": a.category_id,
                "views": a.views or 0,
                "price": round((a.price_cents or 0)/100, 2),
                "address": a.address or "",
                "first_image": (lambda imgs: (imgs[0] if imgs else None))((__import__('json').loads(a.images_json) if a.images_json else [])),
                "images_count": (lambda imgs: len(imgs))((__import__('json').loads(a.images_json) if a.images_json else [])),
                "is_per_month": bool(getattr(a, 'is_per_month', False)),
                "area": float(a.area) if a.area is not None else None,
                "rooms": int(a.rooms) if a.rooms is not None else None,
            } for a in items
        ]
    })


@public_bp.get("/api/admin/categories")
def api_admin_categories():
    maybe = _require_admin()
    if maybe: return maybe
    from .models import Category
    items = Category.query.order_by(Category.id.asc()).all()
    return jsonify({
        "ok": True,
        "items": [ {"id": c.id, "name": c.name} for c in items ]
    })


@public_bp.get("/api/admin/articles")
def api_admin_articles():
    maybe = _require_admin()
    if maybe: return maybe
    try:
        page = max(int(request.args.get('page', 1)), 1)
        per = min(max(int(request.args.get('per', 20)), 1), 100)
    except Exception:
        page, per = 1, 20
    q = Article.query.order_by(Article.created_at.desc())
    draft = request.args.get('draft')
    if draft in ('0','1'):
        q = q.filter(Article.is_draft == (draft=='1'))
    term = (request.args.get('q') or '').strip()
    if term:
        like = f"%{term}%"
        q = q.filter((Article.title.ilike(like)) | (Article.content.ilike(like)))
    author = (request.args.get('author') or '').strip()
    if author:
        match_ids = [u.id for u in User.query.filter(User.username.ilike(f"%{author}%")).all()]
        if match_ids:
            q = q.filter(Article.user_id.in_(match_ids))
        else:
            q = q.filter(False)
    total = q.count()
    items = q.offset((page-1)*per).limit(per).all()
    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "per": per,
        "items": [
            {"id": a.id, "title": a.title, "created_at": a.created_at.isoformat(), "draft": bool(a.is_draft), "user_id": a.user_id}
            for a in items
        ]
    })


@public_bp.post("/api/admin/articles")
def api_admin_articles_create():
    maybe = _require_admin()
    if maybe: return maybe
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '')
    is_draft = bool(data.get('is_draft', True))
    cover_url = (data.get('cover_url') or '').strip() or None
    seo_title = (data.get('seo_title') or '').strip() or None
    seo_description = (data.get('seo_description') or '').strip() or None
    og_image_url = (data.get('og_image_url') or '').strip() or None
    category = (data.get('category') or '').strip() or None
    tags = data.get('tags')
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    if tags is not None and not isinstance(tags, list):
        tags = None
    # Drafts may be created with empty title; set placeholder
    if not title:
        title = "Черновик" if is_draft else None
    if not title:
        return jsonify({"ok": False, "error": "missing_title"}), 400
    a = Article(
        title=title,
        content=content,
        is_draft=is_draft,
        user_id=current_user.id,
        cover_url=cover_url,
        tags_json=json.dumps(tags) if tags else None,
        seo_title=seo_title,
        seo_description=seo_description,
        og_image_url=og_image_url,
        category=category,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"ok": True, "id": a.id})


@public_bp.get("/api/admin/articles/<int:aid>")
def api_admin_article_get(aid: int):
    maybe = _require_admin()
    if maybe: return maybe
    a = Article.query.get_or_404(aid)
    return jsonify({
        "ok": True,
        "item": {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "is_draft": bool(a.is_draft),
            "cover_url": a.cover_url or "",
            "tags": (json.loads(a.tags_json) if a.tags_json else []),
            "seo_title": a.seo_title or "",
            "seo_description": a.seo_description or "",
            "og_image_url": a.og_image_url or "",
            "category": a.category or "",
            "created_at": a.created_at.isoformat(),
            "user_id": a.user_id,
        }
    })


@public_bp.put("/api/admin/articles/<int:aid>")
def api_admin_article_update(aid: int):
    maybe = _require_admin()
    if maybe: return maybe
    a = Article.query.get_or_404(aid)
    data = request.get_json(silent=True) or {}
    title = data.get('title')
    content = data.get('content')
    is_draft = data.get('is_draft')
    cover_url = data.get('cover_url')
    seo_title = data.get('seo_title')
    seo_description = data.get('seo_description')
    og_image_url = data.get('og_image_url')
    category = data.get('category')
    tags = data.get('tags')
    if title is not None:
        t = (title or '').strip()
        if not t:
            t = a.title or 'Черновик'
        a.title = t
    if content is not None:
        a.content = content
    if is_draft is not None:
        a.is_draft = bool(is_draft)
    if cover_url is not None:
        a.cover_url = (cover_url or '').strip() or None
    if seo_title is not None:
        a.seo_title = (seo_title or '').strip() or None
    if seo_description is not None:
        a.seo_description = (seo_description or '').strip() or None
    if og_image_url is not None:
        a.og_image_url = (og_image_url or '').strip() or None
    if category is not None:
        a.category = (category or '').strip() or None
    if tags is not None:
        if isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split(',') if t.strip()]
        elif isinstance(tags, list):
            tags_list = tags
        else:
            tags_list = None
        a.tags_json = json.dumps(tags_list) if tags_list else None
    db.session.commit()
    return jsonify({"ok": True})


@public_bp.get("/api/admin/users")
def api_admin_users():
    maybe = _require_admin()
    if maybe: return maybe
    q = User.query
    term = (request.args.get('q') or '').strip()
    if term:
        q = q.filter(User.username.ilike(f"%{term}%"))
    try:
        page = max(int(request.args.get('page', 1)), 1)
        per = min(max(int(request.args.get('per', 20)), 1), 100)
    except Exception:
        page, per = 1, 20
    total = q.count()
    items = q.order_by(User.id.desc()).offset((page-1)*per).limit(per).all()
    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "per": per,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "is_admin": bool(u.is_admin),
                "is_banned": bool(getattr(u, 'is_banned', False)),
                "balance": round((u.balance_cents or 0)/100, 2),
                "avatar_url": u.avatar_url or ""
            } for u in items
        ]
    })


@public_bp.post("/api/admin/users/<int:uid>/ban")
def api_admin_user_ban(uid: int):
    maybe = _require_admin()
    if maybe: return maybe
    u = User.query.get_or_404(uid)
    u.is_banned = True
    db.session.commit()
    return jsonify({"ok": True})


@public_bp.post("/api/admin/users/<int:uid>/unban")
def api_admin_user_unban(uid: int):
    maybe = _require_admin()
    if maybe: return maybe
    u = User.query.get_or_404(uid)
    u.is_banned = False
    db.session.commit()
    return jsonify({"ok": True})


@public_bp.post("/api/admin/users/<int:uid>/balance")
def api_admin_user_balance(uid: int):
    maybe = _require_admin()
    if maybe: return maybe
    u = User.query.get_or_404(uid)
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get('amount') or 0)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_amount"}), 400
    u.balance_cents = (u.balance_cents or 0) + int(round(amount * 100))
    db.session.commit()
    return jsonify({"ok": True, "balance": round((u.balance_cents or 0)/100, 2)})


@public_bp.get("/api/admin/reports/activity")
def api_admin_reports_activity():
    maybe = _require_admin()
    if maybe: return maybe
    # Simple activity: announcements created per day (with selectable window)
    from datetime import datetime, timedelta
    try:
        window = int(request.args.get('days', 14))
    except Exception:
        window = 14
    window = max(1, min(window, 180))
    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(window-1, -1, -1)]
    out = []
    for d in days:
        start = datetime(d.year, d.month, d.day)
        end = start + timedelta(days=1)
        cnt = Announcement.query.filter(Announcement.created_at >= start, Announcement.created_at < end).count()
        out.append({"date": d.isoformat(), "count": cnt})
    return jsonify({"ok": True, "series": out})


@public_bp.get("/api/admin/reports/categories")
def api_admin_reports_categories():
    maybe = _require_admin()
    if maybe: return maybe
    # Count per category_id
    rows = db.session.execute(db.text("SELECT COALESCE(category_id, 0) as cid, COUNT(*) as c FROM announcement GROUP BY cid")).all()
    data = [{"category_id": int(r[0]), "count": int(r[1])} for r in rows]
    return jsonify({"ok": True, "data": data})


@public_bp.get("/api/admin/settings")
def api_admin_settings_get():
    maybe = _require_admin()
    if maybe: return maybe
    # Provide environment-based settings
    return jsonify({
        "ok": True,
        "settings": {
            "YANDEX_MAPS_API_KEY": os.environ.get("YANDEX_MAPS_API_KEY", ""),
            "TELEGRAM_BOT_USERNAME": os.environ.get("TELEGRAM_BOT_USERNAME", ""),
            "SEO_SITE_NAME": os.environ.get("SEO_SITE_NAME", "Magic Worlds"),
            "SEO_DESCRIPTION": os.environ.get("SEO_DESCRIPTION", ""),
            "SEO_DEFAULT_IMAGE": os.environ.get("SEO_DEFAULT_IMAGE", "/assets/images/logo.png"),
            "SEO_TWITTER": os.environ.get("SEO_TWITTER", ""),
            "FAVICON_URL": os.environ.get("FAVICON_URL", "/assets/favicon/image.png"),
            "OG_TYPE": os.environ.get("OG_TYPE", "website"),
        }
    })


@public_bp.post("/api/admin/settings")
def api_admin_settings_set():
    maybe = _require_admin()
    if maybe: return maybe
    # For demo purposes write to a .env file in project root
    data = request.get_json(silent=True) or {}
    env_path = os.path.join(PROJECT_ROOT, '.env')
    try:
        # Read existing
        existing = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        k,v = line.strip().split('=',1)
                        existing[k]=v
        # Apply updates
        for k in ['YANDEX_MAPS_API_KEY','TELEGRAM_BOT_USERNAME','SEO_SITE_NAME','SEO_DESCRIPTION','SEO_DEFAULT_IMAGE','SEO_TWITTER','FAVICON_URL','OG_TYPE']:
            if k in data:
                existing[k] = str(data[k])
        # Write back
        with open(env_path, 'w') as f:
            for k,v in existing.items():
                f.write(f"{k}={v}\n")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": "write_failed"}), 500

@public_bp.get("/api/config")
def api_public_config():
    return jsonify({
        "yandex_maps_api_key": os.environ.get("YANDEX_MAPS_API_KEY", "")
    })


@public_bp.get("/api/announcements")
def list_announcements():
    from .models import Category  # local import to avoid cycles
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)
    country = (request.args.get("country") or "").strip()
    category_id = request.args.get("category_id")

    q = Announcement.query
    # filter by category name (country) if provided
    if country:
        q = q.join(Category).filter(Category.name == country)
    if category_id:
        try:
            cid = int(category_id)
            q = q.filter(Announcement.category_id == cid)
        except Exception:
            pass
    items = (
        q.order_by(Announcement.created_at.desc())
         .offset(offset)
         .limit(limit)
         .all()
    )

    def first_image(a):
        try:
            import json as _json
            imgs = _json.loads(a.images_json) if a.images_json else []
            return imgs[0] if imgs else None
        except Exception:
            return None

    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "excerpt": a.content_excerpt or "",
            "views": a.views,
            "created_at": a.created_at.isoformat(),
            "category_id": a.category_id,
            "tg_post_url": a.tg_post_url,
            "image_url": first_image(a),
            "price": round((a.price_cents or 0) / 100, 2),
        }
        for a in items
    ])


@public_bp.get("/api/tg_posts")
def api_tg_posts():
    from .models import TgPost
    import json as _json
    country = (request.args.get("country") or "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)

    q = TgPost.query.order_by(TgPost.date.desc())
    if country:
        # crude filter: countries_json contains the country name as a JSON string
        like = f'%"{country}"%'
        q = q.filter(TgPost.countries_json.like(like))
    items = q.offset(offset).limit(limit).all()

    def first_image(tp):
        try:
            arr = _json.loads(tp.image_urls_json) if tp.image_urls_json else []
            return arr[0] if arr else None
        except Exception:
            return None

    def first_lines(text, max_len=160):
        t = (text or '').strip()
        if len(t) <= max_len:
            return t
        return t[:max_len-1] + '…'

    return jsonify([
        {
            "id": tp.id,
            "message_id": tp.tg_message_id,
            "date": tp.date.isoformat() if tp.date else None,
            "text_excerpt": first_lines(tp.text or ''),
            "image_url": first_image(tp),
            "countries": _json.loads(tp.countries_json) if tp.countries_json else [],
            "source_link": tp.source_link,
        }
        for tp in items
    ])


@public_bp.get("/api/announcements/<int:aid>")
def get_announcement(aid: int):
    a = Announcement.query.get_or_404(aid)
    return jsonify({
        "id": a.id,
        "title": a.title,
        "excerpt": a.content_excerpt or "",
        "views": a.views,
        "created_at": a.created_at.isoformat(),
        "category_id": a.category_id,
        "tg_post_url": a.tg_post_url,
    })


@public_bp.post("/api/announcements/<int:aid>/view")
def increment_view(aid: int):
    a = Announcement.query.get_or_404(aid)
    a.views = (a.views or 0) + 1
    db.session.commit()
    return jsonify({"id": a.id, "views": a.views})


# -------- Auth endpoints --------
@public_bp.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "error": "missing_credentials"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401
    login_user(user)
    return jsonify({"ok": True, "user": {
        "id": user.id,
        "username": user.username,
        "balance": round((user.balance_cents or 0) / 100, 2),
        "avatar_url": user.avatar_url or "",
        "bio": user.bio or ""
    }})


# -------- Telegram registration flow --------
@public_bp.post("/api/auth/telegram/init")
def api_telegram_init():
    # No username/password required — registration will use Telegram username
    # Create verification with random password to complete account creation
    token = secrets.token_urlsafe(24)
    code = f"{secrets.randbelow(1000000):06d}"
    random_password = secrets.token_urlsafe(12)
    tv = TelegramVerification(
        token=token,
        code=code,
        username="pending",
        password_hash=generate_password_hash(random_password, method='pbkdf2:sha256', salt_length=16),
    )
    db.session.add(tv)
    db.session.commit()
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "")
    deep_link = f"https://t.me/{bot_username}?start={token}" if bot_username else None
    return jsonify({"ok": True, "token": token, "deep_link": deep_link})


@public_bp.post("/api/auth/telegram/complete")
def api_telegram_complete():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    code = (data.get("code") or "").strip()
    tv = TelegramVerification.query.filter_by(token=token).first()
    if not tv:
        return jsonify({"ok": False, "error": "invalid_token"}), 400
    # expire after 15 minutes
    if tv.created_at and datetime.utcnow() - tv.created_at > timedelta(minutes=15):
        return jsonify({"ok": False, "error": "expired"}), 410
    if tv.code != code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400
    # Username should be set by Telegram bot handler
    base_username = (tv.username or "user").strip()
    if base_username == "pending":
        base_username = "user"
    # ensure unique username
    candidate = base_username
    suffix = 0
    while User.query.filter_by(username=candidate).first() is not None:
        suffix += 1
        candidate = f"{base_username}{suffix}"
    user = User(username=candidate, is_admin=False, balance_cents=0)
    user.password_hash = tv.password_hash
    if tv.avatar_url:
        user.avatar_url = tv.avatar_url
    # Admin promotion based on Telegram user id
    admin_tg_id = os.environ.get("ADMIN_TG_ID")
    if admin_tg_id and str(getattr(tv, 'tg_user_id', '')) == str(admin_tg_id):
        user.is_admin = True
    db.session.add(user)
    db.session.delete(tv)
    db.session.commit()
    login_user(user)
    return jsonify({"ok": True, "user": {
        "id": user.id,
        "username": user.username,
        "balance": round((user.balance_cents or 0)/100, 2),
        "avatar_url": user.avatar_url or ""
    }})


# -------- Telegram login flow --------
@public_bp.post("/api/auth/telegram/login_init")
def api_telegram_login_init():
    token = secrets.token_urlsafe(24)
    code = f"{secrets.randbelow(1000000):06d}"
    tv = TelegramVerification(
        token=token,
        code=code,
        username="pending",
        password_hash=generate_password_hash(secrets.token_urlsafe(12), method='pbkdf2:sha256', salt_length=16),
    )
    db.session.add(tv)
    db.session.commit()
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "")
    deep_link = f"https://t.me/{bot_username}?start={token}" if bot_username else None
    return jsonify({"ok": True, "token": token, "deep_link": deep_link})


@public_bp.post("/api/auth/telegram/login_complete")
def api_telegram_login_complete():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    code = (data.get("code") or "").strip()
    tv = TelegramVerification.query.filter_by(token=token).first()
    if not tv:
        return jsonify({"ok": False, "error": "invalid_token"}), 400
    if tv.created_at and datetime.utcnow() - tv.created_at > timedelta(minutes=15):
        return jsonify({"ok": False, "error": "expired"}), 410
    if tv.code != code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400
    username = (tv.username or "").strip()
    if username == "pending":
        return jsonify({"ok": False, "error": "not_verified_in_bot"}), 400
    user = User.query.filter_by(username=username).first()
    if not user:
        # auto-create user if not found
        base_username = username or "user"
        candidate = base_username
        suffix = 0
        while User.query.filter_by(username=candidate).first() is not None:
            suffix += 1
            candidate = f"{base_username}{suffix}"
        user = User(username=candidate, is_admin=False, balance_cents=0)
        user.password_hash = tv.password_hash
        # set avatar from Telegram if available
        if getattr(tv, 'avatar_url', None):
            user.avatar_url = tv.avatar_url
        db.session.add(user)
    # Admin promotion if Telegram user id matches
    admin_tg_id = os.environ.get("ADMIN_TG_ID")
    if admin_tg_id and str(getattr(tv, 'tg_user_id', '')) == str(admin_tg_id):
        user.is_admin = True
    # Update avatar from Telegram on each login if available
    if getattr(tv, 'avatar_url', None):
        try:
            if not user.avatar_url or user.avatar_url != tv.avatar_url:
                user.avatar_url = tv.avatar_url
        except Exception:
            pass
    # cleanup verification and login
    db.session.delete(tv)
    db.session.commit()
    login_user(user)
    return jsonify({"ok": True, "user": {
        "id": user.id,
        "username": user.username,
        "balance": round((user.balance_cents or 0)/100, 2),
        "avatar_url": user.avatar_url or ""
    }})


# -------- Me (authenticated) endpoints --------
@public_bp.get("/api/me/announcements")
def api_my_announcements():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per", 10)), 1), 50)
    except Exception:
        page, per_page = 1, 10
    q = Announcement.query.filter_by(user_id=current_user.id).order_by(Announcement.created_at.desc())
    total = q.count()
    items = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "per": per_page,
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "excerpt": a.content_excerpt or "",
                "views": a.views,
                "created_at": a.created_at.isoformat(),
                "category_id": a.category_id,
            } for a in items
        ]
    })


@public_bp.post("/api/me/topup")
def api_me_topup():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    try:
        amount = float(amount)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_amount"}), 400
    if amount <= 0:
        return jsonify({"ok": False, "error": "invalid_amount"}), 400
    cents = int(round(amount * 100))
    current_user.balance_cents = (current_user.balance_cents or 0) + cents
    db.session.commit()
    return jsonify({"ok": True, "balance": round((current_user.balance_cents or 0)/100, 2)})


@public_bp.post("/api/me/profile")
def api_me_profile_update():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    new_username = (data.get("username") or "").strip()
    new_password = data.get("password") or None
    new_bio = data.get("bio")
    changed = False
    if new_username and new_username != current_user.username:
        if len(new_username) < 3:
            return jsonify({"ok": False, "error": "weak_username"}), 400
        if User.query.filter_by(username=new_username).first():
            return jsonify({"ok": False, "error": "user_exists"}), 409
        # cooldown 24h between renames
        from datetime import datetime, timedelta
        if getattr(current_user, 'username_changed_at', None):
            if datetime.utcnow() - (current_user.username_changed_at) < timedelta(hours=24):
                return jsonify({"ok": False, "error": "rename_cooldown"}), 429
        current_user.username = new_username
        current_user.username_changed_at = datetime.utcnow()
        changed = True
    if new_password:
        if len(new_password) < 6:
            return jsonify({"ok": False, "error": "weak_password"}), 400
        current_user.set_password(new_password)
        changed = True
    if new_bio is not None:
        current_user.bio = new_bio
        changed = True
    if changed:
        db.session.commit()
    return jsonify({
        "ok": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "balance": round((current_user.balance_cents or 0)/100, 2),
            "avatar_url": current_user.avatar_url or "",
            "bio": current_user.bio or ""
        }
    })


# -------- Articles (authenticated) --------
@public_bp.get("/api/me/articles")
def api_my_articles_list():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    items = (Article.query
             .filter_by(user_id=current_user.id)
             .order_by(Article.created_at.desc())
             .all())
    return jsonify({
        "ok": True,
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "created_at": a.created_at.isoformat(),
            } for a in items
        ]
    })


@public_bp.post("/api/me/articles")
def api_my_articles_create():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"ok": False, "error": "missing_fields"}), 400
    a = Article(title=title, content=content, user_id=current_user.id)
    db.session.add(a)
    db.session.commit()
    return jsonify({"ok": True, "id": a.id})


# -------- Reviews (authenticated) --------
@public_bp.get("/api/me/reviews")
def api_my_reviews_list():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    items = (Review.query
             .filter_by(author_id=current_user.id)
             .order_by(Review.created_at.desc())
             .all())
    return jsonify({
        "ok": True,
        "items": [
            {
                "id": r.id,
                "reviewer_name": r.reviewer_name,
                "rating": r.rating,
                "content": r.content,
                "created_at": r.created_at.isoformat(),
            } for r in items
        ]
    })


@public_bp.post("/api/me/reviews")
def api_my_reviews_create():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    reviewer_name = (data.get("reviewer_name") or "").strip() or "Аноним"
    try:
        rating = int(data.get("rating") or 0)
    except Exception:
        rating = 0
    content = (data.get("content") or "").strip()
    if rating < 1 or rating > 5 or not content:
        return jsonify({"ok": False, "error": "invalid_input"}), 400
    r = Review(author_id=current_user.id, reviewer_name=reviewer_name, rating=rating, content=content)
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True, "id": r.id})

@public_bp.post("/api/me/announcements")
def api_create_my_announcement():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    excerpt = (data.get("excerpt") or "").strip()
    category_id = data.get("category_id")
    tg_post_url = data.get("tg_post_url")
    # advanced fields
    price = float(data.get("price") or 0)
    is_per_month = bool(data.get("is_per_month") or False)
    address = (data.get("address") or "").strip() or None
    location_lat = data.get("location_lat")
    location_lng = data.get("location_lng")
    rooms = data.get("rooms")
    area = data.get("area")
    floor = data.get("floor")
    floors_total = data.get("floors_total")
    period_days = data.get("period_days")
    lease_term = (data.get("lease_term") or "").strip() or None
    images = data.get("images") or []
    draft = bool(data.get("draft") or False)
    subcategory = (data.get("subcategory") or "").strip() or None
    deal_type = (data.get("deal_type") or "").strip() or None
    district = (data.get("district") or "").strip() or None
    if not title:
        return jsonify({"ok": False, "error": "title_required"}), 400
    a = Announcement(
        title=title,
        content_excerpt=excerpt or "",
        category_id=category_id,
        tg_post_url=tg_post_url,
        user_id=current_user.id,
        price_cents=int(round(price * 100)),
        is_per_month=is_per_month,
        address=address,
        location_lat=float(location_lat) if location_lat is not None else None,
        location_lng=float(location_lng) if location_lng is not None else None,
        rooms=int(rooms) if rooms not in (None, "") else None,
        area=float(area) if area not in (None, "") else None,
        floor=int(floor) if floor not in (None, "") else None,
        floors_total=int(floors_total) if floors_total not in (None, "") else None,
        period_days=int(period_days) if period_days not in (None, "") else None,
        lease_term=lease_term,
        images_json=json.dumps(images) if images else None,
        draft=draft,
        subcategory=subcategory,
        deal_type=deal_type,
        district=district,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"ok": True, "id": a.id})


@public_bp.post("/api/upload")
def api_upload_file():
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "no_file"}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({"ok": False, "error": "empty_name"}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return jsonify({"ok": False, "error": "bad_ext"}), 400
    fname = secrets.token_hex(8) + ext
    path = os.path.join(UPLOAD_DIR, fname)
    f.save(path)
    url = f"/uploads/{fname}"
    return jsonify({"ok": True, "url": url})


@public_bp.get('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# -------- Public Articles --------
@public_bp.get("/api/articles/<int:aid>")
def api_public_article(aid: int):
    a = Article.query.get_or_404(aid)
    # Hide drafts from non-admins
    if a.is_draft and not (current_user.is_authenticated and getattr(current_user, 'is_admin', False)):
        abort(404)
    author = User.query.get(a.user_id) if a.user_id else None
    # Metrics and rating
    from sqlalchemy import func
    rating_avg = None
    rating_count = 0
    articles_count = 0
    total_views = 0
    if author:
        try:
            rating_avg = db.session.query(func.avg(Review.rating)).filter(Review.author_id == author.id).scalar()
            rating_count = db.session.query(func.count(Review.id)).filter(Review.author_id == author.id).scalar() or 0
            articles_count = Article.query.filter_by(user_id=author.id, is_draft=False).count()
            total_views = db.session.query(func.coalesce(func.sum(Article.views), 0)).filter(Article.user_id==author.id, Article.is_draft==False).scalar() or 0
        except Exception:
            pass
    return jsonify({
        "ok": True,
        "item": {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "cover_url": a.cover_url or "",
            "tags": (json.loads(a.tags_json) if a.tags_json else []),
            "seo_title": a.seo_title or "",
            "seo_description": a.seo_description or "",
            "og_image_url": a.og_image_url or "",
            "created_at": a.created_at.isoformat(),
            "is_draft": bool(a.is_draft),
            "category": a.category or "",
            "views": int(a.views or 0),
            "author": {"id": author.id, "username": author.username, "avatar_url": author.avatar_url or ""} if author else None,
            "author_rating": {"avg": float(rating_avg) if rating_avg is not None else None, "count": int(rating_count)},
            "author_metrics": {"articles": int(articles_count), "total_views": int(total_views)}
        }
    })

@public_bp.post("/api/auth/logout")
def api_logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({"ok": True})


@public_bp.get("/api/auth/me")
def api_me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False}), 200
    # rating stats
    try:
        ratings = [rv.rating for rv in Review.query.filter_by(author_id=current_user.id).all()]
        rating_count = len(ratings)
        rating_avg = round(sum(ratings)/rating_count, 2) if rating_count else 0
    except Exception:
        rating_count, rating_avg = 0, 0
    return jsonify({
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "balance": round((current_user.balance_cents or 0) / 100, 2),
            "avatar_url": current_user.avatar_url or "",
            "bio": current_user.bio or "",
            "rating_avg": rating_avg,
            "rating_count": rating_count,
            "is_admin": bool(getattr(current_user, 'is_admin', False))
        }
    })


@public_bp.post("/api/auth/register")
def api_register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "error": "missing_credentials"}), 400
    if len(username) < 3 or len(password) < 6:
        return jsonify({"ok": False, "error": "weak_credentials"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"ok": False, "error": "user_exists"}), 409
    user = User(username=username, is_admin=False, balance_cents=0)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"ok": True, "user": {
        "id": user.id,
        "username": user.username,
        "balance": round((user.balance_cents or 0) / 100, 2)
    }})
