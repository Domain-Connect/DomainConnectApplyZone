import json
import os
from re import compile, search

from jsonschema import validate, ValidationError

from domainconnectzone import InvalidTemplate, InvalidData
from domainconnectzone.DomainConnectImpl import get_records_variables


class DomainConnectTemplates(object):
    def __init__(self, template_path=None):
        if not template_path:
            self._template_path = os.path.dirname(os.path.realpath(__file__)) + '/templates'
        else:
            self._template_path = template_path
        if not os.path.isdir(self._template_path) or not os.access(self._template_path, os.R_OK):
            raise InvalidTemplate('Template dir \'{}\' not found or unreadable'.format(os.path.abspath(self._template_path)))
        self._schema = None
        schema_path = os.path.join(self._template_path, 'template.schema')
        if os.path.isfile(schema_path) and os.access(schema_path, os.R_OK):
            with open(schema_path, 'r') as f:
                self._schema = json.load(f)
        else:
            self._schema = None

    @property
    def schema(self):
        return self._schema

    @property
    def templates(self):
        templates = []
        for file_to_check in [r for r in os.listdir(self._template_path) if r.endswith('.json')]:
            with open(os.path.join(self._template_path, file_to_check)) as f:
                try:
                    template_json = json.load(f)
                except ValueError:
                    # skip invalid template files
                    continue
                try:
                    expected_filename = '{}.{}.json'.format(template_json['providerId'].lower(),
                                                            template_json['serviceId'].lower())
                except KeyError:
                    # skip templates without required fields providerId and serviceId
                    continue
                # if file contains other providerId/serviceId - ignore
                if expected_filename != file_to_check:
                    continue
                templates += [{
                    "providerId": template_json['providerId'],
                    "serviceId": template_json['serviceId'],
                    "fileName": file_to_check,
                    "template": template_json
                }]
        return templates

    @staticmethod
    def _validate_domain_name(label, name):
        dom_val = compile("^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.)+[A-Za-z]{2,63}$")
        if dom_val.search(name) is None:
            raise InvalidData("{} is not a valid domain name in label {}".format(name, label))

    def validate_template(self, template):
        if search(r'^[a-zA-Z0-9._-]+$', template["providerId"]) is None \
                or search(r'^[a-zA-Z0-9._-]+$', template["serviceId"]) is None:
            raise InvalidData("Invalid ServiceId or ProviderId")
        if 'syncPubKeyDomain' in template:
            self._validate_domain_name('syncPubKeyDomain', template['syncPubKeyDomain'])
        if 'syncRedirectDomain' in template:
            for dom in [x.strip() for x in template['syncRedirectDomain'].split(',')]:
                if dom != "":
                    self._validate_domain_name('syncRedirectDomain', dom)
        if self._schema is not None:
            try:
                validate(template, self._schema)
            except ValidationError as ve:
                raise InvalidTemplate("{}".format(ve.message))

        #check for fields which should never contain variables
        for r in template["records"]:
            for field in ["groupId", "type", "ttl", "essential", "txtConflictMatchingMode", "txtConflictMatchingPrefix",
                          "weight", "port"]:
                if field in r and '{}'.format(r[field]).find("%") != -1:
                    raise InvalidTemplate(
                        'Forbidden variable in record {} field {}: {}'.format(
                            r["type"].upper(), field.upper(), r[field]))

        #validate if all variables can be extracted
        DomainConnectTemplates.get_variable_names(template)

    def update_template(self, template):
        if not os.access(self._template_path, os.W_OK):
            raise EnvironmentError("Cannot write to the configured template folder.")
        self.validate_template(template)
        templ = self.templates
        for t in templ:
            if t["providerId"] == template["providerId"] and t["serviceId"] == template["serviceId"]:
                with open(os.path.join(self._template_path, t["fileName"]), "w") as f:
                    json.dump(template, f, indent=2)
                return
        raise InvalidTemplate("Cannot find template {} / {}".format(template['providerId'], template['serviceId']))

    def create_template(self, template):
        if not os.access(self._template_path, os.W_OK):
            raise EnvironmentError("Cannot write to the configured template folder.")
        self.validate_template(template)

        templ = self.templates
        for t in templ:
            if t["providerId"] == template["providerId"] and t["serviceId"] == template["serviceId"]:
                raise InvalidTemplate("Template {} / {} already exists.".format(template['providerId'], template['serviceId']))
        with open(os.path.join(self._template_path, "{}.{}.json".format(template['providerId'].lower(), template['serviceId'].lower())), "w") as f:
            json.dump(template, f, indent=2)

    @staticmethod
    def get_variable_names(template, variables=None, group=None):
        params = get_records_variables(template['records'], group)
        if group is None:
            pars = {
                'domain': '',
                'host': '',
                'group': ''
            }
        else:
            pars = {}
        params.update(pars)
        if variables is not None:
            for label in params:
                if label in variables:
                    params[label] = variables[label]
        return params

    @staticmethod
    def get_group_ids(template):
        groups = []
        if 'records' in template:
            for record in template['records']:
                if 'groupId' in record and not record['groupId'] in groups:
                    groups += [record['groupId']]
        return groups
