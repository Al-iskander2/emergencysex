from django.test import TestCase, Client
from emerg_database.models import SessionUser, Match, Like
from django.core.files.uploadedfile import SimpleUploadedFile

class MVPTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1_id = "user1"
        self.user2_id = "user2"
        
        # Create users via API
        self.client.post('/api/mvp/init/', HTTP_X_SESSION_ID=self.user1_id)
        self.client.post('/api/mvp/init/', HTTP_X_SESSION_ID=self.user2_id)
        
        self.user1 = SessionUser.objects.get(session_id=self.user1_id)
        self.user2 = SessionUser.objects.get(session_id=self.user2_id)
        
        # Set prefs
        self.user1.gender = 'man'
        self.user1.looking_for = 'female'
        self.user1.save()
        
        self.user2.gender = 'female'
        self.user2.looking_for = 'man'
        self.user2.save()

    def test_like_and_match(self):
        # User 1 likes User 2
        res = self.client.post('/api/mvp/like/', 
                               data={'target_id': self.user2_id}, 
                               content_type='application/json',
                               HTTP_X_SESSION_ID=self.user1_id)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['match'])
        
        # User 2 likes User 1 -> MATCH
        res = self.client.post('/api/mvp/like/', 
                               data={'target_id': self.user1_id}, 
                               content_type='application/json',
                               HTTP_X_SESSION_ID=self.user2_id)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['match'])
        
        match_id = res.json()['match_id']
        match = Match.objects.get(id=match_id)
        self.assertEqual(match.status, 'matched')

    def test_confirmation(self):
        # Create match
        match = Match.objects.create(user1=self.user1, user2=self.user2, status='matched')
        
        # User 1 confirms
        self.client.post('/api/mvp/confirm/', 
                         data={'match_id': match.id}, 
                         content_type='application/json',
                         HTTP_X_SESSION_ID=self.user1_id)
        
        match.refresh_from_db()
        self.assertTrue(match.user1_confirmed)
        self.assertFalse(match.user2_confirmed)
        self.assertEqual(match.status, 'matched')
        
        # User 2 confirms
        self.client.post('/api/mvp/confirm/', 
                         data={'match_id': match.id}, 
                         content_type='application/json',
                         HTTP_X_SESSION_ID=self.user2_id)
        
        match.refresh_from_db()
        self.assertTrue(match.user2_confirmed)
        self.assertEqual(match.status, 'confirmed')

