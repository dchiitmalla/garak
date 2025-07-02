#!/bin/bash
set -e

# If the first argument is 'garak', pass all arguments directly to garak
if [ "$1" = "garak" ]; then
    exec "$@"
# If no arguments, just keep the container running
elif [ "$#" -eq 0 ]; then
    exec tail -f /dev/null
# Otherwise, run the command with bash
else
    exec "$@"
fi
