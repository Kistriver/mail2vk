import imaplib
import email
import logging

__author__ = 'Alexey Kachalov <kachalov@kistriver.com>'

logger = logging.getLogger('mail2vk')


class Mail(object):
    _login = None
    _pwd = None
    _srv = None
    _port = None
    _con = None

    def __init__(self, login, password, server=None, port=None):
        self._login = login
        self._pwd = password
        self._srv = 'imap.yandex.ru' if server is None else server
        self._port = '993' if port is None else port

    def __enter__(self):
        self._con = imaplib.IMAP4_SSL(self._srv, self._port)
        typ, _ = self._con.login(self._login, self._pwd)
        if typ != 'OK':
            raise
        typ, _ = self._con.select('INBOX')
        if typ != 'OK':
            raise
        return self

    def __exit__(self, type, value, traceback):
        self._con.close()
        self._con.logout()
        self._con = None

    def _decode_header(self, mail_obj, header):
        header_data = mail_obj.get(header)
        if header_data is None:
            return None
        h = email.header.decode_header(header_data)
        return h[0][0].decode(h[0][1]) if h[0][1] else h[0][0]

    def messages(self, *fltrs):
        if not len(fltrs):
            fltrs += ('(UNSEEN)',)

        typ, unseen = self._con.status('INBOX', '(UNSEEN)')
        if typ != 'OK':
            raise
        logger.info('(%s) new messages' %
                    unseen[0].decode('utf-8')[len('INBOX (UNSEEN '):-1])

        typ, data = self._con.uid('SEARCH', None, *fltrs)
        if typ != 'OK':
            raise
        for uid in data[0].split():
            yield uid.decode('utf-8')

    def fetch(self, uid):
        typ, message_parts = self._con.uid('FETCH', uid, '(RFC822)')
        if typ != 'OK':
            raise
        mail = email.message_from_bytes(message_parts[0][1])
        self.unseen(uid)

        msg = []
        msg_html = []
        ats = {}
        ats_types = {}
        if mail.is_multipart():
            for part in mail.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain':
                    msg.append(part.get_payload(decode=True))
                elif ctype == 'text/html':
                    msg_html.append(part.get_payload(decode=True))
                elif part.get_filename() is not None:
                    ats_types[part.get_filename()] = ctype
                    ats.setdefault(part.get_filename(), [])
                    ats[part.get_filename()].append(part.get_payload(
                        decode=True))

        msg, msg_html = map(
            lambda x: b''.join(x).decode('utf-8'),
            [msg, msg_html]
        )

        for file_name, data in ats.items():
            ats[file_name] = b''.join(data)

        data = {
            'uid': uid,
            'msg': msg,
            'msg_html': msg_html,
            'date': self._decode_header(mail, 'Date'),
            'from': self._decode_header(mail, 'From'),
            'email': self._decode_header(mail, 'Envelope-From'),
            'subject': self._decode_header(mail, 'Subject'),
            'attachments': ats,
            'attachments_types': ats_types,
        }
        logger.info(
            '%(subject)s [%(from)s <%(email)s>] %(date)s' % data)
        return data

    def _flag(self, mid, flag, yes=None):
        yes = True if yes is None else bool(yes)
        typ, data = self._con.uid(
            'STORE', mid, '%sFLAGS' % ('+' if yes else '-'), flag)
        if typ != 'OK':
            raise Exception(typ)
        return data

    def seen(self, uid):
        return self._flag(uid, '\\SEEN', True)

    def unseen(self, uid):
        return self._flag(uid, '\\SEEN', False)
