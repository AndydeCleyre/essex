#!/usr/bin/env python3
import sys
from contextlib import suppress
from hashlib import md5

from plumbum import local, CommandNotFound
from plumbum.cli import Application, Flag, SwitchAttr, Range, Set
from plumbum.colors import blue, magenta, green, red, yellow
from plumbum.cmd import (
    s6_log, s6_svc, s6_svscan, s6_svscanctl, s6_svstat,
    fdmove, lsof, pstree, tail
)

# TO DO / CONSIDER:
# .s6-svscan/crash?
# .s6-svscan/finish poweroff? (kill after timeout?)
# check env var for SVCS_PATHS?
# EssexOff doesn't wait for hanging procs?


def warn(out='', err=''):
    print('\n'.join(filter(None, (out, err))).strip() | red, file=sys.stderr)


def fail(r, out='', err=''):
    warn(out, err)
    sys.exit(r)


class ColorApp(Application):
    PROGNAME = green
    VERSION = '0.1.1' | blue
    COLOR_USAGE = green
    COLOR_GROUPS = {
        'Meta-switches': magenta,
        'Switches': yellow,
        'Subcommands': blue
    }
    ALLOW_ABBREV = True


class Essex(ColorApp):
    """Simply manage services"""

    SUBCOMMAND_HELPMSG = False
    DEFAULT_PATHS = ('./svcs', '~/svcs', '/etc/svcs', '/svcs')

    svcs_dir = SwitchAttr(
        ['d', 'directory'],
        argname='SERVICES_DIRECTORY',
        help=(
            "folder of services to manage; "
            f"the default is the first existing match from {DEFAULT_PATHS}, "
            "unless a colon-delimited SERVICES_PATHS env var exists;"
        )
    )

    logs_dir = SwitchAttr(
        ['l', 'logs-directory'],
        argname='SERVICES_LOGS_DIRECTORY',
        help=(
            "folder of services' log files; "
            f"the default is SERVICES_DIRECTORY/../svcs-logs"
        )
    )

    def main(self):
        if self.svcs_dir:
            self.svcs_dir = local.path(self.svcs_dir)
        else:
            try:
                svcs_paths = local.env['SERVICES_PATHS'].split(':')
            except KeyError:
                svcs_paths = self.DEFAULT_PATHS
            for folder in map(local.path, svcs_paths):
                if folder.is_dir():
                    self.svcs_dir = folder
                    break
            else:
                self.svcs_dir = local.path(svcs_paths[0])
        self.svcs_dir.mkdir()
        self.logs_dir = self.logs_dir or self.svcs_dir.up() / 'svcs-logs'
        self.svcs = tuple(f for f in self.svcs_dir if 'run' in f)

    def fail_if_unsupervised(self):
        r, out, err = s6_svscanctl[self.svcs_dir].run(retcode=None)
        if r == 100:
            fail(1, f"{self.svcs_dir} not currently supervised.")
        elif r:
            fail(r, out, err)

    def svc_map(self, svc_names):
        return (self.svcs_dir / sn for sn in svc_names)


class Stopper(ColorApp):

    fail_after = SwitchAttr(
        ['f', 'fail-after'],
        float,
        argname='SECONDS',
        help=(
            "exit with code 1 if a service hasn't died after SECONDS seconds; "
            f"if 0, will not move on until the process dies"
        ),
        default=0,
        excludes=['kill-after']
    )

    kill_after = SwitchAttr(
        ['k', 'kill-after'],
        float,
        argname='SECONDS',
        help=(
            "send a kill signal (9) if a service hasn't died after SECONDS seconds; "
            f"if 0, will not move on until the process dies"
        ),
        default=0,
        excludes=['fail-after']
    )

    def stop(self, svc, announce=False):
        if announce:
            print("Stopping", svc, ". . .")
        self.fail_after = self.fail_after or self.kill_after
        r, out, err = s6_svc['-wD', '-d', '-T', int(self.fail_after * 1000), svc].run(retcode=None)
        if r == 99:
            warn(f"{svc} didn't stop in time!")
            if self.kill_after:
                warn(f"Sending kill signal to {svc}!")
                s6_svc['-k', svc].run_fg()
            else:
                fail(1, "Aborting!")
        elif r:
            fail(r, out, err)

    def is_up(self, svc):
        return s6_svstat('-o', 'up', svc).strip() == 'true'


class Starter(ColorApp):

    def start(self, svc, announce=False, timeout=0):
        # timeout not currently used
        if announce:
            print("Starting", svc)
        # s6_svc['-u', '-wu', '-T', timeout * 1000, svc].run_fg()
        r, out, err = s6_svc['-u', '-wu', '-T', timeout * 1000, svc].run(retcode=None)
        if r:
            fail(r, out, err)
            # warn(out, err)


