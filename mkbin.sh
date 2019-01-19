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

version=0.2.2
ctnr=`buildah from docker://inn0kenty/pyinstaller-alpine:3.7`
buildah run -v "$PWD/essex:/src" $ctnr -- /pyinstaller/pyinstaller.sh -F essex.py
buildah rm $ctnr
rm -rf essex/__pycache__ essex/build essex/essex.spec
cd essex/dist
tar cfJ essex-$version-x86_64.tar.xz essex
