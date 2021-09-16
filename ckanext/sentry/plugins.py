# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration, SentryHandler
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.rq import RqIntegration


from ckan import plugins


log = logging.getLogger(__name__)


CONFIG_FROM_ENV_VARS = {
    'sentry.dsn': 'CKAN_SENTRY_DSN',  # Alias for SENTRY_DSN, used by raven
    'sentry.configure_logging': 'CKAN_SENTRY_CONFIGURE_LOGGING',
    'sentry.log_level': 'CKAN_SENTRY_LOG_LEVEL',
}


class SentryPlugin(plugins.SingletonPlugin):
    '''A simple plugin that add the Sentry middleware to CKAN'''
    plugins.implements(plugins.IMiddleware, inherit=True)

    def make_middleware(self, app, config):
        if plugins.toolkit.check_ckan_version('2.3'):
            return app
        else:
            return self.make_error_log_middleware(app, config)

    def make_error_log_middleware(self, app, config):

        for option in CONFIG_FROM_ENV_VARS:
            from_env = os.environ.get(CONFIG_FROM_ENV_VARS[option], None)
            if from_env:
                config[option] = from_env
        if not config.get('sentry.dsn') and os.environ.get('SENTRY_DSN'):
            config['sentry.dsn'] = os.environ['SENTRY_DSN']

        if plugins.toolkit.asbool(config.get('sentry.configure_logging')):
            self._configure_logging(config)

        log.debug('Adding Sentry middleware...')
        sentry_log_level = config.get('sentry.log_level', logging.INFO)
        sentry_sdk.init(
            dsn=config.get('sentry.dsn'),
            integrations=[
                FlaskIntegration(),
                LoggingIntegration(level=sentry_log_level),
                RqIntegration()
            ]
        )
        return app

    def _configure_logging(self, config):
        '''
        Configure the Sentry log handler to the specified level

        Based on @rshk work on
        https://github.com/opendatatrentino/ckanext-sentry
        '''
        handler = SentryHandler()
        handler.setLevel(logging.NOTSET)

        sentry_log_level = config.get('sentry.log_level', logging.INFO)
        logger = logging.getLogger()
        # ensure we haven't already registered the handler
        if SentryHandler not in map(lambda x: x.__class__, logger.handlers):
            logger.addHandler(handler)
            logger.setLevel(sentry_log_level)
            # Add StreamHandler to sentry's default so you can catch missed exceptions
            logger = logging.getLogger('sentry.errors')
            logger.propagate = False
            logger.addHandler(logging.StreamHandler())

        log.debug('Setting up Sentry logger with level {0}'.format(
            sentry_log_level))