@Essex.subcommand('cat')
class EssexCat(ColorApp):
    """View services' run, finish, and log commands"""

    no_color = Flag(
        ['n', 'no-color'],
        help="do not colorize the output (for piping)"
    )

    def display(self, docpath):
        title_cat = tail['-vn', '+1', docpath]
        if self.no_color:
            title_cat.run_fg()
        else:
            try:
                (
                    title_cat |
                    local['highlight'][
                        '--stdout', '-O', 'truecolor', '-s', 'lucretia', '-S', 'sh'
                    ]
                ).run_fg()
            except CommandNotFound:
                try:
                    (
                        title_cat |
                        local['bat']['-p', '-l', 'sh']
                    ).run_fg()
                except CommandNotFound:
                    title_cat.run_fg()
        print('\n')

    def main(self, svc_name, *extra_svc_names):
        for svc in self.parent.svc_map((svc_name, *extra_svc_names)):
            for file in ('run', 'finish', 'crash'):
                # if (doc := svc / file).is_file():
                doc = svc / file  #
                if doc.is_file():  #
                    self.display(doc)
            # if (logger := svc / 'log' / 'run').is_file():
            logger = svc / 'log' / 'run'  #
            if logger.is_file():  #
                self.display(logger)


@Essex.subcommand('start')
class EssexStart(Starter):
    """Start individual services"""

    def main(self, svc_name, *extra_svc_names):
        self.parent.fail_if_unsupervised()
        s6_svscanctl('-a', self.parent.svcs_dir)
        for svc in self.parent.svc_map((svc_name, *extra_svc_names)):
            self.start(svc)


@Essex.subcommand('stop')
class EssexStop(Stopper):
    """Stop individual services"""

    def main(self, svc_name, *extra_svc_names):
        for svc in self.parent.svc_map((svc_name, *extra_svc_names)):
            self.stop(svc, announce=True)


@Essex.subcommand('list')
class EssexList(ColorApp):
    """List all known services"""

    enabled_only = Flag(
        ['e', 'enabled'],
        help="only list enabled services (configured to be running)"
    )

    def main(self):
        if self.parent.svcs_dir.is_dir():
            if self.enabled_only:
                print(*(s for s in self.parent.svcs if 'down' not in s), sep='\n')
            else:
                print(*self.parent.svcs, sep='\n')


@Essex.subcommand('status')
class EssexStatus(ColorApp):
    """View the current states of (all or specified) services"""

    enabled_only = Flag(
        ['e', 'enabled'],
        help="only list enabled services (configured to be running)"
    )

    def main(self, *svc_names):
        self.parent.fail_if_unsupervised()
        s6_svscanctl('-a', self.parent.svcs_dir)
        cols = (
            'up', 'wantedup', 'normallyup', 'ready', 'paused', 'pid',
            'exitcode', 'signal', 'signum', 'updownsince', 'readysince',
            'updownfor', 'readyfor'
        )
        errors = False
        for svc in self.parent.svc_map(svc_names or self.parent.svcs):
            if 'run' in svc:
                if self.enabled_only and 'down' in svc:
                    continue
                stats = {
                    col: False if val == 'false' else val
                    for col, val in zip(
                        cols, s6_svstat('-o', ','.join(cols), svc).split()
                    )
                }
                statline = f"{svc.name:<20} {'up' if stats['up'] else 'down':<5} {stats['updownfor'] + 's':<10} {stats['pid'] if stats['pid'] != '-1' else stats['exitcode']:<6} {'autorestarts' if stats['wantedup'] else '':<13} {'autostarts' if stats['normallyup'] else '':<11}"
                print(statline | (green if stats['up'] else red))
            else:
                warn(f"{svc} doesn't exist")
                errors = True
        if errors:
            fail(1)


@Essex.subcommand('tree')
class EssexTree(ColorApp):
    """View the process tree from the supervision root"""

    def main(self):
        self.parent.fail_if_unsupervised()
        pstree[
            '-apT', lsof('-t', self.parent.svcs_dir / '.s6-svscan' / 'control').splitlines()[0]
        ].run_fg()


@Essex.subcommand('enable')
class EssexEnable(ColorApp):
    """Configure individual services to be up, without actually starting them"""

    def main(self, svc_name, *extra_svc_names):
        errors = False
        for svc in self.parent.svc_map((svc_name, *extra_svc_names)):
            if svc.is_dir():
                (svc / 'down').delete()
            else:
                warn(f"{svc} doesn't exist")
                errors = True
        if errors:
            fail(1)


