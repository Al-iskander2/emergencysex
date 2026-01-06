import uuid
import json
import math
from datetime import date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q

from emerg_database.models import SessionUser, Photo, Match, Like, Block, Report


# -----------------------------
# Helpers
# -----------------------------

def get_session_user(request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return None
    try:
        return SessionUser.objects.get(session_id=session_id)
    except SessionUser.DoesNotExist:
        return None


def is_age_verified(user: SessionUser) -> bool:
    return bool(getattr(user, "age_verified_at", None))


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two points on Earth (km)."""
    r = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def expire_match_if_needed(match: Match) -> Match:
    if match.status in ("cancelled", "expired"):
        return match
    if timezone.now() > match.expires_at:
        match.status = "expired"
        match.save(update_fields=["status"])
    return match


def assign_host_guest(u1: SessionUser, u2: SessionUser):
    """Returns (host, guest). If impossible (both travel), returns (None, None)."""
    # Hard constraints first
    if u1.role == "host" and u2.role in ("travel", "either"):
        return u1, u2
    if u2.role == "host" and u1.role in ("travel", "either"):
        return u2, u1

    if u1.role == "travel" and u2.role in ("host", "either"):
        return u2, u1
    if u2.role == "travel" and u1.role in ("host", "either"):
        return u1, u2

    # Soft fallback: both either or both host -> pick a deterministic host
    if (u1.role, u2.role) in (("either", "either"), ("host", "host")):
        return (u1, u2) if u1.created_at <= u2.created_at else (u2, u1)

    # If one is either and other is host/travel, prefer the non-either role
    if u1.role == "either" and u2.role in ("host", "travel"):
        return (u2, u1) if u2.role == "host" else (u1, u2)  # if u2 travel, u1 hosts
    if u2.role == "either" and u1.role in ("host", "travel"):
        return (u1, u2) if u1.role == "host" else (u2, u1)

    # Both travel: no host available
    if u1.role == "travel" and u2.role == "travel":
        return None, None

    # Final deterministic fallback
    return (u1, u2) if u1.created_at <= u2.created_at else (u2, u1)


def _blocked_ids_for(user: SessionUser):
    ids1 = Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    ids2 = Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    return set(list(ids1) + list(ids2))


# -----------------------------
# API
# -----------------------------

@csrf_exempt
def init_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    session_id = request.headers.get("X-Session-ID")
    if session_id:
        user, _ = SessionUser.objects.get_or_create(session_id=session_id)
    else:
        session_id = str(uuid.uuid4())
        user = SessionUser.objects.create(session_id=session_id)

    return JsonResponse(
        {
            "session_id": user.session_id,
            "age_verified": is_age_verified(user),
            "has_photo": user.photos.exists(),
            "gender": user.gender,
            "looking_for": user.looking_for,
            "role": user.role,
            "radius": user.radius,
        }
    )


@csrf_exempt
def verify_age(request):
    """Robust (non-checkbox) 18+ gate: user must submit DOB; server validates age >= 18."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        payload = json.loads(request.body or "{}")
        dob_str = payload.get("dob")  # YYYY-MM-DD
        if not dob_str or len(dob_str) != 10:
            return JsonResponse({"error": "Invalid DOB"}, status=400)
        y, m, d = [int(x) for x in dob_str.split("-")]
        dob = date(y, m, d)

        today = timezone.now().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            return JsonResponse({"error": "Must be 18+"}, status=403)

        user.age_verified_at = timezone.now()
        user.save(update_fields=["age_verified_at"])
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)


