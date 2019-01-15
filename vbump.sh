#!/bin/sh
sed -E -i "s/^(__version__ = ').+'$/\1$1'/" essex/__init__.py
sed -E -i "s/^( *VERSION = ')(\.|[0-9])+'(.*)/\1$1'\3/" essex/essex.py
sed -E -i "s/^(VER=).*/\1$1/" mkbin.sh
echo "Remember to update the help output in README.rst"