@Essex.subcommand('disable')
class EssexDisable(ColorApp):
    """Configure individual services to be down, without actually stopping them"""

    def main(self, svc_name, *extra_svc_names):
        errors = False
        for svc in self.parent.svc_map((svc_name, *extra_svc_names)):
            if svc.is_dir():
                (svc / 'down').touch()
            else:
                warn(f"{svc} doesn't exist")
                errors = True
        if errors:
            fail(1)


@Essex.subcommand('on')
class EssexOn(ColorApp):
    """Start supervising all services"""

    def main(self):
        r, out, err = s6_svscanctl[self.parent.svcs_dir].run(retcode=None)
        if r == 100:
            (
                fdmove['-c', '2', '1'][s6_svscan][self.parent.svcs_dir] |
                s6_log['T', self.parent.logs_dir / '.s6-svscan']
            ).run_bg()
        elif r:
            fail(r, out, err)
        else:
            warn(f"{self.parent.svcs_dir} already supervised")


@Essex.subcommand('off')
class EssexOff(Stopper):
    """Stop all services and their supervision"""

    def main(self):
        self.parent.fail_if_unsupervised()
        for svc in self.parent.svcs:
            self.stop(svc, announce=self.is_up(svc))
            # yes, even when not is_up, to catch failed-start loops
        s6_svscanctl['-anpt', self.parent.svcs_dir].run_fg()


@Essex.subcommand('sync')
class EssexSync(Stopper, Starter):
    """Start or stop services to match their configuration"""

    def main(self, *svc_names):
        self.parent.fail_if_unsupervised()
        s6_svscanctl['-an', self.parent.svcs_dir].run_fg()
        for svc in self.parent.svc_map(svc_names or self.parent.svcs):
            is_up = self.is_up(svc)
            if (svc / 'down').exists():
                self.stop(svc, announce=is_up)
                # yes, even when not is_up, to catch failed-start loops
            elif not is_up:
                self.start(svc, announce=True)


@Essex.subcommand('reload')
class EssexReload(Stopper, Starter):
    """Restart (all or specified) running services whose run scripts have changed"""

    def main(self, *svc_names):
        self.parent.fail_if_unsupervised()
        for svc in self.parent.svc_map(svc_names or self.parent.svcs):
            if self.is_up(svc):
                for run, run_md5 in (
                    (svc / 'run', svc / 'run.md5'),
                    (svc / 'log' / 'run', svc / 'log' / 'run.md5')
                ):
                    if run_md5.is_file():
                        if md5(run.read().encode()).hexdigest() != run_md5.read().split()[0]:
                            self.stop(svc, announce=True)
                            self.start(svc, announce=True)
                            break


@Essex.subcommand('log')
class EssexLog(ColorApp):
    """View a service's log"""

    lines = SwitchAttr(
        ['n', 'lines'],
        argname='LINES',
        help=(
            "print only the last LINES lines from the service's current log file, "
            "or prepend a '+' to start at line LINES"
        ),
        default='+1'
    )

    follow = Flag(
        ['f', 'follow'],
        help="continue printing new lines as they are added to the log file"
    )

    all_logs = Flag(['a', 'all'], help="view logs from all services")

    def main(self, svc_name='.s6-svscan', *extra_svc_names):
        if self.all_logs:
            logs = [
                self.parent.logs_dir / svc.name / 'current'
                for svc in self.parent.svcs + (self.parent.svcs_dir / '.s6-svscan',)
            ]
        else:
            logs = [
                self.parent.logs_dir / sn / 'current'
                for sn in (svc_name, *extra_svc_names)
            ]
        if self.follow:
            with suppress(KeyboardInterrupt):
                try:
                    mtail = local.get('lnav', 'multitail')
                except CommandNotFound:
                    tail[['-n', self.lines, '-F'] + logs].run_fg()
                else:
                    mtail[logs].run_fg()
        else:
            for log in logs:
                if log.is_file():
                    tail['-vn', self.lines, log].run_fg()
                    print('\n')


@Essex.subcommand('sig')
class EssexSignal(ColorApp):
    """Send a signal to a service"""

    sigs = {
        'alrm': 'a', 'abrt': 'b', 'quit': 'q',
        'hup': 'h', 'kill': 'k', 'term': 't',
        'int': 'i', 'usr1': '1', 'usr2': '2',
        'stop': 'p', 'cont': 'c', 'winch': 'y'
    }

    def main(self, signal: Set(*sigs), svc_name, *extra_svc_names):
        self.parent.fail_if_unsupervised()
        sig = self.sigs[signal.lower()]
        for svc in self.parent.svc_map((svc_name, *extra_svc_names)):
            s6_svc[f'-{sig}', svc].run_fg()


def columnize_comments(*line_pairs):
    col2_at = max(len(code) for code, comment in line_pairs) + 2
    return '\n'.join(
        f"{code}{' ' * (col2_at - len(code))}{'# ' * bool(comment)}{comment}"
        for code, comment in line_pairs
    )