@csrf_exempt
def update_profile(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    # Photo upload (multipart/form-data)
    if "photo" in request.FILES:
        Photo.objects.create(user=user, image=request.FILES["photo"])

    # Preferences
    data = request.POST
    if "gender" in data:
        user.gender = data["gender"]
    if "looking_for" in data:
        user.looking_for = data["looking_for"]
    if "role" in data:
        user.role = data["role"]
    if "radius" in data:
        try:
            user.radius = int(data["radius"])
        except ValueError:
            pass

    user.save()
    return JsonResponse({"status": "ok"})


@csrf_exempt
def update_location(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    try:
        data = json.loads(request.body or "{}")
        user.lat = data.get("lat")
        user.lon = data.get("lon")
        user.save(update_fields=["lat", "lon"])
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)


def search_candidates(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    # Require location for distance-based search
    if user.lat is None or user.lon is None:
        return JsonResponse({"error": "Location required"}, status=400)

    # Base queryset
    candidates = SessionUser.objects.exclude(id=user.id)

    # Safety: block list
    blocked_ids = _blocked_ids_for(user)
    if blocked_ids:
        candidates = candidates.exclude(id__in=list(blocked_ids))

    # Exclude users without photos
    candidates = candidates.filter(photos__isnull=False).distinct()

    # Mutual preference filtering (simple MVP)
    if user.looking_for and user.looking_for != "trans":
        candidates = candidates.filter(gender=user.looking_for)

    # Candidate must also be compatible with my gender (treat 'trans' as "no hard filter" for MVP)
    if user.gender:
        candidates = candidates.filter(
            Q(looking_for="") | Q(looking_for__isnull=True) | Q(looking_for="trans") | Q(looking_for=user.gender)
        )

    # Role compatibility
    if user.role == "host":
        candidates = candidates.filter(role__in=["travel", "either"])
    elif user.role == "travel":
        candidates = candidates.filter(role__in=["host", "either"])

    # Exclude already liked
    liked_ids = Like.objects.filter(from_user=user).values_list("to_user_id", flat=True)
    candidates = candidates.exclude(id__in=liked_ids)

    # Distance filter: take recent active sample, then filter in Python
    radius_km = int(user.radius or 10)
    if radius_km <= 0:
        # Interpret "0 km" as "very close" for usability (walkable)
        radius_km = 1

    sample = (
        candidates.filter(lat__isnull=False, lon__isnull=False)
        .order_by("-last_active")[:200]
    )

    ranked = []
    for c in sample:
        try:
            d = haversine_km(user.lat, user.lon, c.lat, c.lon)
            if d <= radius_km:
                ranked.append((d, c))
        except Exception:
            continue

    ranked.sort(key=lambda t: t[0])
    ranked = ranked[:20]

    results = []
    for dist, c in ranked:
        photo = c.photos.first()
        results.append(
            {
                "id": c.id,
                "photo_url": photo.image.url if photo else "",
                "distance_km": round(dist, 1),
            }
        )

    return JsonResponse({"candidates": results})


@csrf_exempt
def like_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    try:
        data = json.loads(request.body or "{}")
        target_id = (data.get("user_id") or data.get("target_id"))
        target_user = SessionUser.objects.get(id=target_id)

        # Blocked?
        if target_user.id in _blocked_ids_for(user):
            return JsonResponse({"error": "Not allowed"}, status=403)

        Like.objects.get_or_create(from_user=user, to_user=target_user)

        # Mutual like -> match
        if Like.objects.filter(from_user=target_user, to_user=user).exists():
            match = Match.objects.create(user1=user, user2=target_user, status="matched")
            return JsonResponse({"match": True, "match_id": match.id})

        return JsonResponse({"match": False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def poll_status(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    match = (
        Match.objects.filter(Q(user1=user) | Q(user2=user), status__in=["matched", "confirmed"])
        .order_by("-created_at")
        .first()
    )

    if not match:
        return JsonResponse({"match_found": False})

    match = expire_match_if_needed(match)

    other_user = match.user2 if match.user1 == user else match.user1
    photo = other_user.photos.first()

    i_confirmed = match.user1_confirmed if match.user1 == user else match.user2_confirmed
    they_confirmed = match.user2_confirmed if match.user1 == user else match.user1_confirmed

    host, guest = assign_host_guest(match.user1, match.user2)
    my_role = "host" if host and user.id == host.id else ("guest" if guest and user.id == guest.id else None)

    # Only reveal destination to the guest, and only after both confirmed.
    location = None
    maps_url = None
    if match.status == "confirmed" and host and guest and my_role == "guest":
        if host.lat is not None and host.lon is not None:
            location = {"lat": host.lat, "lon": host.lon}
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={host.lat},{host.lon}"

    return JsonResponse(
        {
            "match_found": True,
            "match_id": match.id,
            "status": match.status,
            "expires_at": match.expires_at.isoformat(),
            "other_user": {
                "photo_url": photo.image.url if photo else "",
                "gender": other_user.gender,
            },
            "i_confirmed": i_confirmed,
            "they_confirmed": they_confirmed,
            "my_role": my_role,
            "location": location,
            "maps_url": maps_url,
        }
    )


@csrf_exempt
def confirm_match(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    try:
        data = json.loads(request.body or "{}")
        match_id = data.get("match_id")
        match = Match.objects.get(id=match_id)

        match = expire_match_if_needed(match)
        if match.status == "expired":
            return JsonResponse({"error": "Match expired"}, status=410)
        if match.status == "cancelled":
            return JsonResponse({"error": "Match cancelled"}, status=410)

        if match.user1 == user:
            match.user1_confirmed = True
        elif match.user2 == user:
            match.user2_confirmed = True
        else:
            return JsonResponse({"error": "Not your match"}, status=403)

        # When both confirmed, ensure we can assign host/guest.
        if match.user1_confirmed and match.user2_confirmed:
            host, guest = assign_host_guest(match.user1, match.user2)
            if not host or not guest:
                match.status = "cancelled"
                match.save(update_fields=["status", "user1_confirmed", "user2_confirmed"])
                return JsonResponse({"error": "No host available (both chose travel)."}, status=409)
            match.status = "confirmed"

        match.save()
        return JsonResponse({"status": "ok", "match_status": match.status})
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)


@csrf_exempt
def cancel_match(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body or "{}")
        match_id = data.get("match_id")
        match = Match.objects.get(id=match_id)

        if match.user1 == user or match.user2 == user:
            match.status = "cancelled"
            match.save(update_fields=["status"])
            return JsonResponse({"status": "ok"})
        return JsonResponse({"error": "Not your match"}, status=403)
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)


@csrf_exempt
def block_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    try:
        data = json.loads(request.body or "{}")
        target_id = data.get("user_id")
        reason = (data.get("reason") or "")[:200]
        target = SessionUser.objects.get(id=target_id)

        Block.objects.get_or_create(blocker=user, blocked=target, defaults={"reason": reason})

        # Safety: cancel any active match between them
        Match.objects.filter(
            Q(user1=user, user2=target) | Q(user1=target, user2=user),
            status__in=["matched", "confirmed"],
        ).update(status="cancelled")

        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)


@csrf_exempt
def report_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user = get_session_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not is_age_verified(user):
        return JsonResponse({"error": "Age verification required"}, status=403)

    try:
        data = json.loads(request.body or "{}")
        target_id = data.get("user_id")
        reason = (data.get("reason") or "")[:200]
        details = (data.get("details") or "")[:2000]
        if not reason:
            return JsonResponse({"error": "Reason required"}, status=400)

        target = SessionUser.objects.get(id=target_id)
        Report.objects.create(reporter=user, reported=target, reason=reason, details=details)
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)


def mvp_index(request):
    return render(request, "mvp_index.html")
