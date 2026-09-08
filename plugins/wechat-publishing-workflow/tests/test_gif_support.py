import base64
import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / 'skills'
SKILLS = Path(os.environ.get('WECHAT_TEST_SKILLS', str(DEFAULT_ROOT)))
spec = importlib.util.spec_from_file_location('publisher_gif_tests', SKILLS / 'wechat-draft-publisher/scripts/wechat_draft.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
GIF = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jB9kAAAAASUVORK5CYII=')

def data_image(raw, mime='image/gif'):
    return f'data:{mime};base64,' + base64.b64encode(raw).decode('ascii')

class GifSupportTests(unittest.TestCase):
    def test_gif_bytes_mime_and_extension_preserved(self):
        self.assertEqual(publisher.decode_data_image(data_image(GIF)), (GIF, 'image/gif', 'gif'))

    def test_gif_over_one_mb_never_enters_static_compression(self):
        raw = GIF + b'\0' * publisher.MAX_ARTICLE_IMAGE_BYTES
        with mock.patch.object(publisher, '_compress_article_image', side_effect=AssertionError('GIF flattened')):
            self.assertEqual(publisher.decode_data_image(data_image(raw)), (raw, 'image/gif', 'gif'))

    def test_gif87a_and_mislabeled_gif_are_routed_as_gif(self):
        raw = b'GIF87a' + GIF[6:]
        self.assertEqual(publisher.decode_data_image(data_image(raw, 'image/png')), (raw, 'image/gif', 'gif'))

    def test_invalid_gif_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'GIF 图片数据损坏'):
            publisher.decode_data_image(data_image(PNG))

    def test_gif_over_ten_mb_is_rejected_without_static_fallback(self):
        with mock.patch.object(publisher, 'MAX_ARTICLE_GIF_BYTES', len(GIF)-1):
            with self.assertRaisesRegex(ValueError, 'GIF 超过 10MB'):
                publisher.decode_data_image(data_image(GIF))

    def test_png_and_jpeg_behavior_unchanged(self):
        for raw, mime, extension in ((PNG, 'image/png', 'png'), (b'\xff\xd8\xfftest', 'image/jpeg', 'jpg')):
            with self.subTest(mime=mime):
                self.assertEqual(publisher.decode_data_image(data_image(raw, mime)), (raw, mime, extension))

    def test_gif_not_accepted_as_cover(self):
        with self.assertRaisesRegex(ValueError, '封面必须是 PNG 或 JPEG'):
            publisher.decode_cover_data(data_image(GIF))

    def test_mixed_images_use_correct_endpoints_and_keep_markup(self):
        gif_src, png_src = data_image(GIF), data_image(PNG, 'image/png')
        content = f'<p>before</p><img src="{gif_src}" alt="motion"><img src="{png_src}"><img src="{gif_src}"><p>after</p>'
        responses = [{'url': 'https://mmbiz.qpic.cn/gif/0', 'media_id': 'gif-id'}, {'url': 'https://mmbiz.qpic.cn/png/0'}]
        with mock.patch.object(publisher, 'upload_image', side_effect=responses) as upload:
            result = publisher.upload_article_images('test-account', 'test-token', content)
        self.assertEqual(upload.call_count, 2)
        gif_call, png_call = [call.args for call in upload.call_args_list]
        self.assertEqual(gif_call[1:3], (GIF, 'image/gif'))
        self.assertTrue(gif_call[3].endswith('.gif'))
        self.assertTrue(gif_call[4].endswith('/material/add_material?type=image'))
        self.assertTrue(png_call[4].endswith('/media/uploadimg'))
        self.assertEqual(result, content.replace(gif_src, responses[0]['url']).replace(png_src, responses[1]['url']))

    def test_existing_wechat_image_is_not_reuploaded(self):
        content = '<img src="https://mmbiz.qpic.cn/gif/0">'
        with mock.patch.object(publisher, 'upload_image') as upload:
            self.assertEqual(publisher.upload_article_images('a', 't', content), content)
            upload.assert_not_called()

    def test_missing_url_fails_instead_of_dropping_animation(self):
        with mock.patch.object(publisher, 'upload_image', return_value={'media_id': 'no-url'}):
            with self.assertRaisesRegex(publisher.WeChatApiError, '正文图片地址'):
                publisher.upload_article_images('a', 't', f'<img src="{data_image(GIF)}">')

    def test_gif_api_error_does_not_fallback_to_jpeg(self):
        with mock.patch.object(publisher, 'upload_image', side_effect=publisher.WeChatApiError('rejected', 40005)) as upload:
            with self.assertRaises(publisher.WeChatApiError):
                publisher.upload_article_images('a', 't', f'<img src="{data_image(GIF)}">')
            self.assertEqual(upload.call_count, 1)

if __name__ == '__main__':
    unittest.main()
