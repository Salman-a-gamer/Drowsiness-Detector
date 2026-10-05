import unittest
from drowsy_guard.identity import clean_name, name_context
from drowsy_guard.speech import resolve_phrase


class IdentityTests(unittest.TestCase):
    def test_name_only_when_enabled_and_present(self):
        settings = dict(user_name='Alex', personalization_enabled=False)
        self.assertEqual(name_context(settings), {})
        self.assertIsNone(resolve_phrase('{name}, wake up.', name_context(settings)))
        settings['personalization_enabled'] = True
        self.assertEqual(resolve_phrase('{name}, wake up.', name_context(settings)), 'Alex, wake up.')
        settings['user_name'] = ''
        self.assertEqual(name_context(settings), {})

    def test_name_is_bounded_and_cannot_inject_placeholders(self):
        self.assertEqual(clean_name('  A{lex}\n '), 'Alex')
        self.assertEqual(len(clean_name('x' * 100)), 24)
