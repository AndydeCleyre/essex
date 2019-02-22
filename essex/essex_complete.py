#!/usr/bin/env python3

import shlex
from sys import argv
from itertools import count
from collections import defaultdict

from plumbum import local


subcommands = (
    'cat', 'disable', 'enable', 'list', 'log', 'new', 'off', 'on', 'pid',
    'print', 'reload', 'sig', 'start', 'status', 'stop', 'sync', 'tree', 'upgrade'
)
signals = (
    'alrm', 'abrt', 'quit', 'hup', 'kill', 'term', 'int',
    'usr1', 'usr2', 'stop', 'cont', 'winch'
)

# Declare switches, which take arguments
stop_cmds = ('off', 'reload', 'stop', 'sync', 'upgrade')
opts = defaultdict(tuple, {
    sc: ('-f', '--fail-after', '-k', '--kill-after') for sc in stop_cmds
})
opts.update({
    'essex': ('-d', '--directory', '-l', '--logs-directory'),
    'log': ('-n', '--lines'),
    'new': (
        '-d', '--working-dir', '-f', '--finish', '-o', '--on-rotate',
        '-p', '--prune-at', '-r', '--rotate-at', '-u', '--as-user', '-s', '--store'
    )
})

# Declare flags, which take no arguments. All svcs have -h, --help
hlp = ('-h', '--help')
flags = defaultdict(lambda: hlp)
flags['cat'] += ('-n', '--no-color', '-r', '--run-only', '-e', '--enabled')
flags['log'] += ('-f', '--follow', '-d', '--debug')
flags['new'] += ('-e', '--enable')
flags['list'] += ('-e', '--enabled')
flags['print'] += ('-n', '--no-color', '-r', '--run-only', '-e', '--enabled')
flags['status'] += ('-e', '--enabled')
flags['tree'] += ('-q', '--quiet')


def get_subcmd(words):
    subcmd = 'essex'
    for idx in count(1):
        if idx == len(words):
            return subcmd
        if all((
            words[idx] not in (*opts['essex'], *flags['essex']),
            words[idx - 1] not in opts['essex'],
            words[idx] in subcommands
        )):
            return words[idx]


def get_svcs_dir(words, defaults=('./svcs', '~/svcs', '/var/svcs', '/svcs')):
    for idx in (1, 3):
        if idx < len(words) and words[idx] in ('-d', '--directory'):
            return local.path(words[idx + 1])
    try:
        svcs_paths = local.env['SERVICES_PATHS'].split(':')
    except KeyError:
        svcs_paths = defaults
    for folder in map(local.path, svcs_paths):
        if folder.is_dir():
            return folder
    return local.path(svcs_paths[0])


def get_svcs(words):
    return tuple(f for f in get_svcs_dir(words) if 'run' in f)


def main():
    cmd, partial_word, prev_word = argv[1:]
    line = local.env['COMP_LINE']
    suggestions = []
    words = shlex.split(line)
    subcmd = get_subcmd(words)
    suggestions.extend(
        opt for opt in (*opts[subcmd], *flags[subcmd])
        if opt.startswith(partial_word)
    )
    if prev_word in (*opts[subcmd], *hlp):
        suggestions.clear()
    elif subcmd == 'essex':
        suggestions.extend(
            sc for sc in subcommands
            if sc.startswith(partial_word)
        )
    elif subcmd == 'sig' and prev_word == 'sig':
        suggestions.extend(
            sig for sig in signals
            if sig.startswith(partial_word)
        )
    elif subcmd not in ('list', 'new', 'off', 'on', 'tree'):
        suggestions.extend(
            svc.name for svc in get_svcs(words)
            if svc.name.startswith(partial_word)
        )
    if subcmd == 'new' and prev_word in ('-u', '--as-user'):
        suggestions.extend(
            line.split(':')[0]
            for line in local.path('/etc/passwd').read().splitlines()
        )
    print('\n'.join(suggestions))


if __name__ == '__main__':
    main()
