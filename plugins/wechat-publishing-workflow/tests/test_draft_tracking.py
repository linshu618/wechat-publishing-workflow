from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(os.environ.get('WECHAT_TEST_SKILLS', str(Path(__file__).resolve().parents[1] / 'skills')))

def load_publisher():
    spec = importlib.util.spec_from_file_location('tracking_test', ROOT / 'wechat-draft-publisher/scripts/wechat_draft.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class DraftTrackingTests(unittest.TestCase):
    def setUp(self):
        self.p = load_publisher()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.article = self.root / 'article.html'
        self.drafts = {}
        self.requests = []
        self.fail_get = False
        self.lose_add_response = False
        self.reject_add = False
        self.reject_update = False
        self.update_without_confirmation = False
        self.fields = dict(title='Title', content='<p>Original</p>', cover_bytes=b'cover', cover_mime='image/png', cover_extension='png')
        for patch in (
            mock.patch.object(self.p, 'CONFIG_ROOT', self.root / 'config'),
            mock.patch.object(self.p, 'resolve_credentials', side_effect=lambda appid='', secret='': (appid or 'account-a', 'secret')),
            mock.patch.object(self.p, 'get_access_token', return_value='token'),
            mock.patch.object(self.p, 'upload_article_images', side_effect=lambda appid, token, content: content),
            mock.patch.object(self.p, 'upload_image', return_value={'media_id': 'cover-id'}),
            mock.patch.object(self.p, '_request_json', side_effect=self.request),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def request(self, url, **kwargs):
        operation = url.split('/draft/')[1].split('?')[0]
        payload = json.loads(kwargs['body'])
        self.requests.append((operation, payload))
        if operation == 'add':
            if self.reject_add:
                raise self.p.WeChatApiError('invalid content', 45166)
            media_id = f'draft-{len(self.drafts)+1}'
            self.drafts[media_id] = copy.deepcopy(payload['articles'])
            if self.lose_add_response:
                raise self.p.WeChatApiError('response lost')
            return {'media_id': media_id}
        if operation == 'get':
            if self.fail_get:
                raise self.p.WeChatApiError('network unavailable')
            if payload['media_id'] not in self.drafts:
                raise self.p.WeChatApiError('invalid media id', 40007)
            return {'news_item': copy.deepcopy(self.drafts[payload['media_id']])}
        if operation == 'update':
            self.assertEqual(payload['index'], 0)
            if self.reject_update:
                raise self.p.WeChatApiError('invalid content', 45166)
            self.drafts[payload['media_id']] = [copy.deepcopy(payload['articles'])]
            return {} if self.update_without_confirmation else {'errcode': 0, 'errmsg': 'ok'}
        raise AssertionError(operation)

    def save(self, **changes):
        return self.p.publish_draft(article_path=self.article, **{**self.fields, **changes})

    def count(self, operation):
        return sum(op == operation for op, _ in self.requests)

    def test_repeat_click_does_not_create_or_upload_again(self):
        first = self.save()
        second = self.save()
        self.assertEqual(first['mediaId'], second['mediaId'])
        self.assertEqual(second['action'], 'unchanged')
        self.assertEqual(self.count('add'), 1)
        self.assertEqual(self.count('update'), 0)
        self.assertEqual(self.p.upload_image.call_count, 1)

    def test_edit_updates_same_id_and_persists_association(self):
        first = self.save()
        second = self.save(content='<p>Edited</p>')
        self.assertEqual(second['action'], 'updated')
        self.assertEqual(first['mediaId'], second['mediaId'])
        self.assertEqual(self.count('add'), 1)
        self.assertEqual(self.drafts[first['mediaId']][0]['content'], '<p>Edited</p>')
        record = json.loads(self.p._draft_state_path('account-a', self.article).read_text())
        self.assertEqual(record['mediaId'], first['mediaId'])
        self.assertEqual(record['status'], 'verified')
        self.assertNotIn('secret', json.dumps(record))
        self.assertNotIn('<p>', json.dumps(record))

    def test_backend_changes_stop_before_upload(self):
        result = self.save()
        self.drafts[result['mediaId']][0]['content'] = 'changed in backend'
        with self.assertRaisesRegex(ValueError, '后台草稿已发生变化（正文）'):
            self.save(content='local edit')
        self.assertEqual(self.count('update'), 0)
        self.assertEqual(self.p.upload_image.call_count, 1)

    def test_backend_changes_during_upload_stop_update(self):
        result = self.save()
        def upload(*args):
            self.drafts[result['mediaId']][0]['title'] = 'concurrent edit'
            return {'media_id': 'cover-id'}
        self.p.upload_image.side_effect = upload
        with self.assertRaisesRegex(ValueError, '准备上传期间后台草稿发生变化'):
            self.save(content='local edit')
        self.assertEqual(self.count('update'), 0)

    def test_deleted_draft_is_not_silently_recreated(self):
        result = self.save()
        del self.drafts[result['mediaId']]
        with self.assertRaises(self.p.WeChatApiError):
            self.save(content='edit')
        self.assertEqual(self.count('add'), 1)

    def test_explicit_existing_draft_is_updated_without_add(self):
        self.drafts['legacy'] = [{'title': 'Old', 'content': 'old content'}]
        result = self.save(existing_media_id='legacy')
        self.assertEqual(result['mediaId'], 'legacy')
        self.assertEqual(result['action'], 'updated')
        self.assertEqual(self.count('add'), 0)

    def test_account_and_article_paths_are_isolated(self):
        self.save()
        self.save(appid='account-b')
        self.p.publish_draft(article_path=self.root / 'other.html', **self.fields)
        self.assertEqual(self.count('add'), 3)

    def test_temporary_urls_do_not_cause_conflicts(self):
        result = self.save()
        self.drafts[result['mediaId']][0]['url'] = 'https://example.test/temporary'
        self.assertEqual(self.save()['action'], 'unchanged')

    def test_multi_article_draft_cannot_be_overwritten(self):
        self.drafts['multi'] = [{'title': 'one'}, {'title': 'two'}]
        with self.assertRaisesRegex(ValueError, '不是单篇文章'):
            self.save(existing_media_id='multi')
        self.assertEqual(self.count('update'), 0)

    def test_uncertain_create_does_not_retry_add(self):
        self.lose_add_response = True
        with self.assertRaises(self.p.WeChatApiError):
            self.save()
        self.lose_add_response = False
        with self.assertRaisesRegex(ValueError, '上次提交结果未确认'):
            self.save()
        self.assertEqual(self.count('add'), 1)
        self.assertEqual(self.save(existing_media_id='draft-1')['action'], 'updated')
        self.assertEqual(self.count('add'), 1)

    def test_confirmed_create_rejection_is_retryable(self):
        self.reject_add = True
        with self.assertRaises(self.p.WeChatApiError):
            self.save()
        self.reject_add = False
        self.assertEqual(self.save()['action'], 'created')
        self.assertEqual(len(self.drafts), 1)

    def test_confirmed_update_rejection_retains_original_record(self):
        original = self.save()
        self.reject_update = True
        with self.assertRaises(self.p.WeChatApiError):
            self.save(content='edit')
        self.reject_update = False
        self.assertEqual(self.save(content='edit')['mediaId'], original['mediaId'])
        self.assertEqual(self.count('add'), 1)

    def test_post_create_read_failure_keeps_known_id(self):
        self.fail_get = True
        result = self.save()
        self.assertIn('warning', result)
        self.fail_get = False
        with self.assertRaisesRegex(ValueError, '未完成内容校验'):
            self.save()
        self.assertEqual(self.count('add'), 1)

    def test_malformed_state_stops_new_creation(self):
        path = self.p._draft_state_path('account-a', self.article)
        path.parent.mkdir(parents=True)
        path.write_text('invalid json')
        with self.assertRaisesRegex(ValueError, '关联记录无法读取'):
            self.save()
        self.assertEqual(self.count('add'), 0)

    def test_lock_rejects_concurrent_save_and_releases_afterwards(self):
        path = self.p._draft_state_path('account-a', self.article)
        with self.p._draft_lock(path):
            with self.assertRaisesRegex(ValueError, '正在保存草稿'):
                self.save()
        self.assertEqual(self.save()['action'], 'created')

    def test_missing_update_acknowledgement_does_not_report_success(self):
        self.save()
        self.update_without_confirmation = True
        with self.assertRaisesRegex(self.p.WeChatApiError, '未确认草稿更新'):
            self.save(content='edit')
        with self.assertRaisesRegex(ValueError, '结果未确认'):
            self.save(content='edit')
        self.assertEqual(self.count('add'), 1)

if __name__ == '__main__':
    unittest.main()
