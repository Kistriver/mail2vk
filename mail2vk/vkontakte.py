import vk
import logging
import requests

__author__ = 'Alexey Kachalov <kachalov@kistriver.com>'

logger = logging.getLogger('mail2vk')


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
        if 'error' in res_json.keys():
            raise Exception(res_json['error'])
        file_cred = res_json['file']
        ats = self.api.docs.save(file=file_cred, title=file_name)[0]
        return ats
