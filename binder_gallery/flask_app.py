import os
from flask import Flask as BaseFlask
from flask.app import setupmethod


class Flask(BaseFlask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # load default config
        self.config.from_object('config.Config')
        # to override default config
        custom_config = os.getenv('BG_APPLICATION_SETTINGS')
        if custom_config:
            self.config.from_object(custom_config)

        self.base_url = self.config['BASE_URL']
        self.default_binder_url = self.config['BINDER_URL'].rstrip('/')

        # add static url rule manually
        # https://stackoverflow.com/questions/26722279/how-to-set-static-url-path-in-flask-application/26722526#26722526
        self.static_folder = "static"
        self.add_url_rule(
            self.static_url_path + '/<path:filename>',
            endpoint='static',
            host=None,
            view_func=self.send_static_file
        )

    @setupmethod
    def add_url_rule(self, rule, endpoint=None, view_func=None,
                     provide_automatic_options=None, **options):
        base_url = self.base_url.rstrip('/') if rule.startswith('/') else self.base_url
        rule = base_url + rule
        super().add_url_rule(rule, endpoint, view_func, provide_automatic_options, **options)
