import unittest2
from mock import patch

from mail2vk.vkontakte import Vk


class VkCase(unittest2.TestCase):
    def setUp(self):
    	self.vk = Vk(1234, "user", "pass")

    def test_init(self):
    	self.assertEqual(self.vk._app_id, 1234)
    	self.assertEqual(self.vk._login, "user")
    	self.assertEqual(self.vk._pwd, "pass")
    	self.assertEqual(self.vk._session, None)
    	self.assertEqual(self.vk._api, None)

    def test_empty_arguments(self):
    	with self.assertRaises(TypeError):
    		x = Vk()

    def test_api(self):
    	self.vk._api = object()
    	self.assertEqual(self.vk.api, self.vk._api)


if __name__ == '__main__':
    unittest2.main()