@Essex.subcommand('new')
class EssexNew(ColorApp):
    """Create a new service"""

    working_dir = SwitchAttr(
        ['d', 'working-dir'],
        argname='WORKING_DIRECTORY',
        help=(
            "run the process from inside this folder; "
            "the default is SERVICES_DIRECTORY/svc_name"
        )
    )

    as_user = SwitchAttr(
        ['u', 'as-user'],
        argname='USERNAME',
        help="non-root user to run the new service as (only works for root)"
    )

    enabled = Flag(
        ['e', 'enable'], help="enable the new service after creation"
    )

    on_finish = SwitchAttr(
        ['f', 'finish'],
        argname='FINISH_CMD',
        help=(
            "command to run whenever the supervised process dies "
            "(must complete in under 5 seconds)"
        )
    )

    rotate_at = SwitchAttr(
        ['r', 'rotate-at'],
        Range(1, 256),
        argname='MEBIBYTES',
        help="archive each log file when it reaches MEBIBYTES mebibytes",
        default=4
    )

    prune_at = SwitchAttr(
        ['p', 'prune-at'],
        Range(0, 1024),
        argname='MEBIBYTES',
        help=(
            "keep up to MEBIBYTES mebibytes of logs before deleting the oldest; "
            "0 means never prune"
        ),
        default=40
    )

    on_rotate = SwitchAttr(
        ['o', 'on-rotate'],
        argname='PROCESSOR_CMD',
        help=(
            "processor command to run when rotating logs; "
            "receives log via stdin; "
            "its stdout is archived; "
            "PROCESSOR_CMD will be double-quoted"
        )
    )

    # TODO: use skabus-dyntee for socket-logging? maybe
    def main(self, svc_name, cmd):
        self.svc = self.parent.svcs_dir / svc_name
        if self.svc.exists():
            fail(1, f"{self.svc} already exists!")
        self.cmd = cmd
        self.mk_runfile()
        self.mk_logger()
        if not self.enabled:
            (self.svc / 'down').touch()

    def mk_runfile(self):
        self.svc.mkdir()
        runfile = self.svc / 'run'
        shebang = ('#!/bin/execlineb -P', '')
        hash_run = (
            'foreground { redirfd -w 1 run.md5 md5sum run }',
            "Generate hashfile, to detect changes since launch"
        )
        err_to_out = ('fdmove -c 2 1', "Send stderr to stdout")
        set_user = (
            f's6-setuidgid {self.as_user}', "Run as this user"
        ) if self.as_user else None
        working_dir = (
            f'cd {local.path(self.working_dir)}', "Enter working directory"
        ) if self.working_dir else None
        runfile.write(columnize_comments(*filter(None, (
            shebang, hash_run, err_to_out, set_user, working_dir, (self.cmd, "Do the thing")
        ))))
        runfile.chmod(0o755)
        if self.on_finish:
            runfile = self.svc / 'finish'
            runfile.write(columnize_comments(*filter(None, (
                ('#!/bin/execlineb', ''), err_to_out, set_user, (self.on_finish, "Do the thing")
            ))))
            runfile.chmod(0o755)

    def mk_logger(self):
        logger = self.svc / 'log'
        logger.mkdir()
        # (self.parent.logs_dir / self.svc.name).mkdir()
        runfile = logger / 'run'
        shebang = ('#!/bin/execlineb -P', '')
        hash_run = (
            'foreground { redirfd -w 1 run.md5 md5sum run }',
            "Generate hashfile, to detect changes since launch"
        )
        receive = ('s6-log', "Receive process output")
        timestamp = ('  T', "Start each line with an ISO 8601 timestamp")
        rotate = (
            f'  s{self.rotate_at * 1024 ** 2}',
            "Archive log when it gets this big (bytes)"
        )
        prune = (
            f'  S{self.prune_at * 1024 ** 2}',
            "Purge oldest archived logs when the archive gets this big (bytes)"
        )
        process = (
            f'!"{self.on_rotate}"',
            "Processor (log --stdin--> processor --stdout--> archive)"
        ) if self.on_rotate else None
        logfile = (f'  {self.parent.logs_dir / self.svc.name}', "Store logs here")
        runfile.write(columnize_comments(*filter(None, (
            shebang, hash_run, receive, timestamp, rotate, prune, process, logfile
        ))))
        runfile.chmod(0o755)


def main():
    for app in (
        EssexCat, EssexDisable, EssexEnable, EssexList, EssexLog, EssexNew,
        EssexOff, EssexOn, EssexSignal, EssexStart, EssexStatus, EssexStop,
        EssexSync, EssexTree
    ):
        app.unbind_switches('help-all', 'v', 'version')
    Essex()


if __name__ == '__main__':
    main()

