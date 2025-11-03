from flask import Blueprint, jsonify, request, abort
from .extensions import db
from .models import Announcement, Category, Article

admin_bp = Blueprint("admin", __name__)

# NOTE: Упрощённые endpoins для первичного наполнения (без auth, добавим позже)

@admin_bp.post("/admin/announcements")
def admin_create_announcement():
    data = request.get_json(force=True)
    title = data.get("title")
    if not title:
        abort(400, "title is required")
    a = Announcement(
        title=title,
        content_excerpt=data.get("excerpt", ""),
        category_id=data.get("category_id"),
        tg_post_url=data.get("tg_post_url"),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"id": a.id}), 201


@admin_bp.post("/admin/categories")
def admin_create_category():
    data = request.get_json(force=True)
    name = data.get("name")
    slug = data.get("slug")
    if not name or not slug:
        abort(400, "name and slug are required")
    c = Category(name=name, slug=slug)
    db.session.add(c)
    db.session.commit()
    return jsonify({"id": c.id}), 201


@admin_bp.post("/admin/articles")
def admin_create_article():
    data = request.get_json(force=True)
    title = data.get("title")
    content = data.get("content")
    if not title or not content:
        abort(400, "title and content are required")
    art = Article(title=title, content=content)
    db.session.add(art)
    db.session.commit()
    return jsonify({"id": art.id}), 201
