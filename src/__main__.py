import vk
from vk.exceptions import VkAPIError
import imaplib
import os
import email
import logging
import sys
import zipstream
import requests
import time

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
                'id': i,
                'msg': msg,
                'msg_html': msg_html,
                'date': self._decode_header(mail, 'Date'),
                'from': self._decode_header(mail, 'From'),
                'email': self._decode_header(mail, 'Envelope-From'),
                'subject': self._decode_header(mail, 'Subject'),
                'attachments': ats,
                'attachments_types': ats_types,
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
                    'ats_keys': ', '.join(msg['attachments'].keys()),
                    'ats_count': len(msg['attachments']),
                    'msg_show':
                    msg['msg'] if len(msg['msg']) else msg['msg_html'],
                })

                docs = []
                z = zipstream.ZipFile()
                for file_name, file_data in msg['attachments'].items():
                    z.writestr(file_name, file_data)

                try:
                    doc = vk.upload_file(
                        'mail2vk_attachments.zip',
                        b''.join(list(z)),
                    )
                    docs.append(doc)
                    time.sleep(5)
                except:
                    logger.exception(
                        'Can\'t upload file: mail2vk_attachments.zip')

                for file_name, file_data in msg['attachments'].items():
                    try:
                        doc = vk.upload_file(
                            file_name,
                            file_data,
                        )
                        docs.append(doc)
                        time.sleep(5)
                    except VkAPIError as e:
                        vk.api.messages.send(message='''
Can't upload file: %(file_name)s
Captcha required: %(captcha)s''' % {
                            'captcha': e.captcha_img,
                            'file_name': file_name,
                        }, chat_id=vk_reciever)
                    except:
                        logger.exception('Can\'t upload file: %s' % file_name)
                res = vk.api.messages.send(
                    message='''From: %(from)s <%(email)s>
Subject: %(subject)s
Date: %(date)s
Attachments (%(ats_count)i): %(ats_keys)s
==============
%(msg_show)s''' % msg,
                    chat_id=vk_reciever,
                    attachment=','.join([
                        'doc%(owner_id)i_%(did)i' % doc
                        for doc in docs
                    ]) if msg['ats_count'] else None,
                )
                mail.seen(msg['id'])
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    main()
