# coding=utf-8
"""
Python-specific API tests for the domainconnectzone library.

Data-driven protocol compliance tests (record processing, variable
substitution, conflict rules, etc.) live in compliance_tests.yaml and are
executed by test_compliance.py.  This file covers only tests that are
tightly coupled to the Python API surface:
  - DomainConnect constructor / loading behaviour
  - verify_sig / is_sig_required
  - prompt() (deprecated helper)
  - is_custom_record_type() and get_records_variables() (validator helpers)
"""
import os
import sys
import unittest

from domainconnectzone import *
from domainconnectzone.DomainConnectImpl import get_records_variables

if sys.version_info >= (3, 3):
    from unittest.mock import patch
else:
    from mock import patch


class DomainConnectTests(unittest.TestCase):
    def setUp(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_definitions', 'templates')

    def tearDown(self):
        pass

    # ------------------------------------------------------------------
    # Signature helpers (DNS-mocked; not suitable for language-agnostic YAML)
    # ------------------------------------------------------------------
    def _test_sig(self, title, provider_id, service_id, qs, sig, key, ignore_signature, expected):
        dc = DomainConnect(provider_id, service_id, self.template_dir)
        passed = False
        try:
            dc.verify_sig(qs, sig, key, ignore_signature)
            if expected:
                passed = True
        except InvalidSignature:
            if not expected:
                passed = True
        self.assertTrue(passed, title)

    def _test_sig_tests(self):
        sig = ('LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4'
               '+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl'
               '/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk'
               '/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw==')
        key = '_dck1'
        qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
        self._test_sig('Passed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False, True)

        sig = ('BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4'
               '+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl'
               '/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk'
               '/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw==')
        self._test_sig('Failed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False, False)

        self._test_sig('Missing Sig', 'exampleservice.domainconnect.org', 'template2', qs, None, None, False, False)

        self._test_sig('Ignore Sig', 'exampleservice.domainconnect.org', 'template2', None, None, None, True, True)

    # ------------------------------------------------------------------
    # Constructor / template loading
    # ------------------------------------------------------------------
    def test_DomainConnectClass_not_existing_template_default_dir(self):
        with self.assertRaises(InvalidTemplate):
            DomainConnect('foo', "bar")

    def test_DomainConnectClass_custom_template(self):
        dc = DomainConnect(None, None, template={"providerId": "foo", 'serviceId': "ser"})
        self.assertEqual(dc.data, {"providerId": "foo", 'serviceId': "ser"})

    def test_DomainConnectClass_verify_sig(self):
        dc = DomainConnect(None, None, template={"providerId": "foo", 'serviceId': "ser",
                                                 "syncPubKeyDomain": "exampleservice.domainconnect.org"})
        query_string = "a=1&b=2&ip=10.10.10.10&domain=foobar.com"
        signature = ("rxWqGP0qPPzaj+9zukKC/jZqz4ic7bHO62GyGlxqcnz6s9/tEPJccwJfku8jD9ofK3eTJpKJLTsYN00SN9qyx0YXVT8baPtkavMpT"
                     "+epcuDaUbcyXo270s7RQmwPAo0C8I1NLodGbzTUvTktwdgZPRT3Oda1Hyk7eFJetmocLv6iGICAsPkCf32C8EcQcxYjQ56ytINIn"
                     "FQwKOLuZr8g3AMNOVX73Qu3rnuB4Zl2BKOQi9dikzUxOyAsOLMUrWLbXthpwJ2cl5ek2QSg9KX+2WhEyQmaaJWveYVkYCRL1ckMk"
                     "q35pIq++RJI48CbTIQPPh2VdqZsUSu16fKztrt9pw==")
        key = "_dck1"
        dc.verify_sig(query_string, signature, key)

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(None, signature, key)
        self.assertEqual("Missing data for signature verification", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string, None, key)
        self.assertEqual("Missing data for signature verification", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string, signature, None)
        self.assertEqual("Missing data for signature verification", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string, signature, "_not_existing_key")
        self.assertEqual(
            "Unable to get public key for template/key from _not_existing_key.exampleservice.domainconnect.org",
            str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string + "&blah=blah", signature, key)
        self.assertEqual("Signature not valid", str(ex.exception))

    def test_is_sig_required(self):
        dc = DomainConnect(template={'providerId': "foo.com", 'serviceId': "bar",
                                     'syncPubKeyDomain': 'example.com'})
        self.assertTrue(dc.is_sig_required(), "case: signature is required")

        dc = DomainConnect(template={'providerId': "foo.com", 'serviceId': "bar"})
        self.assertFalse(dc.is_sig_required(), "case: signature is not required")

    def test_domain_connect_class_constructor(self):
        with self.assertRaises(InvalidTemplate, msg="No parameters"):
            DomainConnect()
        with self.assertRaises(InvalidTemplate, msg="Just serviceId"):
            DomainConnect(service_id='foo')
        with self.assertRaises(InvalidTemplate, msg="Just providerId"):
            DomainConnect(provider_id='bar')
        with self.assertRaises(InvalidTemplate, msg="Just providerId positional"):
            DomainConnect('foo')

        dc = DomainConnect('exampleservice.domainconnect.org', 'template1', self.template_dir)
        self.assertEqual(dc.provider_id, "exampleservice.domainconnect.org")
        self.assertEqual(dc.service_id, "template1")

        dc = DomainConnect(
            template={
                'providerId': "foo.com",
                'providerName': 'Foo provider',
                'serviceId': "bar",
                'serviceName': 'Bar service',
                'variableDescription': 'Variable description',
                'records': [
                    {"type": "TXT", "host": "@", "data": "%param1%", "ttl": 1800},
                    {"type": "TXT", "host": "@", "data": "%param2%", "ttl": 1800},
                ]
            }
        )
        self.assertEqual(dc.provider_id, "foo.com")
        self.assertEqual(dc.service_id, "bar")

    # ------------------------------------------------------------------
    # Deprecated prompt() helper
    # ------------------------------------------------------------------
    @patch('domainconnectzone.DomainConnectImpl.raw_input', side_effect=['value1'])
    def test_prompt(self, mock_input):
        data = {
            'providerId': "foo.com",
            'providerName': 'Foo provider',
            'serviceId': "bar",
            'serviceName': 'Bar service',
            'variableDescription': 'Variable description',
            'records': [
                {"type": "TXT", "host": "@", "data": "%param1%", "ttl": 1800}
            ]
        }
        dc = DomainConnect(template=data)
        params = dc.prompt()
        self.assertEqual(params, {'param1': 'value1'})

    # ------------------------------------------------------------------
    # Validator helpers (not suitable for language-agnostic YAML tests)
    # ------------------------------------------------------------------
    def test_custom_record_type_empty_string_rejected(self):
        from domainconnectzone.validate import is_custom_record_type
        self.assertFalse(is_custom_record_type(''))
        self.assertFalse(is_custom_record_type(None))

    def test_custom_record_type_get_records_variables(self):
        template_records = [
            {'type': 'CAA',    'host': '@',          'data': '0 issue "%issuer%"', 'ttl': 3600},
            {'type': 'TYPE99', 'host': '%subdomain%', 'data': 'static',             'ttl': 300},
        ]
        params = get_records_variables(template_records)
        self.assertIn('issuer', params)
        self.assertIn('subdomain', params)
        self.assertIsNone(params['issuer'])
        self.assertIsNone(params['subdomain'])


if __name__ == '__main__':
    unittest.main()
