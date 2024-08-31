import unittest

import sys
if sys.version_info >= (3, 3):
    from unittest.mock import patch, MagicMock
else:
    from mock import patch, MagicMock

from domainconnectzone.sigutil import verify_sig, generate_sig, get_publickey


class TestVerifySig(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Hard-coded public key (for demonstration purposes)
        cls.public_key_pem = """-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAJj64Q9HqZTjD9lsgwvN9/pqW1iHvEhk7r467q2ya9uw2R3NmQv2rbiR
wPflwOG4FSHA9daI+q8a/fONb84kxl5ywL53NS08nWa5i8wu36sF3TyI8QLOwD/c
gSa29l1u3eUoM++bw+OLbhOqYyzpa2QGRS53RY5xxw7fikcNLWLjAgMBwAE=
-----END RSA PUBLIC KEY-----"""

        # Hard-coded valid signature for known data "test data"
        cls.valid_signature = (b"AQ73+ixnVP9PdO6KRIRA1Rk1ihLaiMNtFW5b8C9gAjiZMcOM1Q9bJt"
                               b"/v63RUbEiow7YZN5cZuNDVxM0SLmQigk78PZZzv4bVNfYAUkhugPywQLyBZmFz/fEYg8pqKxq/9kerNWuNqf"
                               b"/KXbUDUgvZp0/X/kdkR9BabwuvL07vl04=")
        cls.data = "test data"

    def test_verify_correct_signature(self):
        # Test with correct, hard-coded signature
        self.assertTrue(verify_sig(self.public_key_pem, self.valid_signature, self.data))

    def test_verify_incorrect_signature(self):
        # Test with incorrect signature
        incorrect_signature = "incorrect_signature_here"  # Replace with an incorrect signature
        self.assertFalse(verify_sig(self.public_key_pem, incorrect_signature, self.data))

    def test_verify_incorrect_data(self):
        # Test with incorrect data
        incorrect_data = "wrong data"
        self.assertFalse(verify_sig(self.public_key_pem, self.valid_signature, incorrect_data))

    def test_exception_handling(self):
        # Test the function's exception handling with invalid public key
        self.assertFalse(verify_sig("invalid public key", self.valid_signature, self.data))


class TestGenerateSig(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Hard-coded private key
        cls.private_key_pem = """-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQCY+uEPR6mU4w/ZbIMLzff6altYh7xIZO6+Ou6tsmvbsNkdzZkL
9q24kcD35cDhuBUhwPXWiPqvGv3zjW/OJMZecsC+dzUtPJ1muYvMLt+rBd08iPEC
zsA/3IEmtvZdbt3lKDPvm8Pji24TqmMs6WtkBkUud0WOcccO34pHDS1i4wIDAcAB
AoGAO3y380H42KpXv5JA9TtuNKCGG0eECOD4Rvu7v4vmB2hVf5kggpCo5KAj/vWy
qN/J+gohpS2Yei1oU4uLt60P57vPEjyTHhCuZL34o5CPxw6DCQeUs9yBxm0srI+E
38YL63gMmNyMaSW4yVn5B5BSWeOZMkGD201jJjtinKBu8G0CQQDWAf49eBuN/L3Z
75tZO/ctUgllKTK/yd2AmOyCnVBTJ6bMdyDPl8fbZr0lVeQ1DVyVO1gTCfo8nn9K
2iOICdD9AkEAtv9Y6Nchqrp/HrOqC2j6/3gRknBxC60kpNVTpiZ6o0uftDwPT8rg
fTFqjrkqWkDUpThY8UgcbW5WYnzr8Cq5XwJBALFwMIShO5Nha5hmmVqTOFRIhmQr
3IES+FmoBZjdLUOqmjanBDxTayOcv81UQSE5wIrrJDdv4hw3Ux56FAEpVTUCQCXE
9jd0MF7AlFsrIfm4mnI3sIUz+hveBina7VqqsL0kxM1HwBSYhoGcQYRTEbJQ45DD
IoLPv/UGCVIB6sXAsrMCQQCpxSaJxnwcKhrz/TxEAuj3PwUupyrgOY/kX53mSndh
d9tBSVfC0sLpdQ0rhswJaG72Gh3UEcbmGkexARQ5Mzu2
-----END RSA PRIVATE KEY-----
"""

        # Hard-coded expected signature for known data "test data"
        cls.expected_signature = (b"AQ73+ixnVP9PdO6KRIRA1Rk1ihLaiMNtFW5b8C9gAjiZMcOM1Q9bJt"
                                  b"/v63RUbEiow7YZN5cZuNDVxM0SLmQigk78PZZzv4bVNfYAUkhugPywQLyBZmFz/fEYg8pqKxq"
                                  b"/9kerNWuNqf/KXbUDUgvZp0/X/kdkR9BabwuvL07vl04=")

    def test_generate_signature(self):
        # Test signature generation
        data = "test data"
        generated_sig = generate_sig(self.private_key_pem, data)

        # Compare the generated signature with the hard-coded expected signature
        self.assertEqual(generated_sig, self.expected_signature)

    def test_exception_handling(self):
        # Test the function's exception handling with an invalid private key
        with self.assertRaises(ValueError):
            generate_sig("invalid private key", "data")


class TestGetPublicKey(unittest.TestCase):

    @patch('dns.resolver.query')
    def test_get_publickey(self, mock_query):
        # Mock DNS TXT records
        mock_records = MagicMock()
        record1 = MagicMock()
        record1.strings = [b'p=0,d=MIIBIjANBg']
        record2 = MagicMock()
        record2.strings = [b'p=1,d=kqG9w0BAQEFAAOCAQ8AMIIBCgKCAQE']
        mock_records.__iter__.return_value = [record1, record2]
        mock_query.return_value = mock_records

        # Test get_publickey function
        domain = 'example.com'
        expected_key = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqG9w0BAQEFAAOCAQ8AMIIBCgKCAQE\n-----END PUBLIC KEY-----\n'
        self.assertEqual(get_publickey(domain), expected_key)

    @patch('dns.resolver.query')
    def test_get_publickey_full_spec(self, mock_query):
        # Mock DNS TXT records with fully specified algorithm and type
        mock_records = MagicMock()
        record1 = MagicMock()
        record1.strings = [b'a=RS256,t=x509,p=0,d=MIIBIjANBg']
        record2 = MagicMock()
        record2.strings = [b'a=RS256,t=x509,p=1,d=kqG9w0BAQEFAAOCAQ8AMIIBCgKCAQE']
        record3 = MagicMock()
        record3.strings = [b'p=2']
        mock_records.__iter__.return_value = [record1, record2, record3]
        mock_query.return_value = mock_records

        # Test get_publickey function with fully specified parameters
        domain = 'example.com'
        expected_key = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqG9w0BAQEFAAOCAQ8AMIIBCgKCAQE\n-----END PUBLIC KEY-----\n'
        self.assertEqual(get_publickey(domain), expected_key)

    @patch('dns.resolver.query')
    def test_get_publickey_with_invalid_data(self, mock_query):
        # Mock DNS TXT record with invalid data
        mock_records = MagicMock()
        record = MagicMock()
        record.strings = [b'a=invalid']
        mock_records.__iter__.return_value = [record]
        mock_query.return_value = mock_records

        # Test get_publickey function with invalid data
        domain = 'example.com'
        self.assertIsNone(get_publickey(domain))

    @patch('dns.resolver.query')
    def test_get_publickey_with_invalid_algorithm(self, mock_query):
        # Mock DNS TXT record with unsupported algorithm
        mock_records = MagicMock()
        record = MagicMock()
        record.strings = [b'a=unsupported_algo,d=MIIBIjANBg']
        mock_records.__iter__.return_value = [record]
        mock_query.return_value = mock_records

        # Test get_publickey function with invalid algorithm
        domain = 'example.com'
        self.assertIsNone(get_publickey(domain))

    @patch('dns.resolver.query')
    def test_get_publickey_with_invalid_type(self, mock_query):
        # Mock DNS TXT record with unsupported type
        mock_records = MagicMock()
        record = MagicMock()
        record.strings = [b't=unsupported_type,d=MIIBIjANBg']
        mock_records.__iter__.return_value = [record]
        mock_query.return_value = mock_records

        # Test get_publickey function with invalid type
        domain = 'example.com'
        self.assertIsNone(get_publickey(domain))