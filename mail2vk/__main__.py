from vk.exceptions import VkAPIError
import os
import email
import logging
import sys
import zipstream
import time

from mail2vk.mail import Mail
from mail2vk.vkontakte import Vk


__author__ = 'Alexey Kachalov <kachalov@kistriver.com>'

logger = logging.getLogger('mail2vk')
logger.setLevel(os.environ.get('LOGGER', logging.INFO))

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


message_str = '''From: %(from)s <%(email)s>
Subject: %(subject)s
Date: %(date)s
Attachments (%(ats_count)i): %(ats_keys)s
==============
%(msg_show)s'''


def main():
    e_login = os.environ.get('EMAIL_LOGIN', None)
    e_password = os.environ.get('EMAIL_PASSWORD', None)

    vk_login = os.environ.get('VK_LOGIN', None)
    vk_password = os.environ.get('VK_PASSWORD', None)
    vk_reciever = os.environ.get('VK_RECIEVER', None)
    vk_app_id = os.environ.get('VK_APP_ID', None)

    mail = Mail(e_login, e_password)
    vk_api = Vk(vk_app_id, vk_login, vk_password)
    with mail as mail, vk_api as vk_api:
        try:
            for uid in mail.messages():
                msg = mail.fetch(uid)
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
                    message=message_str % msg,
                    chat_id=vk_reciever,
                    attachment=','.join([
                        'doc%(owner_id)i_%(did)i' % doc
                        for doc in docs
                    ]) if msg['ats_count'] else None,
                )
                mail.seen(uid)
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    main()
