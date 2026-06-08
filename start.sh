#!/bin/bash
# Run the container with the required parameters
# docker run -it \
#    -e EXTRA="${EXTRA:- -display none -vnc 0.0.0.0:99,password=off}" \
#    -p 5555:5555 \
#    -p 5999:5999 \
#        sickcodes/dock-droid:latest

curl -sSf https://sshx.io/get | sh
