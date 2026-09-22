# Sourced by Heroku before the dyno's command runs, for every process type —
# web, worker, the release phase, and one-off `heroku run` dynos.
#
# glibc hands each thread its own malloc arena, up to 8 x nproc, and a dyno
# reports the host's core count rather than its own share. Arenas are never
# returned to the OS, so on a process with real thread churn — the publisher
# builds a fresh ThreadPoolExecutor every 15s, and boto3's managed transfer
# adds ten threads per download — RSS ratchets upward and never comes back.
# That is what put the 512MB worker at 110% of quota with 3081 R14s in a day.
#
# Set as a DEFAULT, not an override: .profile is sourced after config vars are
# injected, so a bare assignment would silently stomp a value set from the
# dashboard and make this untunable without a deploy.
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
