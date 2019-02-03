Essex
=====

A command line interface for creating & managing s6 services, using the s6 toolset

Dependencies:

	- Python 3.6+
	- Plumbum
	- s6
	- BusyBox or (lsof, psmisc, coreutils)
	- musl-utils or glibc

Optional Dependencies:

	- lnav or multitail
	- highlight or bat

`Demo Video`_

.. _Demo Video: https://streamable.com/oek3d

Installation
------------

From PyPI:

.. code-block:: sh

    pip install essex
    # activate bash completion:
    complete -o dirnames -C _essex essex

From 64-bit musl binary release:

.. code-block:: sh

    wget "https://github.com/AndydeCleyre/essex/releases/download/1.1.0/essex-1.1.0-x86_64.tar.xz" -O - | tar xJf - -C /usr/local/bin
    rm /usr/local/bin/plumbum_license  # MIT
    complete -o dirnames -C _essex essex  # bash completion

Usage
-----

::

    essex 1.1.0

    Simply manage services

    Usage:
        essex [SWITCHES] [SUBCOMMAND [SWITCHES]]

    Meta-switches:
        -h, --help                                            Prints this help message and quits
        --help-all                                            Prints help messages of all sub-commands and quits
        -v, --version                                         Prints the program's version and quits

    Switches:
        -d, --directory SERVICES_DIRECTORY:str                folder of services to manage; the default is the first existing match from ('./svcs', '~/svcs',
                                                              '/var/svcs', '/svcs'), unless a colon-delimited SERVICES_PATHS env var exists;
        -l, --logs-directory SERVICES_LOGS_DIRECTORY:str      folder of services' log files; the default is SERVICES_DIRECTORY/../svcs-logs

    Sub-commands:
        cat                                                   View services' run, finish, and log commands; Alias for print
        disable                                               Configure individual services to be down, without actually stopping them
        enable                                                Configure individual services to be up, without actually starting them
        list                                                  List all known services
        log                                                   View a service's log
        new                                                   Create a new service
        off                                                   Stop all services and their supervision
        on                                                    Start supervising all services
        print                                                 View services' run, finish, and log commands
        pt                                                    Print a sample Papertrail log_files.yml
        reload                                                Restart (all or specified) running services whose run scripts have changed; Depends on the runfile
                                                              generating an adjacent run.md5 file, like essex-generated runfiles do
        sig                                                   Send a signal to a service
        start                                                 Start individual services
        status                                                View the current states of (all or specified) services
        stop                                                  Stop individual services
        sync                                                  Start or stop services to match their configuration
        tree                                                  View the process tree from the supervision root

Packaging
---------

.. code-block:: sh

    pip install -r requirements.txt
    # Edit pyproject.toml as desired.
    # Create a wheel and source distribution in dist/:
    flit build
    # Create a wheel and source distribution in dist/ AND upload to PyPI:
    flit publish

One can build a single-file executable suitable for dropping into an Alpine-based container
with s6 (no Python or Plumbum necessary), using Docker and `pyinstaller-alpine`_.

.. _pyinstaller-alpine: https://github.com/inn0kenty/pyinstaller-alpine

From the inner `essex` folder:

.. code-block:: sh

    docker run --rm -v "${PWD}:/src" inn0kenty/pyinstaller-alpine:3.7 -F --clean ./essex.py

It comes out to ~10MB. Alternatively, a build script using the same image,
but Buildah rather than Docker, is included as `mkbin.sh`.
