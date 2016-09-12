import unittest2
from mock import patch, Mock
import imaplib

from mail2vk.mail import Mail


class MailCase(unittest2.TestCase):
    def setUp(self):
        self.mail = Mail('test@example.com', 'pass')

    def test_params(self):
        self.assertEqual(self.mail._login, 'test@example.com')
        self.assertEqual(self.mail._pwd, 'pass')
        self.assertEqual(self.mail._srv, 'imap.yandex.ru')
        self.assertEqual(self.mail._port, '993')

    def test_params_with_imap_server(self):
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
        self.assertEqual(self.mail._response(('OK', 't1')), 't1')
        self.assertTupleEqual(self.mail._response(
            ('OK', 't1', 't2')), ('t1', 't2'))

    def test_decode_header_not_exists(self):
        mail_obj = Mock()
        mail_obj.get.return_value = None
        self.assertEqual(self.mail._decode_header(mail_obj, 'No-Header'), None)

    @patch('email.header')
    def test_decode_header(self, email_header):
        mail_obj = Mock()
        mail_obj.get.return_value = ''

        email_header.decode_header.side_effect = (
            [('data', None)],
            [('data'.encode('iso-8859-1'), 'iso-8859-1')],
        )
        self.assertEqual(self.mail._decode_header(mail_obj, 'H1'), 'data')
        self.assertEqual(self.mail._decode_header(mail_obj, 'H2'), 'data')

    def test_messages_no_filters_ok(self):
        self.mail._con = Mock()
        self.mail._con.status.return_value = 'OK', [b'INBOX (UNSEEN 3)']
        self.mail._con.uid.return_value = 'OK', [b'1 2 3']
        self.assertTupleEqual(tuple(self.mail.messages()), ('1', '2', '3'))

    def test_seen(self):
        self.mail._con = Mock()
        self.mail._con.uid.return_value = 'OK', []
        self.mail.seen('1')
        self.assertTupleEqual(
            self.mail._con.uid.call_args,
            ('STORE', '1', '+FLAGS', '\\SEEN'))

    def test_unseen(self):
        self.mail._con = Mock()
        self.mail._con.uid.return_value = 'OK', []
        self.mail.unseen('1')
        self.assertTupleEqual(
            self.mail._con.uid.call_args,
            ('STORE', '1', '-FLAGS', '\\SEEN'))


if __name__ == '__main__':
    unittest2.main()
