#!/usr/bin/env python3
#
#  IRIS Source Code
#  Copyright (C) 2022 - DFIR-IRIS Team
#  contact@dfir-iris.org
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3 of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
import decimal
import json
import pickle
import uuid
import datetime
from string import Template

import requests
import re

import iris_interface.IrisInterfaceStatus as InterfaceStatus
from iris_interface.IrisModuleInterface import IrisModuleInterface, IrisModuleTypes
from app.datamgmt.iris_engine.modules_db import module_list_available_hooks
from app.schema.marshables import AlertSchema, CaseDetailsSchema, CaseAssetsSchema, CaseNoteSchema, IocSchema, EventSchema, CaseEvidenceSchema, CaseTaskSchema
import iris_webhooks_module.IrisWebHooksConfig as interface_conf


class IrisWebHooksInterface(IrisModuleInterface):
    """
    Provide the interface between Iris and WebHooks
    """
    name = "IrisWebHooksInterface"
    _module_name = interface_conf.module_name
    _module_description = interface_conf.module_description
    _interface_version = interface_conf.interface_version
    _module_version = interface_conf.module_version
    _pipeline_support = interface_conf.pipeline_support
    _pipeline_info = interface_conf.pipeline_info
    _module_configuration = interface_conf.module_configuration
    _module_type = IrisModuleTypes.module_processor

    def register_hooks(self, module_id: int):
        """
        Registers hooks for the module. None by default

        :param module_id: Module ID provided by IRIS
        :return: Nothing
        """
        self.module_id = module_id
        module_conf = self.module_dict_conf

        if module_conf is None:
            self.log.info('No configuration found - probably first run')
            return

        hooks = []

        if module_conf.get('wh_configuration') is None:
            self.log.info('Web hook configuration not found. Maybe first run?')
            self.log.info('Nothing to do here')
            return

        jconfig = json.loads(module_conf.get('wh_configuration'))

        if not jconfig.get('webhooks'):
            self.log.info('No web hooks configured - skipping')
            return

        if not self._check_self_config(jconfig.get('webhooks')):
            self.log.error('Web hook configuration not valid')
            return

        available_hooks = [hook.hook_name for hook in module_list_available_hooks()]
        for inhook in available_hooks:
            if 'on_postload' not in inhook:
                continue
            self.deregister_from_hook(module_id=module_id, iris_hook_name=inhook)

        for hook in jconfig.get('webhooks'):

            for iris_hook in hook.get('trigger_on'):

                if hook.get('active') is False:
                    self.log.info(f'Web hook {hook.get("name")} is not active, skipping')
                    if 'on_manual_trigger' in iris_hook:
                        self.deregister_from_hook(module_id=module_id, iris_hook_name=iris_hook)
                    continue

                if iris_hook in ['all', 'all_update', 'all_create', 'all_delete']:
                    hook_split = iris_hook.split('_')
                    hook_action = None

                    if len(hook_split) == 2:
                        hook_action = hook_split[1]

                    for inhook in available_hooks:
                        if 'on_postload' not in inhook:
                            continue

                        if hook_action and not inhook.endswith(hook_action):
                            continue

                        self.log.info(f'Registering to {inhook}')
                        status = self.register_to_hook(module_id, iris_hook_name=inhook)
                        if status.is_failure():
                            self.log.error(status.get_message())
                            self.log.error(status.get_data())

                        else:
                            hooks.append(inhook)

                supported_hooks = [
                    'on_postload',
                    'on_manual_trigger'
                ]

                if iris_hook.startswith('on_preload_'):
                    if not iris_hook.endswith('_delete'):
                        self.log.warning(f'{iris_hook} is not supported by this module')
                        continue
                elif not any(iris_hook.startswith(prefix) for prefix in supported_hooks):
                    self.log.warning(f'{iris_hook} is not supported by this module')
                    continue

                if 'on_manual_trigger' in iris_hook:
                    # Check that we have a manual trigger name
                    if not hook.get('manual_trigger_name'):
                        self.log.warning(f'No manual trigger name for {iris_hook}. Please set manual_trigger_name.')
                        continue

                    manual_trigger_name = hook.get('manual_trigger_name')
                    self.log.info(f'Registering to manual hook {iris_hook}')
                    status = self.register_to_hook(module_id, iris_hook_name=iris_hook,
                                                   manual_hook_name=manual_trigger_name)

                    if status.is_failure():
                        self.log.error(status.get_message())
                        self.log.error(status.get_data())
                    else:
                        hooks.append(iris_hook)

                else:
                    self.log.info(f'Registering to {iris_hook}')
                    status = self.register_to_hook(module_id, iris_hook_name=iris_hook)

                    if status.is_failure():
                        self.log.error(status.get_message())
                        self.log.error(status.get_data())

                    else:
                        hooks.append(iris_hook)

        self.log.info('Successfully registered to hooks {hooks}'.format(hooks=','.join(set(hooks))))

    def hooks_handler(self, hook_name: str, hook_ui_name: str, data: any):
        """
        Hooks handler table. Calls corresponding methods depending on the hooks name.

        :param hook_name: Name of the hook which triggered
        :param hook_ui_name: Name of the ui hook
        :param data: Data associated with the trigger.
        :return: Data
        """

        self.log.info(f'Received {hook_name}')
        status = self._handle_hook(hook_name, hook_ui_name, data=data)

        if status.is_failure():
            self.log.error(f"Encountered error processing hook {hook_name}")
            return InterfaceStatus.I2Error(data=data, logs=list(self.message_queue))

        self.log.info(f"Successfully processed hook {hook_name}")
        return InterfaceStatus.I2Success(data=data, logs=list(self.message_queue))

    def _handle_hook(self, hook_name, hook_ui_name, data) -> InterfaceStatus.IIStatus:
        """
        Handle the data the module just received. The module registered
        to on_postload hooks, so it receives instances of object.
        These objects are attached to a dedicated SQlAlchemy session so data can
        be modified safely.

        :param data: Data associated to the hook
        :param hook_name: Name of the received hook
        :param hook_ui_name: Name of the hook in UI
        :return: IIStatus
        """

        self.log.info(f'Received {hook_name}, {hook_ui_name}')
        in_status = InterfaceStatus.IIStatus(code=InterfaceStatus.I2CodeNoError)

        module_conf = self.module_dict_conf

        if module_conf.get('wh_configuration') is None:
            self.log.error('Web hook configuration not found')

        jconfig = json.loads(module_conf.get('wh_configuration'))
        if not self._check_self_config(jconfig.get('webhooks')):
            self.log.error('Web hook configuration not valid')
            return InterfaceStatus.I2Error(msg='Configuration not valid')

        server_url = jconfig.get('instance_url')

        for hook in jconfig.get('webhooks'):

            for iris_hook in hook.get('trigger_on'):
                if hook.get('active') is False:
                    self.log.info(f'Web hook {hook.get("name")} is not active, skipping')
                    continue

                if iris_hook in ['all', 'all_update', 'all_create']:
                    hook_split = iris_hook.split('_')

                    if len(hook_split) == 2:
                        hook_action = hook_split[1]

                        if hook_name.endswith(hook_action):
                            self._do_web_hook(hook_name, data, hook, server_url)

                    else:
                        self._do_web_hook(hook_name, data, hook, server_url)

                elif iris_hook == hook_name:
                    if hook_name.startswith('on_manual_trigger'):
                        if hook.get('manual_trigger_name') == hook_ui_name:
                            self._do_web_hook(hook_name, data, hook, server_url)
                        else:
                            continue
                    else:
                        self._do_web_hook(hook_name, data, hook, server_url)

        return in_status(data=data)

    def _do_web_hook(self, hook_name, data, hook, server_url) -> InterfaceStatus.IIStatus:
        """

        :param hook_name:
        :param server_url:
        :param data:
        :param hook:
        :param server_url:
        :return:
        """

        hook_split = hook_name.split('_')
        hook_type = hook_split[-1]
        hook_object = '_'.join(hook_split[2:3])

        if 'on_manual_trigger' in hook_name:
            hook_object = '_'.join(hook_split[3:])

        user_name = 'N/A'
        object_name = 'N/A'
        case_name = 'N/A'
        case_id = None
        object_url = None
        case_info = ""
        raw_data = {}
        file_path = ""
        rfile = ""

        request_rendering = hook.get('request_rendering')
        use_rendering = hook.get('use_rendering')

        # Get the username if it exists. Check if data[0] contains user first
        if getattr(data[0], 'user', None):
            user_name = data[0].user.name
        elif getattr(data[0], 'user_update', None):
            user_name = data[0].user_update.name
        try:
            if hook_object == 'case':
                object_name = data[0].name
                object_url = f"{server_url}/case?cid={data[0].case_id}"
                case_name = data[0].name
                raw_data = {
                    'cases': CaseDetailsSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'asset':
                object_name = data[0].asset_name
                case_id = data[0].case_id
                object_url = f"{server_url}/case/assets?cid={case_id}&shared={data[0].asset_id}"
                case_name = data[0].case.name
                raw_data = {
                    'assets': CaseAssetsSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'note':
                object_name = data[0].note_title
                case_id = data[0].note_case_id
                object_url = f"{server_url}/case/notes?cid={case_id}&shared={data[0].note_id}"
                case_name = data[0].case.name
                raw_data = {
                    'notes': CaseNoteSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'ioc':
                object_name = data[0].ioc_value
                raw_data = {
                    'iocs': IocSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'event':
                object_name = data[0].event_title
                case_name = data[0].case.name
                case_id = data[0].case_id
                object_url = f"{server_url}/case/timeline?cid={case_id}&shared={data[0].event_id}"
                raw_data = {
                    'events': EventSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'evidence':
                object_name = data[0].filename
                case_name = data[0].case.name
                case_id = data[0].case_id
                object_url = f"{server_url}/case/evidences?cid={case_id}&shared={data[0].id}"
                raw_data = {
                    'evidences': CaseEvidenceSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'task' or hook_object == 'global_task':
                object_name = data[0].task_title
                case_name = data[0].case.name
                case_id = data[0].task_case_id
                object_url = f"{server_url}/case/tasks?cid={case_id}&shared={data[0].id}"
                raw_data = {
                    'tasks': CaseTaskSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'alert':
                if isinstance(data[0], dict):
                    object_url = f"{server_url}/alerts/filter?alert_ids={data[0]['alert_ids']}"
                else:
                    object_url = f"{server_url}/alerts/filter?alert_ids={data[0].alert_id}"
                raw_data = {
                    'alerts': AlertSchema(many=True).dump(data),
                    'object_url': object_url
                }
    
            elif hook_object == 'report':
                object_name = data[0]['report_id']
                user_name = data[0]['user_name']
                case_name = data[0]['report_id']
                case_id = data[0]['case_id']
                file_path = data[0]['file_path']
                rfile = data[0]['file']
        except AttributeError as AttrException:
            self.log.error(str(AttrException))
            raise

        if object_url:
            object_name = self._render_url(object_url, object_name, request_rendering)

        if case_id:
            case_info = "on case {rendered_url}".format(rendered_url=self._render_url(f"{server_url}/case?cid={case_id}",
                                                                                      f"#{case_id}", request_rendering))

        raw_data['object_url'] = object_url

        description = f"{user_name} {hook_type}d {hook_object} {object_name} {case_info}"
        title = f"[{case_name}] {hook_object.capitalize()} {hook_type}d"

        try:
            request_content = json.dumps(hook.get('request_body'), cls=AlchemyEncoder)
        except Exception as e:
            self.log.error(str(e))
            return

        if use_rendering:
            request_content = request_content.replace('%TITLE%', title)
            request_content = request_content.replace('%DESCRIPTION%', description)
            request_content = request_content.replace('%FILE%', rfile)
            try:
                request_data = json.loads(request_content)
            except Exception as e:
                self.log.error('Encountered error running hook.')
                self.log.error(str(e))
                return

        else:

            request_data = self.map_request_content(hook.get('request_body'), raw_data)
            req = json.dumps(request_data, cls=AlchemyEncoder)
            request_data = json.loads(req)

        url = hook.get('request_url')
        request_headers = hook.get('request_headers') if hook.get('request_headers') is not None else {}
        verify_ssl = hook.get('verify_ssl') if hook.get('verify_ssl') is not None else True

        result = requests.post(url, json=request_data, headers=request_headers, verify=verify_ssl)

        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.log.error(err)
            self.log.error(result.text)
            self.log.error(request_data)
        else:
            self.log.info(f"Webhook {hook.get('name')} - Payload delivered successfully, code {result.status_code}.")

    def get_nested(self, data, key_list):
        if not key_list:
            return data

        element = key_list.pop(0)

        if isinstance(data, list):
            return [self.get_nested(item, key_list.copy()) for item in data]

        if isinstance(data, dict) and element in data:
            return self.get_nested(data[element], key_list)
        else:
            return None

    def replace_template_placeholders(self, template_str, data):
        # get all keys in template
        keys_in_template = re.findall(r"\${{(.*?)}}", template_str)

        replacements = {}
        for key in keys_in_template:
            keys = key.split('.')

            if isinstance(data.get(keys[0]), list):
                extracted_values = []
                for cdata in data[keys[0]]:
                    nested_value = self.get_nested(cdata, keys[1:])
                    extracted_values.append(nested_value if nested_value is not None else "")

                if len(keys) == 1:
                    replacements[key] = extracted_values
                else:
                    replacements[key] = extracted_values if len(extracted_values) > 1 else extracted_values[0]
            else:
                nested_value = self.get_nested(data, keys)
                replacements[key] = nested_value if nested_value is not None else ""

        for key, value in replacements.items():
            template_str = template_str.replace(f"${{{{{key}}}}}", str(value))
        return template_str

    def map_request_content(self, request_content, data):
        result = {}

        for key, value in request_content.items():
            if isinstance(value, str) and '${{' in value:
                # Handle templated strings
                result[key] = self.replace_template_placeholders(value, data)

            # handle nested values
            elif isinstance(value, dict):
                result[key] = self.map_request_content(value, data)

            else:
                keys = value.split('.')

                if isinstance(data.get(keys[0]), list):
                    extracted_values = []
                    for cdata in data[keys[0]]:
                        nested_value = self.get_nested(cdata, keys[1:])
                        extracted_values.append(nested_value if nested_value is not None else "")

                    if len(keys) == 1:
                        result[key] = extracted_values
                    else:
                        result[key] = extracted_values if len(extracted_values) > 1 else extracted_values[0]

                else:
                    nested_value = self.get_nested(data, keys)
                    result[key] = nested_value if nested_value is not None else ""

        return result

    def _render_url(self, url, link, rendering_format):
        """
        Renders the url with the rendering format
        :param url: url to render
        :param link: link to render
        :param rendering_format: rendering format
        :return: rendered url
        """

        if rendering_format == 'markdown':
            return f"[{link}]({url})"
        elif rendering_format == 'markdown_slack':
            return f"<{url}|{link}>"
        elif rendering_format == 'html':
            return f"<a href='{url}'>{link}</a>"
        else:
            return url

    def _check_self_config(self, jconfig):
        """
        Verifies the web hook configuration provided is valid
        :return: Bool
        """

        for hook in jconfig:

            if hook.get('name') is None:
                self.log.error('Tag "name" not found in web hook configuration')
                return False

            if hook.get('request_url') is None:
                self.log.error('Tag "request_url" not found in web hook configuration')
                return False

            if hook.get('request_body') is None:
                self.log.error('Tag "request_body" not found in web hook configuration')
                return False

            if hook.get('trigger_on') is None:
                self.log.error('Tag "trigger_on" not found in web hook configuration')
                return False

        return True


class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):

        if isinstance(obj, decimal.Decimal):
            return str(obj)

        if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
            return obj.isoformat()

        if isinstance(obj, uuid.UUID):
            return str(obj)

        else:
            if obj.__class__ == bytes:
                try:
                    return pickle.load(obj)
                except Exception:
                    return str(obj)

        try:
            return json.JSONEncoder.default(self, obj)
        except Exception:
            return str(obj)
