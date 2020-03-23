#!/usr/bin/env python3
# a script to manage rCTF installations

from rctf import *

import sys, os, io, subprocess, selectors
import argparse, functools
import traceback, re
import collections, json


# custom pip3 dependencies:
# * requests
# * envparse

try:
    import requests # requests
    import envparse # envparse
except ModuleNotFoundError:
    logging.fatal('You must install the required modules')
    logging.error('    pip3 install --upgrade requests envparse\n', exc_info = True)
    exit(1)


# from: https://stackoverflow.com/a/38662876
def strip_ansi(line):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', line)


# main


if __name__ == '__main__':
    # parse arguments

    parser = argparse.ArgumentParser(description = 'Manage rCTF installations from the CLI')
    parser.add_argument('--install-path', '--path', '-d', type = str, default = os.environ.get('RCTF_INSTALL_PATH', os.environ.get('INSTALL_PATH', '/opt/rctf/')), help = 'The path to the rCTF installation to manage')
    parser.add_argument('--config-path', '--config', type = str, default = None, help = 'The path to the rCTF configuration file')
    parser.add_argument('--no-ansi', '-c', default = False, action = 'store_true', help = 'Disable ANSI coloring on all output')
    parser.add_argument('--log-level', '-v', default = None, type = str, help = 'Set logging level')

    subparsers = parser.add_subparsers(help = 'The sub-command to execute')

    parser_up = subparsers.add_parser('up', aliases = ['start'], help = 'Start rCTF in background')
    parser_up.set_defaults(subcommand = 'up')

    parser_down = subparsers.add_parser('down', aliases = ['stop'], help = 'Stop rCTF if running')
    parser_down.set_defaults(subcommand = 'down')

    parser_update = subparsers.add_parser('update', aliases = ['upgrade'], help = 'Update the rCTF installation')
    parser_update.set_defaults(subcommand = 'update')

    parser_config = subparsers.add_parser('config', aliases = ['configure'], help = 'Configure the rCTF installation')
    parser_config.set_defaults(subcommand = 'config')
    parser_config.add_argument('--editor', '--edit', '-e', default = False, action = 'store_true', help = 'Open a text editor of the configuration (from $EDITOR)')
    parser_config.add_argument('--unset', '-u', default = False, action = 'store_true', help = 'Leave the key unset but do not delete it from the config')
    parser_config.add_argument('--delete', '-d', default = False, action = 'store_true', help = 'Remove the key from the config')
    parser_config.add_argument('key', nargs = '?', default = None, help = 'The config key to read/write')
    parser_config.add_argument('value', nargs = '?', default = None, help = 'The value to write to the key')

    args = parser.parse_args()

    install_path = args.install_path
    os.chdir(install_path)

    instance = rctf.rCTF(install_path = install_path)

    # config path

    if args.config_path != None:
        instance._default_config_path = args.config_path

    # parse cli config

    read_config = False

    try:
        config = instance.get_config()

        read_config = True
    except PermissionError:
        # XXX: this is a dummy path. find a better way to handle
        config = Config(Config.default_config)

    # disable ansi color codes if necessary

    if (not config.get_bool('cli.ansi')) or args.no_ansi:
        USE_ANSI = False

        # XXX: this is a bit hacky
        for key in colors.keys():
            colors[key] = ''

    # set logging level

    log_level = args.log_level

    if log_level is None:
        log_level = config.get('cli.logLevel', 'debug')

    log_level = log_levels.get(log_level, log_level)

    try:
        log_level = int(log_level)
    except ValueError:
        # convert to int if possible
        logging.warn('Unable to convert logging level ', colored_command(log_level), ' to an integer.')

    logging.setLevel(log_level)

    # parse arguments

    if not 'subcommand' in vars(args):
        logging.info('This is the rCTF CLI management tool. For usage, run:\n\n    ', colored_command('%s --help' % sys.argv[0]), '\n')
        exit(0)

    subcommand = args.subcommand

    if subcommand in ['start', 'up']:
        logging.info('Starting rCTF...')

        try:
            instance.start()
            logging.info('Started rCTF.')
        except:
            logging.fatal('Failed to start rCTF.', exc_info = True)
            exit(1)
    elif subcommand in ['stop', 'down']:
        logging.info('Stopping rCTF...')

        try:
            instance.stop()
            logging.info('Stopped rCTF.')
        except:
            logging.fatal('Failed to stop rCTF.', exc_info = True)
            exit(1)
    elif subcommand in ['update', 'upgrade']:
        logging.info('Upgrading rCTF instance...')

        try:
            instance.upgrade()

            logging.info('Successfully updated instance.')
            logging.info('Upgrading %s CLI tool...' % colored_command(sys.argv[0]))

            # XXX: possible argument injection probably not worth fixing
            execute(['cp', 'install/rctf.py', sys.argv[0]])
            execute(['chmod', '+x', sys.argv[0]])

            logging.info('Finished. Run ', colored_command(sys.argv[0] + ' up'), ' to start the rCTF instance again.' % sys.argv[0])
        except:
            logging.fatal('Failed to upgrade rCTF.', exc_info = True)
            exit(1)
    elif subcommand in ['config', 'configure']:
        if args.editor:
            editor = get_editor()

            if not verify_privileges():
                logging.warning('You may not have proper permissions to access the rCTF installation.')

            if not read_config:
                logging.exception('You do not have proper permission to access the config file ', colored_command(instance.config_path), '.')
                exit(1)

            execute([editor, rctf.config_path])

            logging.info('Note: You may have to restart rCTF for the changes to take effect.')
        else:
            unset = args.unset
            delete = args.delete
            _key = args.key
            _value = args.value

            if unset and not _key:
                logging.error('The argument ', colored_command('--unset'), ' must be used with a key.')
                exit(1)

            if not read_config:
                logging.exception('You do not have proper permission to access the config file ', colored_command(rctf.config_path), '.')
                exit(1)

            format_config = lambda key, value : (
                colored(str(key), ['bold', 'red']) + colored(' => ', ['bold_white']) + (
                    colored('(unset)', ['gray', 'italics']) if value == None else colored(str(value), ['red'])
                )
            )

            if not _key:
                # print out whole config
                for key, value in config.items():
                    logging.info(format_config(key, value))
            else:
                if delete:
                    del config[_key]
                    config.write()
                elif _value or unset:
                    # write to config
                    if unset:
                        _value = None

                    config[_key] = _value
                    config.write()
                else:
                    _value = config.get(_key)

                logging.info(format_config(_key, _value))
