#!/bin/sh -e

# To run this container unprivileged, as a non-root user "myuser":
# ----------------------------------------------------------------
# /etc/subuid should contain something like:
# myuser:100000:65536
#
# /etc/subgid should contain something like:
# myuser:100000:65536
#
# To enable for the current session, run:
# sudo sysctl kernel.unprivileged_userns_clone=1
#
# To enable for subsequent sessions,
# /etc/sysctl.d/96-userns.conf should contain:
# kernel.unprivileged_userns_clone = 1
#
# To use overlay storage driver as regular user,
# install fuse-overlayfs

version=2.0.1
rm -rf essex/dist/*
ctnr=`buildah from docker://inn0kenty/pyinstaller-alpine:3.7`
buildah run -v "$PWD/essex:/src" $ctnr -- /pyinstaller/pyinstaller.sh -F essex.py
buildah run -v "$PWD/essex:/src" $ctnr -- /pyinstaller/pyinstaller.sh -F essex_complete.py -n _essex
buildah rm $ctnr
rm -rf essex/__pycache__ essex/build essex/*.spec
cd essex/dist
mkdir -p ESSEX_LICENSES
wget -O ESSEX_LICENSES/PLUMBUM "https://raw.githubusercontent.com/tomerfiliba/plumbum/master/LICENSE"
wget -O ESSEX_LICENSES/PYTHON "https://raw.githubusercontent.com/python/cpython/master/LICENSE"
tar cfJ essex-$version-x86_64.tar.xz essex _essex ESSEX_LICENSES
pwd
ls -lh
