from odoo import api, fields, models, _, SUPERUSER_ID
import requests
import json

class response_message_wizard(models.TransientModel):
    _name = 'response.message.wizard'
    _description = 'Response Message'

    def _get_message(self):
        return self._context['message']

    message = fields.Html("Response", default=_get_message, readonly=True)