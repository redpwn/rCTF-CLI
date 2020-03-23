#!/usr/bin/env python3

import os, sys

from . import execute, config, logging

class rCTF:
    def __init__(self, install_path = '/opt/rctf/'):
        if not install_path.endswith('/'):
            install_path += '/'

        self.install_path = install_path

        self._default_config_path = install_path + '.config.json'
        self._dotenv_path = install_path + '.env'


    def start(self):
        os.chdir(self.install_path)

        if not execute('docker-compose --no-ansi up -d --build', environ = self.get_env()):
            logging.fatal('Failed to start rCTF instance.')
            return False

        return True


    def stop(self):
        os.chdir(self.install_path)

        if not execute('docker-compose --no-ansi down', environ = self.get_env()):
            logging.fatal('Failed to stop rCTF instance.')
            return False

        return True


    def upgrade(self):
        os.chdir(self.install_path)

        # XXX: is there a way to make this not error if it fails?
        self.down()

        if not execute('git pull'):
            logging.fatal('Failed to pull latest from repository.')
            return False

        if not execute('docker-compose --no-ansi build --no-cache', environ = self.get_env()):
            logging.fatal('Failed to rebuild docker image.')
            return False

        return True


    def get_config(self, path = None, update_config = False):
        return config.Config(path or self._default_config_path).read(update_config = update_config)


    def __getattr__(self, name):
        if self.name == 'config':
            # return default config path
            return self.get_config()
        else:
            # default behaviour
            raise AttributeError

    # merges os.environ and configuration environ
    def get_env(self):
        environ = self.get_config()._get_as_environ()
        environ.update(os.environ.copy())

        return environ
