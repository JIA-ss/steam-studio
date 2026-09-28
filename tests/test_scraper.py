import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

TOOL = Path(__file__).resolve().parents[1] / 'skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py'
spec = importlib.util.spec_from_file_location('scraper', TOOL)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def app(free=False, coming=False, price=None):
    result = {'name': 'Example', 'type': 'game', 'is_free': free,
              'release_date': {'date': 'Coming soon' if coming else '1 Jan, 2026', 'coming_soon': coming},
              'platforms': {'windows': True, 'mac': False, 'linux': True}}
    if price is not None:
        result['price_overview'] = price
    return result


def reviews(total=10):
    return {'success': 1, 'query_summary': {'total_positive': total, 'total_negative': 0,
                                         'total_reviews': total, 'review_score': 7,
                                         'review_score_desc': 'Positive'}}


class FakeClient:
    def __init__(self, *payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def get(self, url, params):
        self.calls.append((url, params))
        value = next(self.payloads)
        if isinstance(value, Exception):
            raise value
        return value


class FakeResponse:
    def __init__(self, status=200, data=None, headers=None):
        self.status_code = status
        self.data = data
        self.headers = headers or {}

    def __bool__(self):
        return self.status_code < 400

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.headers = {}
        self.count = 0

    def get(self, *args, **kwargs):
        self.count += 1
        r = next(self.responses)
        if isinstance(r, Exception):
            raise r
        return r


class ScraperTests(unittest.TestCase):
    def test_missing_price_not_free_or_zero(self):
        row = s.ParseSteamGame(app())
        self.assertFalse(row['is_free'])
        self.assertIsNone(row['price_final_minor'])
        self.assertIsNone(row['currency'])

    def test_locale_price_uses_integer_units(self):
        row = s.ParseSteamGame(app(price={'final': 123456, 'initial': 200000,
                                          'currency': 'EUR', 'final_formatted': '1.234,56€'}))
        self.assertEqual(row['price_final_minor'], 123456)
        self.assertEqual(row['currency'], 'EUR')

    def test_upcoming_and_country_retained(self):
        client = FakeClient({'12': {'success': True, 'data': app(coming=True)}}, reviews(0))
        with tempfile.TemporaryDirectory() as tmp:
            row, result = s.fetch_record(client, 12, 'cn', 'schinese', False, Path(tmp))
            self.assertEqual(result['status'], 'ok')
            self.assertTrue(row['coming_soon'])
            self.assertEqual(row['release_date'], 'Coming soon')
            self.assertEqual(row['review_summary']['total_reviews'], 0)
            self.assertEqual(client.calls[0][1]['cc'], 'cn')
            self.assertEqual(client.calls[0][1]['l'], 'schinese')
            self.assertTrue((Path(tmp) / '12.steam_store.json').exists())

    def test_spy_failure_is_partial_not_zero(self):
        client = FakeClient({'12': {'success': True, 'data': app()}}, reviews(), s.FetchError('http_503'))
        with tempfile.TemporaryDirectory() as tmp:
            row, result = s.fetch_record(client, 12, 'us', 'english', True, Path(tmp))
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(row['steamspy'])
        self.assertIsNone(row['tags'])
        self.assertEqual(row['review_summary']['total_reviews'], 10)

    def test_retry_is_bounded_and_handles_falsey_429(self):
        session = FakeSession([FakeResponse(429), FakeResponse(503), FakeResponse(503)])
        delays = []
        client = s.Client(retries=2, session=session, sleep=delays.append)
        with self.assertRaisesRegex(s.FetchError, 'http_503'):
            client.get('https://example.test')
        self.assertEqual(session.count, 3)
        self.assertIn(60, delays)

    def test_long_retry_after_stops(self):
        session = FakeSession([FakeResponse(429, headers={'Retry-After': '600'})])
        client = s.Client(session=session, sleep=lambda _: None)
        with self.assertRaisesRegex(s.FetchError, 'rate_limited_retry_later'):
            client.get('https://example.test')
        self.assertEqual(session.count, 1)

    def test_network_error_redacts_key(self):
        session = FakeSession([requests.ConnectionError('https://example.test?key=secret')])
        client = s.Client(retries=0, session=session)
        with self.assertRaises(s.FetchError) as caught:
            client.get('https://example.test', {'key': 'secret'})
        self.assertEqual(str(caught.exception), 'network_error')

    def test_catalog_pagination_and_no_key_in_output(self):
        client = FakeClient({'response': {'apps': [{'appid': 12}], 'have_more_results': True, 'last_appid': 12}},
                            {'response': {'apps': [{'appid': 20}], 'have_more_results': False}})
        result = s.catalog(client, 'secret')
        self.assertEqual([a['appid'] for a in result['apps']], [12, 20])
        self.assertEqual(client.calls[1][1]['last_appid'], 12)
        self.assertNotIn('secret', json.dumps(result))

    def test_catalog_cursor_loop_rejected(self):
        client = FakeClient({'response': {'apps': [], 'have_more_results': True, 'last_appid': 0}})
        with self.assertRaisesRegex(s.FetchError, 'cursor'):
            s.catalog(client, 'secret')

    def test_atomic_write_failure_preserves_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.json'
            s.save_json({'good': True}, path)
            with self.assertRaises(ValueError):
                s.save_json({'bad': float('nan')}, path)
            self.assertEqual(json.loads(path.read_text()), {'good': True})
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_partial_run_resume_retries_failed_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient({'12': {'success': True, 'data': app()}}, s.FetchError('http_503'))
            self.assertEqual(s.collect(client, [12], tmp), 2)
            self.assertEqual(json.loads((Path(tmp) / 'run.json').read_text())['status'], 'partial')
            client = FakeClient({'12': {'success': True, 'data': app()}}, reviews())
            self.assertEqual(s.collect(client, [12], tmp), 0)
            self.assertEqual(len(client.calls), 2)
            client = FakeClient()
            self.assertEqual(s.collect(client, [12], tmp), 0)
            self.assertEqual(client.calls, [])

    def test_failed_refresh_marks_old_snapshot_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = FakeClient({'12': {'success': True, 'data': app()}}, reviews())
            s.collect(good, [12], tmp)
            self.assertEqual(s.collect(FakeClient(s.FetchError('http_503')), [12], tmp, refresh=True), 2)
            row = json.loads((Path(tmp) / 'games.json').read_text())['12']
            self.assertEqual(row['status'], 'stale')
            self.assertEqual(row['name'], 'Example')

    def test_missing_catalog_key_fails_without_network(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(s.main(['--catalog-only']), 2)

    def test_dlc_is_explicitly_excluded(self):
        value = app()
        value['type'] = 'dlc'
        with tempfile.TemporaryDirectory() as tmp:
            row, result = s.fetch_record(FakeClient({'12': {'success': True, 'data': value}}),
                                         12, 'us', 'english', False, Path(tmp))
        self.assertIsNone(row)
        self.assertEqual(result['status'], 'excluded')

    def test_inconsistent_review_totals_are_not_accepted(self):
        value = reviews()
        value['query_summary']['total_reviews'] = 20
        with tempfile.TemporaryDirectory() as tmp:
            row, result = s.fetch_record(FakeClient({'12': {'success': True, 'data': app()}}, value),
                                         12, 'us', 'english', False, Path(tmp))
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(row['review_summary'])

    def test_interrupt_has_terminal_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(s, 'fetch_record', side_effect=KeyboardInterrupt):
                self.assertEqual(s.collect(FakeClient(), [12], tmp), 130)
            self.assertEqual(json.loads((Path(tmp) / 'run.json').read_text())['status'], 'interrupted')


if __name__ == '__main__':
    unittest.main()
