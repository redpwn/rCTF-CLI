#!/usr/bin/env python3

from . import logger

import os, sys, traceback
import subprocess, selectors

# XXX: this is quite a hack
logging = logger.logging
colored = logger.colored
colored_command = logger.colored_command
colors = logger.colors
log_levels = logger.log_levels
strip_ansi = logger.strip_ansi


# define useful functions


def verify_privileges(euid = 0):
    return os.geteuid() == euid


def check_file(fn):
    # verifies a file exists
    return os.path.isfile(fn)


'''
find an editor to use, first from $EDITOR then try to find a suitable text editor
:return: the path to a suitable text editor
'''
def get_editor():
    editor = os.environ.get('EDITOR')
    try_editors = ['/usr/bin/vim', '/usr/bin/nano']

    for test_editor in try_editors:
        if editor:
            break

        if check_file(test_editor):
            editor = test_editor

    if not editor:
        raise RuntimeError('No $EDITOR configured and no editors discovered.')

    return editor


'''
executes a shell command

:arg command: a str or list with the command
:arg environ: a dict add to runtime environmental variables
:return: whether or not the command was successful based on status code
'''
def execute(command, environ = None):
    logging.debug('Executing ', colored_command(command), '...')

    if not environ:
        environ = os.environ.copy()

    # shell=False if list, shell=True if str
    if isinstance(command, str):
        command = ['/bin/sh', '-c', command]

    p = subprocess.Popen(command, shell = False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, env = environ)

    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ)
    sel.register(p.stderr, selectors.EVENT_READ)

    should_exit = False
    should_print_bars = False

    # use selectors to print stderr/stdout as we get them
    while True:
        if should_exit:
            break

        for key, _ in sel.select():
            data = key.fileobj.read1().decode()

            if not data:
                should_exit = True
                break

            data = strip_ansi(data.strip())

            prompt = ' *  '
            data = data.replace('\n', '\n' + prompt)

            if not should_print_bars:
                logging.debug('-'*80, prompt = ' *--')
                should_print_bars = True

            if key.fileobj is p.stdout:
                # stdout
                logging.debug(colored(data, ['italics']), prompt = prompt)
            else:
                # stderr
                logging.debug(colored(data, ['italics', 'bold']), prompt = prompt)

    p.communicate()
    status_code = p.returncode

    # only print bars if we read something
    if should_print_bars:
        logging.debug('-'*80, prompt = ' *--')

    if status_code:
        logging.error('Command failed to execute; exited with status code ', colored_command(status_code), '.')

    # XXX: check to make sure this status code isn't just docker?
    if status_code == 1 and not verify_privileges(): # permission denied
        logging.warning('Possible permission denied error? Try running as root.\n\n    %s\n' % colored_command(' '.join(sys.argv)))
        raise PermissionError('Permission denied. Try running as root.')


    return status_code == 0


from . import rctf, config
