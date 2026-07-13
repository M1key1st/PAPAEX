from flask import Blueprint, abort, jsonify, request

from app.extensions import limiter
from app.services import interaction_service, title_service
from app.utils.security import get_client_ip, get_voter_key, hash_ip

api_bp = Blueprint("api", __name__)


@api_bp.route("/vote/<int:title_id>", methods=["POST"])
@limiter.limit("30 per minute")
def vote(title_id):
    title = title_service.get_by_id(title_id)
    if title is None:
        abort(404)

    data = request.get_json(silent=True) or {}
    value = data.get("value")
    if value not in (1, -1):
        return jsonify({"ok": False, "error": "Noto'g'ri qiymat."}), 400

    voter_key = get_voter_key()
    ip_hash = hash_ip(get_client_ip())
    result = interaction_service.cast_vote(title_id, voter_key, ip_hash, value)

    updated = title_service.get_by_id(title_id)
    return jsonify({
        "ok": True,
        "vote": result,
        "likes": updated["likes_count"],
        "dislikes": updated["dislikes_count"],
    })


@api_bp.route("/bookmark/<int:title_id>", methods=["POST"])
@limiter.limit("60 per minute")
def bookmark(title_id):
    title = title_service.get_by_id(title_id)
    if title is None:
        abort(404)

    voter_key = get_voter_key()
    bookmarked = interaction_service.toggle_bookmark(title_id, voter_key)
    return jsonify({"ok": True, "bookmarked": bookmarked})
