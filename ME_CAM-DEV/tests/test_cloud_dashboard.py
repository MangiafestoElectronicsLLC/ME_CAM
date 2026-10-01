import io
import hashlib
import re
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from cloud_dashboard import create_app


class CloudDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-secret',
            'DATABASE': str(root / 'test.sqlite3'),
            'MEDIA_DIR': str(root / 'events'),
            'COOKIE_SECURE': False,
        })
        self.client = self.app.test_client()
        self.owner_setup()
        self.device_id, self.device_token = self.enroll_camera()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _csrf(self, response):
        match = re.search(rb'name="_csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def owner_setup(self):
        page = self.client.get('/setup')
        response = self.client.post('/setup', data={
            '_csrf_token': self._csrf(page),
            'username': 'owner',
            'password': 'correct-horse-battery-staple',
        })
        self.assertEqual(response.status_code, 302)

    def enroll_camera(self):
        page = self.client.get('/dashboard')
        response = self.client.post('/cameras', data={
            '_csrf_token': self._csrf(page),
            'name': 'Front door',
        }, follow_redirects=True)
        code_match = re.search(rb'<code>([^<]+)</code>', response.data)
        self.assertIsNotNone(code_match)
        code = code_match.group(1).decode()
        device_id = 'mecam-test-0001'
        result = self.client.post('/api/device/activate', json={
            'activation_code': code,
            'device_id': device_id,
            'camera_module': 'ov5647',
        })
        self.assertEqual(result.status_code, 200)
        return device_id, result.get_json()['device_token']

    def test_device_auth_required_and_activation(self):
        self.assertEqual(self.client.get('/api/device/status').status_code, 401)
        response = self.client.get('/api/device/status', headers={
            'Authorization': f'Bearer {self.device_token}',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['device_id'], self.device_id)
        self.assertTrue(response.get_json()['armed'])

    def test_health_check_and_case_sensitive_activation_code(self):
        health = self.client.get('/healthz')
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json(), {'ok': True})

        page = self.client.get('/dashboard')
        code = 'aB_cD-1234567890xyZ_efghijklmnop'
        with patch('cloud_dashboard.secrets.token_urlsafe', return_value=code):
            response = self.client.post('/cameras', data={
                '_csrf_token': self._csrf(page),
                'name': 'Case-sensitive code',
            }, follow_redirects=True)
        self.assertIn(f'<code>{code}</code>'.encode(), response.data)

        activated = self.client.post('/api/device/activate', json={
            'activation_code': code,
            'device_id': 'mecam-case-sensitive',
        })
        self.assertEqual(activated.status_code, 200)

    def test_armed_state_and_motion_clip_survive_as_cloud_event(self):
        upload = self.client.post('/api/motion/with-clip', headers={
            'Authorization': f'Bearer {self.device_token}',
        }, data={
            'video': (io.BytesIO(b'fake-mp4-content'), 'event.mp4', 'video/mp4'),
            'duration_seconds': '12',
            'has_audio': 'true',
            'device_id': self.device_id,
        }, content_type='multipart/form-data')
        self.assertEqual(upload.status_code, 201)
        event_id = upload.get_json()['event_id']
        with self.app.app_context():
            from cloud_dashboard import _db
            event = _db().execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
            self.assertEqual(event['duration_seconds'], 12)
            self.assertEqual(event['has_audio'], 1)
            stored = Path(self.app.config['MEDIA_DIR']) / event['filename']
            self.assertNotEqual(stored.read_bytes(), b'fake-mp4-content')
        playback = self.client.get(f'/events/{event_id}/clip')
        self.assertEqual(playback.status_code, 200)
        self.assertEqual(playback.data, b'fake-mp4-content')

        page = self.client.get('/dashboard')
        mode_form = re.search(
            rb'<form class="armed[^>]*method="post" action="([^"]+)"[^>]*>(.*?)</form>',
            page.data, re.S,
        )
        self.assertIsNotNone(mode_form)
        action = mode_form.group(1).decode()
        csrf = re.search(rb'name="_csrf_token" value="([^"]+)"', mode_form.group(2)).group(1).decode()
        mode = re.search(rb'name="mode" value="([^"]+)"', mode_form.group(2)).group(1).decode()
        result = self.client.post(action, data={'_csrf_token': csrf, 'mode': mode})
        self.assertEqual(result.status_code, 302)
        status = self.client.get('/api/device/status', headers={
            'Authorization': f'Bearer {self.device_token}',
        }).get_json()
        self.assertFalse(status['armed'])
        self.assertEqual(status['camera_mode'], 'standby')
        rejected = self.client.post('/api/motion/with-clip', headers={
            'Authorization': f'Bearer {self.device_token}',
        }, data={
            'video': (io.BytesIO(b'fake-mp4-content'), 'event.mp4', 'video/mp4'),
            'duration_seconds': '12',
            'device_id': self.device_id,
        }, content_type='multipart/form-data')
        self.assertEqual(rejected.status_code, 409)

    def test_authenticated_stream_frame_uses_agent_contract(self):
        stream = self.client.get('/camera/1/stream.mjpg', buffered=False)
        self.assertEqual(stream.status_code, 200)
        stream.close()
        response = self.client.post(f'/api/cameras/{self.device_id}/live-frame', headers={
            'Authorization': f'Bearer {self.device_token}',
            'Content-Type': 'image/jpeg',
        }, data=b'\xff\xd8jpeg\xff\xd9')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['stream_requested'])
        command = self.client.get(f'/api/cameras/{self.device_id}/stream-command?applied_mode=security', headers={
            'Authorization': f'Bearer {self.device_token}',
        })
        self.assertEqual(command.status_code, 200)
        self.assertTrue(command.get_json()['stream_requested'])
        self.assertEqual(command.get_json()['camera_mode'], 'security')
        self.assertIn('multipart/x-mixed-replace', stream.content_type)

    def test_event_history_keeps_latest_ten(self):
        headers = {'Authorization': f'Bearer {self.device_token}'}
        ids = []
        oldest_media = None
        for index in range(12):
            response = self.client.post('/api/motion/with-clip', headers=headers, data={
                'video': (io.BytesIO(f'clip-{index}'.encode()), f'event-{index}.mp4', 'video/mp4'),
                'duration_seconds': '8',
                'device_id': self.device_id,
            }, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 201)
            event_id = response.get_json()['event_id']
            ids.append(event_id)
            if index == 0:
                with self.app.app_context():
                    from cloud_dashboard import _db
                    row = _db().execute('SELECT filename FROM events WHERE id = ?', (event_id,)).fetchone()
                    oldest_media = Path(self.app.config['MEDIA_DIR']) / row['filename']
        history = self.client.get('/api/cameras/1/events')
        self.assertEqual(history.status_code, 200)
        events = history.get_json()['events']
        self.assertEqual(len(events), 10)
        self.assertEqual(events[0]['id'], ids[-1])
        self.assertNotIn(ids[0], [event['id'] for event in events])
        self.assertFalse(oldest_media.exists())
        with self.app.app_context():
            from cloud_dashboard import _db
            oldest = _db().execute('SELECT filename FROM events WHERE id = ?', (ids[0],)).fetchone()
            self.assertIsNone(oldest)

    def test_initial_owner_setup_key_is_enforced(self):
        root = Path(self.temp_dir.name) / 'keyed'
        with patch.dict('os.environ', {'MECAM_SETUP_KEY':'test-setup-secret'}):
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'test-secret',
                'DATABASE': str(root / 'keyed.sqlite3'),
                'MEDIA_DIR': str(root / 'events'),
                'COOKIE_SECURE': False,
            })
        client = app.test_client()
        page = client.get('/setup')
        csrf = self._csrf(page)
        response = client.post('/setup', data={
            '_csrf_token': csrf,
            'username': 'owner',
            'password': 'correct-horse-battery-staple',
            'setup_key': 'wrong-key',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid setup key', response.data)
        response = client.post('/setup', data={
            '_csrf_token': csrf,
            'username': 'owner',
            'password': 'correct-horse-battery-staple',
            'setup_key': 'test-setup-secret',
        })
        self.assertEqual(response.status_code, 302)

    def test_two_way_audio_transport(self):
        page = self.client.get('/dashboard')
        csrf = self._csrf(page)
        enabled = self.client.post('/camera/1/listen', data={
            '_csrf_token': csrf,
            'enabled': '1',
        })
        self.assertTrue(enabled.get_json()['listen_requested'])

        device_headers = {'Authorization': f'Bearer {self.device_token}'}
        queue = self.client.get('/api/cameras/1/speak-queue', headers=device_headers)
        self.assertTrue(queue.get_json()['listen_requested'])

        pcm = b'\x01\x00' * 100
        uploaded = self.client.post(
            f'/api/cameras/{self.device_id}/listen-chunk',
            headers={**device_headers, 'Content-Type':'audio/pcm;rate=16000;ch=1;fmt=s16le'},
            data=pcm,
        )
        self.assertEqual(uploaded.status_code, 200)
        self.assertTrue(uploaded.get_json()['listen_requested'])
        heard = self.client.get('/api/cameras/1/listen-audio?after=0')
        self.assertEqual(len(heard.get_json()['chunks']), 1)
        self.assertEqual(heard.get_json()['chunks'][0]['sample_rate'], 16000)

        talk = self.client.post('/api/cameras/1/speak', headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'audio/webm',
        }, data=b'talk-audio')
        self.assertEqual(talk.status_code, 202)
        speaker_queue = self.client.get('/api/cameras/1/speak-queue', headers=device_headers)
        self.assertTrue(speaker_queue.get_json()['has_audio'])
        self.assertEqual(speaker_queue.get_json()['content_type'], 'audio/webm')

    def test_wifi_update_is_encrypted_and_delivered_to_pi(self):
        page = self.client.get('/config')
        queued = self.client.post('/config/wifi', data={
            '_csrf_token': self._csrf(page),
            'device_id': '1',
            'ssid': 'HomeNet',
            'wifi_password': 'test-wifi-password',
        })
        self.assertEqual(queued.status_code, 302)
        with self.app.app_context():
            from cloud_dashboard import _db
            row = _db().execute('SELECT * FROM wifi_changes WHERE device_id = 1').fetchone()
            self.assertNotIn(b'test-wifi-password', row['password_cipher'])
            change_id = row['change_id']

        headers = {'Authorization': f'Bearer {self.device_token}'}
        command = self.client.get(
            f'/api/cameras/{self.device_id}/stream-command', headers=headers)
        self.assertEqual(command.status_code, 200)
        self.assertEqual(command.get_json()['wifi_change_id'], change_id)
        self.assertEqual(command.get_json()['wifi_ssid'], 'HomeNet')
        self.assertEqual(command.get_json()['wifi_password'], 'test-wifi-password')

        reported = self.client.post('/api/device/status', headers=headers, json={
            'wifi_change_id': change_id,
            'wifi_change_result': 'rolled_back',
            'wifi_change_reason': 'target_unreachable',
        })
        self.assertEqual(reported.status_code, 200)
        final = self.client.get('/api/device/status', headers=headers).get_json()
        self.assertEqual(final['wifi_change_result'], 'rolled_back')
        self.assertNotIn('wifi_password', final)

    def test_temporary_share_expires_and_can_be_revoked(self):
        page = self.client.get('/dashboard')
        created = self.client.post('/cameras/1/share', data={
            '_csrf_token': self._csrf(page),
            'hours': '1',
        }, follow_redirects=True)
        match = re.search(rb'href="(http://[^\"]+/share/[^\"]+)"', created.data)
        self.assertIsNotNone(match)
        from urllib.parse import urlparse
        share_url = urlparse(match.group(1).decode())
        shared = self.client.get(share_url.path)
        self.assertEqual(shared.status_code, 200)
        self.assertIn(b'Temporary access expires', shared.data)

        owner_page = self.client.get('/dashboard')
        revoked = self.client.post('/cameras/1/share/revoke', data={
            '_csrf_token': self._csrf(owner_page),
        })
        self.assertEqual(revoked.status_code, 302)
        self.assertEqual(self.client.get(share_url.path).status_code, 404)

        owner_page = self.client.get('/dashboard')
        second = self.client.post('/cameras/1/share', data={
            '_csrf_token': self._csrf(owner_page),
            'hours': '1',
        }, follow_redirects=True)
        second_match = re.search(rb'href="(http://[^\"]+/share/[^\"]+)"', second.data)
        self.assertIsNotNone(second_match)
        expired_url = urlparse(second_match.group(1).decode())

        with self.app.app_context():
            from cloud_dashboard import _db
            _db().execute(
                'UPDATE shares SET expires_at = 0 WHERE token_hash = ?',
                (hashlib.sha256(expired_url.path.rsplit('/', 1)[-1].encode()).hexdigest(),),
            )
            _db().commit()
        self.assertEqual(self.client.get(expired_url.path).status_code, 404)

    def test_owner_can_change_password(self):
        page = self.client.get('/account')
        response = self.client.post('/account', data={
            '_csrf_token': self._csrf(page),
            'current_password': 'correct-horse-battery-staple',
            'new_password': 'new-correct-horse-battery',
        })
        self.assertEqual(response.status_code, 302)
        self.client.post('/logout', data={
            '_csrf_token': self._csrf(self.client.get('/dashboard')),
        })
        login_page = self.client.get('/login')
        rejected = self.client.post('/login', data={
            '_csrf_token': self._csrf(login_page),
            'username': 'owner',
            'password': 'correct-horse-battery-staple',
        })
        self.assertEqual(rejected.status_code, 200)
        login_page = self.client.get('/login')
        accepted = self.client.post('/login', data={
            '_csrf_token': self._csrf(login_page),
            'username': 'owner',
            'password': 'new-correct-horse-battery',
        })
        self.assertEqual(accepted.status_code, 302)

    def test_event_can_be_deleted_with_its_encrypted_file(self):
        uploaded = self.client.post('/api/motion/with-clip', headers={
            'Authorization': f'Bearer {self.device_token}',
        }, data={
            'video': (io.BytesIO(b'delete-me'), 'event.mp4', 'video/mp4'),
        }, content_type='multipart/form-data')
        event_id = uploaded.get_json()['event_id']
        with self.app.app_context():
            from cloud_dashboard import _db
            row = _db().execute('SELECT filename FROM events WHERE id = ?', (event_id,)).fetchone()
            media = Path(self.app.config['MEDIA_DIR']) / row['filename']
        events_page = self.client.get('/events')
        deleted = self.client.post(f'/events/{event_id}/delete', data={
            '_csrf_token': self._csrf(events_page),
        })
        self.assertEqual(deleted.status_code, 302)
        self.assertFalse(media.exists())
        self.assertEqual(self.client.get(f'/events/{event_id}/clip').status_code, 404)


if __name__ == '__main__':
    unittest.main()
