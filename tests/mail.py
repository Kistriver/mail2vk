import unittest2
from mock import patch
import imaplib

from mail2vk.mail import Mail


class MailCase(unittest2.TestCase):
    def setUp(self):
        self.mail = Mail('test@example.com', 'pass')

    def test_params1(self):
        self.assertEqual(self.mail._login, 'test@example.com')
        self.assertEqual(self.mail._pwd, 'pass')
        self.assertEqual(self.mail._srv, 'imap.yandex.ru')
        self.assertEqual(self.mail._port, '993')

    def test_params2(self):
        self.mail = Mail('t2@example.com', 'pass2', 'imap.example.com', '228')
        self.assertEqual(self.mail._login, 't2@example.com')
        self.assertEqual(self.mail._pwd, 'pass2')
        self.assertEqual(self.mail._srv, 'imap.example.com')
        self.assertEqual(self.mail._port, '228')

    @patch('imaplib.IMAP4_SSL')
    def test_connection(self, imap_mock):
        imap_instance = imap_mock.return_value
        imap_instance.login.return_value = ('OK',)
        imap_instance.select.return_value = ('OK',)
        self.assertEqual(self.mail.__enter__(), self.mail)
        self.mail.__exit__(None, None, None)
        self.assertIsNone(self.mail._con)

    @patch('imaplib.IMAP4_SSL')
    def test_connection_auth_failed(self, imap_mock):
        imap_instance = imap_mock.return_value
        imap_instance.login.side_effect = imaplib.IMAP4.error('')
        self.assertRaises(imaplib.IMAP4.error, self.mail.__enter__)

    def test_response_empty(self):
        self.assertIsNone(self.mail._response(()))

    def test_response_ok(self):
        self.assertTupleEqual(self.mail._response(('OK', )), ())

    def test_response_failed(self):
        self.assertRaises(Exception, self.mail._response, ('FAILED', ))

    def test_response_data(self):
        self.assertEqual(self.mail._response(('OK', 'test'))[0], 'test')
        self.assertTupleEqual(self.mail._response(
            ('OK', 't1', 't2')), ('t1', 't2'))

if __name__ == '__main__':
    unittest2.main()
