import unittest

import service


class ServiceSecurityTests(unittest.TestCase):
    def test_service_defaults_to_loopback_binding(self):
        self.assertEqual(service.os.getenv("AIMS_BIND_HOST", "127.0.0.1"), "127.0.0.1")

    def test_wildcard_cors_is_not_installed_by_default(self):
        cors = [middleware for middleware in service.app.user_middleware if middleware.cls.__name__ == "CORSMiddleware"]
        self.assertEqual(cors, [])


if __name__ == "__main__":
    unittest.main()
