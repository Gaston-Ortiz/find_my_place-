#!/bin/bash
set -e

# The container stops if the migrations fail
alembic -c web_scraper/alembic.ini upgrade head

# cron jobs don't inherit the container's environment
(umask 077 && export -p | grep -E '^declare -x DATABASE_URL=' > /app/cron_env.sh)

# logs_files is a volume, so the log can't be created in the image
touch /app/logs_files/cron.log

cron
exec tail -f /app/logs_files/cron.log
