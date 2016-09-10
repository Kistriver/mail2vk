import vk
import imaplib
import os
import email
import logging
import sys
import zipstream
import requests

__author__ = 'Alexey Kachalov <kachalov@kistriver.com>'

logger = logging.getLogger('mail2vk')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


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
        for i in data[0].split():
            typ, message_parts = self._con.uid('FETCH', i, '(RFC822)')
            if typ != 'OK':
                raise
            mail = email.message_from_bytes(message_parts[0][1])
            self.unseen(i)

            ats = []
            z = zipstream.ZipFile()
            for part in mail.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                file_name = part.get_filename()

                if bool(file_name):
                    ats.append(file_name)
                    z.writestr(file_name, part.get_payload(decode=True))

            msg_parts = [
                (part.get_filename(), part.get_payload(decode=True))
                for part in mail.walk()
                if part.get_content_type() in ['text/plain', 'text/html']
            ]
            msg = []
            for name, data in msg_parts:
                msg.append(data.decode('utf-8'))
            data = {
                'id': i,
                'msg': ''.join(msg),
                'date': self._decode_header(mail, 'Date'),
                'from': self._decode_header(mail, 'From'),
                'email': self._decode_header(mail, 'Envelope-From'),
                'subject': self._decode_header(mail, 'Subject'),
                'attachments': z,
                'attachments_list': ats,
            }
            logger.info('%(subject)s [%(from)s <%(email)s>] %(date)s' % data)
            yield data

    def _flag(self, mid, flag, yes=None):
        yes = True if yes is None else bool(yes)
        typ, data = self._con.uid(
            'STORE', mid, '%sFLAGS' % ('+' if yes else '-'), flag)
        if typ != 'OK':
            raise Exception(typ)
        return data

    def seen(self, mid):
        return self._flag(mid, '\\SEEN', True)

    def unseen(self, mid):
        return self._flag(mid, '\\SEEN', False)


class Vk(object):
    _app_id = None
    _login = None
    _pwd = None
    _session = None
    _api = None

    def __init__(self, app_id, login, password):
        self._app_id = app_id
        self._login = login
        self._pwd = password

    def __enter__(self):
        self._session = vk.AuthSession(
            app_id=self._app_id,
            user_login=self._login,
            user_password=self._pwd,
            scope='offline,messages,docs',
        )
        self._api = vk.API(self._session)
        return self

    def __exit__(self, type, value, traceback):
        self._session = None
        self._api = None

    @property
    def api(self):
        return self._api

    def upload_file(self, file_name, file_content):
        try:
            cs = self.api.docs.getUploadServer()['upload_url']
        except KeyError as e:
            logger.exception(e)
            raise e
        res = requests.post(
            cs,
            files={
                'file': (file_name, file_content),
            }
        )
        res_json = res.json()
        try:
            file_cred = res_json['file']
        except KeyError as e:
            logger.exception(res_json)
            raise e
        ats = self.api.docs.save(file=file_cred, title=file_name)[0]
        return ats


def main():
    e_login = os.environ.get('EMAIL_LOGIN', None)
    e_password = os.environ.get('EMAIL_PASSWORD', None)

    vk_login = os.environ.get('VK_LOGIN', None)
    vk_password = os.environ.get('VK_PASSWORD', None)
    vk_reciever = os.environ.get('VK_RECIEVER', None)
    vk_app_id = os.environ.get('VK_APP_ID', None)

    mail = Mail(e_login, e_password)
    vk = Vk(vk_app_id, vk_login, vk_password)
    with mail as m, vk as vk:
        try:
            for msg in m.messages():
                msg.update({
                    'ats': ', '.join(msg['attachments_list']),
                    'ats_count': len(msg['attachments_list']),
                })

                ats = vk.upload_file(
                    'attachments.zip',
                    b''.join(list(msg['attachments'])),
                ) if msg['ats_count'] else None
                res = vk.api.messages.send(
                    message='''From: %(from)s <%(email)s>
Subject: %(subject)s
Date: %(date)s
Attachments (%(ats_count)i): %(ats)s
==============
%(msg)s''' % msg,
                    chat_id=vk_reciever,
                    attachment='doc%(owner_id)i_%(did)i' % ats
                    if msg['ats_count'] else None,
                )
                mail.seen(msg['id'])
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    main()
