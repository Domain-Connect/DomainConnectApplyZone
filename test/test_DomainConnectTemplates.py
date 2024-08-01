import json
import unittest
from unittest.mock import patch, mock_open, MagicMock
from domainconnectzone import DomainConnectTemplates, InvalidData, InvalidTemplate
from jsonschema import validate, ValidationError

class TestDomainConnectTemplates(unittest.TestCase):
    def setUp(self):
        self.template_base = \
            {
                "providerId": "Provider",
                "providerName": "Provider Name",
                "serviceId": "Service",
                "serviceName": "Service Name",
                "syncRedirectDomain": "foo.com,bar.net",
                "records": [
                    {"type": "A", "groupId": "1", "host": "@", "pointsTo": "127.0.0.1", "ttl": 300},
                    {"type": "TXT", "groupId": "1", "host": "@", "data": "foo", "ttl": 300},
                    {"type": "SPFM", "groupId": "1", "host": "@", "spfRules": "include:foo.com", "ttl": 300},
                    {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
                     'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400},
                    {'type': 'REDIR301', 'host': 'bar', 'target': 'http://www.bar.foo.com'},
                ]
            }
        self.dct = DomainConnectTemplates('./test/templates')

    @patch('os.path.isdir')
    @patch('os.access')
    @patch('os.listdir')
    @patch('builtins.open', new_callable=mock_open, read_data='{"providerId": "Provider", "serviceId": "Service"}')
    def test_templates_success(self, mock_open, mock_listdir, mock_access, mock_isdir):
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = ['provider.service.json']

        d = DomainConnectTemplates()
        templates = d.templates

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]['fileName'], 'provider.service.json')

    @patch('os.path.isdir')
    @patch('os.access')
    def test_invalid_template_dir(self, mock_access, mock_isdir):
        mock_isdir.return_value = False
        mock_access.return_value = False

        with self.assertRaises(InvalidTemplate):
            DomainConnectTemplates()

    @patch('os.path.isdir')
    @patch('os.access')
    @patch('os.listdir')
    def test_malformed_json(self, mock_listdir, mock_access, mock_isdir):
        # Mocking a malformed JSON file in the directory
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = ['malformed.json']
        malformed_json_content = '{"providerId": "Provider", "serviceId": "Service"'
        with patch('builtins.open', mock_open(read_data=malformed_json_content)):
            d = DomainConnectTemplates()
            templates = d.templates
            self.assertEqual(len(templates), 0)  # Malformed JSON should be ignored

    @patch('os.path.isdir')
    @patch('os.access')
    @patch('os.listdir')
    def test_incorrect_template_content(self, mock_listdir, mock_access, mock_isdir):
        # Testing with a file that does not follow the naming convention
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = ['provider.service.json']
        correct_json_content = '{"providerId": "Provider"}'
        with patch('builtins.open', mock_open(read_data=correct_json_content)):
            d = DomainConnectTemplates()
            templates = d.templates
            self.assertEqual(len(templates), 0)  # File with incomplete template should be ignored

    @patch('os.path.isdir')
    @patch('os.access')
    @patch('os.listdir')
    def test_incorrect_naming_convention(self, mock_listdir, mock_access, mock_isdir):
        # Testing with a file that does not follow the naming convention
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = ['incorrectname.json']
        correct_json_content = '{"providerId": "Provider", "serviceId": "Service"}'
        with patch('builtins.open', mock_open(read_data=correct_json_content)):
            d = DomainConnectTemplates()
            templates = d.templates
            self.assertEqual(len(templates), 0)  # File with incorrect naming should be ignored

    @patch('os.path.isdir')
    @patch('os.access')
    @patch('os.listdir')
    def test_empty_templates_directory(self, mock_listdir, mock_access, mock_isdir):
        # Testing with an empty templates directory
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = []
        d = DomainConnectTemplates()
        templates = d.templates
        self.assertEqual(len(templates), 0)  # No templates should be found

    @patch('os.path.isdir')
    @patch('os.access')
    @patch('os.listdir')
    def test_custom_template_path(self, mock_listdir, mock_access, mock_isdir):
        # Testing with a custom template path
        custom_path = '/custom/path/to/templates'
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = ['provider.service.json']
        valid_json_content = '{"providerId": "Provider", "serviceId": "Service"}'
        with patch('builtins.open', mock_open(read_data=valid_json_content)):
            d = DomainConnectTemplates(template_path=custom_path)
            templates = d.templates
            self.assertEqual(len(templates), 1)
            self.assertEqual(templates[0]['fileName'], 'provider.service.json')
            self.assertIn(custom_path, d._template_path)

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('os.access')
    @patch('os.listdir')
    def test_schema_loading(self, mock_listdir, mock_access, mock_isfile, mock_isdir):
        # Testing schema loading
        mock_isdir.return_value = True
        mock_access.side_effect = [True, True]  # First for schema_path, second for template_path
        mock_isfile.return_value = True
        mock_listdir.return_value = ['provider.service.json']
        valid_schema_content = '{"some": "schema"}'
        mock_open_instance = mock_open()
        mock_open_instance.side_effect = [mock_open(read_data=valid_schema_content).return_value,
                                          mock_open(read_data=json.dumps(self.template_base)).return_value]

        with patch('builtins.open', mock_open_instance):
            d = DomainConnectTemplates()
            templates = d.templates
            self.assertEqual(d.schema, {"some": "schema"})
            self.assertEqual(len(templates), 1)
            self.assertEqual(templates[0]['fileName'], 'provider.service.json')

    def test_validate_template_success(self):
        # Test successful template validation
        self.dct.validate_template(self.template_base)

    def test_invalid_provider_service_id(self):
        # Test with invalid providerId and serviceId
        invalid_template = self.template_base.copy()
        invalid_template["providerId"] = "invalid provider!"
        invalid_template["serviceId"] = "invalid service!"
        with self.assertRaises(InvalidData):
            self.dct.validate_template(invalid_template)

    def test_invalid_domain_names(self):
        # Test with invalid domain names in syncPubKeyDomain and syncRedirectDomain
        invalid_template = self.template_base.copy()
        invalid_template["syncPubKeyDomain"] = "invalid-domain..com"
        invalid_template["syncRedirectDomain"] = "another-invalid-domain..com"
        with self.assertRaises(InvalidData):
            self.dct.validate_template(invalid_template)

    def test_forbidden_variable_in_records(self):
        # Test forbidden variable presence in records
        invalid_template = self.template_base.copy()
        invalid_template["records"][0]["groupId"] = "%invalid%"
        with self.assertRaises(InvalidTemplate):
            self.dct.validate_template(invalid_template)

    def test_invalid_variable_in_records(self):
        # Test forbidden variable presence in records
        invalid_template = self.template_base.copy()
        invalid_template["records"][0]["host"] = "%invalid"
        with self.assertRaises(InvalidTemplate):
            self.dct.validate_template(invalid_template)

    def test_forbidden_domain_in_syncRedirectDomain(self):
        # Test forbidden characters presence in syncRedirectDomain
        invalid_template = self.template_base.copy()
        invalid_template["syncRedirectDomain"] = "foo.&pl"
        with self.assertRaises(InvalidData):
            self.dct.validate_template(invalid_template)

    def test_schema_validation_error(self):
        # Test invalid template
        invalid_template = self.template_base.copy()
        del invalid_template["providerName"]
        with self.assertRaises(InvalidTemplate):
            self.dct.validate_template(invalid_template)


