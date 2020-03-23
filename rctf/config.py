#!/usr/bin/env python3

import collections
import envparse
import os, sys
import json

from . import logging, execute, check_file, colored_command

# XXX: they do be makin it hard for us
def read_env(fname):
    # i hate envparse so much, you have no idea
    # same goes for python-dotenv, environs, etc

    env_backup = envparse.os.environ
    envparse.os.environ = dict()
    envparse.env.read_envfile(fname)
    contents = envparse.os.environ
    envparse.os.environ = env_backup

    return contents


class Config(collections.OrderedDict):
    # for mapping to headers
    config_keys = {
        'RCTF_NAME' : 'ctf.name',
        'RCTF_ORIGIN' : 'ctf.origin',

        'RCTF_DATABASE_URL' : 'db.url',

        'RCTF_REDIS_URL' : 'redis.url',

        'RCTF_SMTP_URL' : 'smtp.url',
        'RCTF_EMAIL_FROM' : 'smtp.from'
    }


    # this is what the actual config is by default
    default_config = collections.OrderedDict({
        'cli.ansi' : True
    })


    def __init__(self, config_path, *args, dotenv_path = None, **kwargs):
        retval = super().__init__(*args, **kwargs)

        self.config_path = config_path
        self.dotenv_path = dotenv_path

        self.get = self.__get
        self.set = self.__set

        return retval


    def __get(self, key, default = None):
        return str(self[key]) if key in self else default


    # XXX: support more types of vars
    def get_bool(self, *args, **kwargs):
        return str(self.get(*args, **kwargs).strip().lower()) in ['true', '1', 'enable', 'true']


    def get_int(self, *args, **kwargs):
        return int(str(self.get(*args, **kwargs).strip()))


    def __set(self, key, value):
        self[key] = str(value)
        return key

    '''
    reads from the config file and updates local dict
    :arg update_config: tells it to replace config entries with dotenv entries
    :return: self
    '''
    def read(self, update_config = False):
        if self.config_path == '':
            raise RuntimeError('Attempted to read dummy config path')

        # XXX: TOCTOU
        if update_config or not check_file(self.config_path):
            print('kk')
            logging.debug('Config file ', colored_command(self.config_path), ' does not exist, using default config...')

            config = Config.default_config.copy()

            if update_config:
                config = self.read(update_config = False)

            if self.dotenv_path:
                logging.debug('... and importing config from dotenv file ', colored_command(self.dotenv_path))

                dotenv_config = read_env(self.dotenv_path)

                # copy only certain keys from dotenv
                for key in sorted(dotenv_config.keys()):
                    value = dotenv_config[key]

                    if key in Config.config_keys:
                        config[Config.config_keys[key]] = str(value)

            self.clear()
            self.update(config)
            self.write()
        else:
            with open(self.config_path, 'r') as f:
                # TODO: auto identify bad permissions on config and warn
                config = json.loads(f.read(), object_pairs_hook = collections.OrderedDict)

            self.clear()
            self.update(config)

        return self


    def write(self):
        if self.config_path == '':
            raise RuntimeError('Attempted to write dummy config path')

        config = json.dumps(self, indent = 2)

        with open(self.config_path, 'w') as f:
            return f.write(config)


        # XXX/BUG: race condition vuln
        os.chmod(self.config_path, 0o600)


    # gets config environ
    def _get_as_environ(self):
        envvars = dict()

        reverse_config_keys = {value : key for key, value in Config.config_keys.items()}

        for key, value in self.items():
            if key in reverse_config_keys:
                envvars[reverse_config_keys[key]] = str(value)
            elif not key.startswith('cli.'):
                envvars[key] = str(value)

        return envvars
