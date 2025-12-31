import uuid
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from budsi_database.models import SessionUser, Photo, Match, Like

# Helper to get session user
def get_session_user(request):
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return None
    try:
        return SessionUser.objects.get(session_id=session_id)
    except SessionUser.DoesNotExist:
        return None

@csrf_exempt
def init_session(request):
    if request.method == 'POST':
        session_id = request.headers.get('X-Session-ID')
        if session_id:
            user, created = SessionUser.objects.get_or_create(session_id=session_id)
        else:
            session_id = str(uuid.uuid4())
            user = SessionUser.objects.create(session_id=session_id)
        
        return JsonResponse({
            'session_id': user.session_id,
            'has_photo': user.photos.exists(),
            'gender': user.gender,
            'looking_for': user.looking_for,
            'role': user.role,
            'radius': user.radius
        })
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def update_profile(request):
    if request.method == 'POST':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # Handle photo upload
        if 'photo' in request.FILES:
            Photo.objects.create(user=user, image=request.FILES['photo'])
        
        # Handle preferences
        data = request.POST
        if 'gender' in data: user.gender = data['gender']
        if 'looking_for' in data: user.looking_for = data['looking_for']
        if 'role' in data: user.role = data['role']
        if 'radius' in data: user.radius = int(data['radius'])
        
        user.save()
        
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def update_location(request):
    if request.method == 'POST':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        try:
            data = json.loads(request.body)
            user.lat = data.get('lat')
            user.lon = data.get('lon')
            user.save()
            return JsonResponse({'status': 'ok'})
        except:
            return JsonResponse({'error': 'Invalid data'}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def search_candidates(request):
    if request.method == 'GET':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # Basic filtering logic
        candidates = SessionUser.objects.exclude(id=user.id)
        
        # Filter by looking_for
        if user.looking_for != 'trans': # If looking for trans, logic might be specific, assuming 'trans' is a gender option? 
            # If user is looking for X, candidate gender must be X
            # AND candidate must be looking for user's gender
            candidates = candidates.filter(gender=user.looking_for)
        
        # Filter by role (host/travel)
        if user.role == 'host':
            candidates = candidates.filter(role__in=['travel', 'either'])
        elif user.role == 'travel':
            candidates = candidates.filter(role__in=['host', 'either'])
        
        # Exclude already liked/matched
        liked_ids = Like.objects.filter(from_user=user).values_list('to_user_id', flat=True)
        candidates = candidates.exclude(id__in=liked_ids)
        
        # Exclude users without photos
        candidates = candidates.filter(photos__isnull=False).distinct()

        # TODO: Distance filtering using lat/lon (simple approximation for MVP)
        # For MVP, just return top 10 recent active users
        candidates = candidates.order_by('-last_active')[:10]
        
        results = []
        for c in candidates:
            photo = c.photos.first()
            results.append({
                'id': c.session_id,
                'gender': c.gender,
                'role': c.role,
                'photo_url': photo.image.url if photo else '',
                'distance': '5km' # Mock distance for MVP
            })
            
        return JsonResponse({'candidates': results})
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def like_user(request):
    if request.method == 'POST':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        try:
            data = json.loads(request.body)
            target_id = data.get('target_id')
            target_user = SessionUser.objects.get(session_id=target_id)
            
            # Create Like
            Like.objects.get_or_create(from_user=user, to_user=target_user)
            
            # Check for Match
            # If target_user already liked user
            if Like.objects.filter(from_user=target_user, to_user=user).exists():
                # Create Match
                match = Match.objects.create(user1=user, user2=target_user, status='matched')
                return JsonResponse({'match': True, 'match_id': match.id})
            
            return JsonResponse({'match': False})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def poll_status(request):
    if request.method == 'GET':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # Check for active matches
        match = Match.objects.filter(
            Q(user1=user) | Q(user2=user),
            status__in=['matched', 'confirmed']
        ).first()
        
        if match:
            other_user = match.user2 if match.user1 == user else match.user1
            photo = other_user.photos.first()
            
            # Check confirmation status
            i_confirmed = match.user1_confirmed if match.user1 == user else match.user2_confirmed
            they_confirmed = match.user2_confirmed if match.user1 == user else match.user1_confirmed
            
            return JsonResponse({
                'match_found': True,
                'match_id': match.id,
                'status': match.status,
                'other_user': {
                    'gender': other_user.gender,
                    'photo_url': photo.image.url if photo else ''
                },
                'i_confirmed': i_confirmed,
                'they_confirmed': they_confirmed,
                'location': {'lat': other_user.lat, 'lon': other_user.lon} if match.status == 'confirmed' else None
            })
            
        return JsonResponse({'match_found': False})
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def confirm_match(request):
    if request.method == 'POST':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        try:
            data = json.loads(request.body)
            match_id = data.get('match_id')
            match = Match.objects.get(id=match_id)
            
            if match.user1 == user:
                match.user1_confirmed = True
            elif match.user2 == user:
                match.user2_confirmed = True
            else:
                return JsonResponse({'error': 'Not your match'}, status=403)
            
            if match.user1_confirmed and match.user2_confirmed:
                match.status = 'confirmed'
            
            match.save()
            return JsonResponse({'status': 'ok'})
        except:
            return JsonResponse({'error': 'Invalid data'}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def cancel_match(request):
    if request.method == 'POST':
        user = get_session_user(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        try:
            data = json.loads(request.body)
            match_id = data.get('match_id')
            match = Match.objects.get(id=match_id)
            
            if match.user1 == user or match.user2 == user:
                match.status = 'cancelled'
                match.save()
                return JsonResponse({'status': 'ok'})
            return JsonResponse({'error': 'Not your match'}, status=403)
        except:
            return JsonResponse({'error': 'Invalid data'}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

def mvp_index(request):
    return render(request, 'budsidesk_app/mvp_index.html')