class TestDomainConnectTemplatesVariableNames(unittest.TestCase):

    def setUp(self):
        self.template = {
            "records": [
                {"type": "A", "host": "@", "pointsTo": "%h%"},
                {"groupId": "a", "type": "CNAME", "host": "foo", "pointsTo": "%d%"}
            ]
        }

    def test_get_variable_names_no_group_no_variables(self):
        # Test without group and variables
        result = DomainConnectTemplates.get_variable_names(self.template)
        self.assertEqual(result, {"domain": '', "host": '', "group": '', "d": None, "h": None})

    def test_get_variable_names_with_group(self):
        # Test with group
        result = DomainConnectTemplates.get_variable_names(self.template, group="a")
        self.assertEqual(result, {"d": None})

    def test_get_variable_names_with_variables(self):
        # Test with provided variables
        variables = {"d": "customdomain.com", "newvar": "value"}
        result = DomainConnectTemplates.get_variable_names(self.template, variables=variables)
        self.assertEqual(result, {"domain": '', "host": '', "group": '', "d": "customdomain.com", "h": None})


class TestDomainConnectTemplatesGetGroupIDs(unittest.TestCase):
    def test_get_group_ids_with_groups(self):
        # Testing with multiple records having unique group IDs
        template = {
            "records": [
                {"type": "A", "groupId": "group1"},
                {"type": "CNAME", "groupId": "group2"},
                {"type": "MX", "groupId": "group1"}
            ]
        }
        groups = DomainConnectTemplates.get_group_ids(template)
        self.assertEqual(groups, ["group1", "group2"])

    def test_get_group_ids_without_groups(self):
        # Testing with records that don't have group IDs
        template = {
            "records": [
                {"type": "A"},
                {"type": "CNAME"}
            ]
        }
        groups = DomainConnectTemplates.get_group_ids(template)
        self.assertEqual(groups, [])

    def test_get_group_ids_no_records(self):
        # Testing with no records in the template
        template = {}
        groups = DomainConnectTemplates.get_group_ids(template)
        self.assertEqual(groups, [])

    def test_get_group_ids_with_duplicate_groups(self):
        # Testing with duplicate group IDs in the records
        template = {
            "records": [
                {"type": "A", "groupId": "group1"},
                {"type": "CNAME", "groupId": "group1"}
            ]
        }
        groups = DomainConnectTemplates.get_group_ids(template)
        self.assertEqual(groups, ["group1"])

if __name__ == '__main__':
    unittest.main()