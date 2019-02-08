#!/bin/sh
if [[ "$#" -eq 0 ]]; then
    echo "Provide new version as argument"
    exit 1
fi
sed -E -i "s/^(__version__ = ')(\.|[0-9])*('.*)/\1$1\3/" essex/__init__.py
sed -E -i "s/^( *VERSION = ')(\.|[0-9])*('.*)/\1$1\3/" essex/essex.py
sed -E -i "s/^(version=).*/\1$1/" mkbin.sh
sed -E -i "s:(/releases/download/)(\.|[0-9])*(/essex-)(\.|[0-9])*(-):\1$1\3$1\5:" README.rst
./essex/essex.py --help-all | sed 's/essex.py/essex/' > docs/help-all.txt
echo "Remember to update the help output in README.rst"
