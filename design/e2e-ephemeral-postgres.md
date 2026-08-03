# The e2e suite stands up its own PostgreSQL cluster

**Chosen:** `initdb` into a temporary directory, `pg_ctl` on a free port, trust authentication, torn down when the session ends. Roughly 4.4 seconds, measured.

**Why not a shared local server.** It would need credentials, it would need to already exist, and two runs would collide. "Ephemeral" means the harness owns the server, which is precisely what removes the configuration.

**Why not Docker.** It is separate infrastructure with its own daemon and its own state, and introducing it is not a decision the test suite gets to make on a developer's machine.

**Why not pytest-postgresql.** Ruled out on evidence, not preference: on Windows it launches the server with `-c log_destination='stderr'` and nothing strips the quotes, so the server rejects its own configuration with `invalid value for parameter "log_destination"`.

**Three things the hand-rolled fixture must keep doing.** No quoted values in `pg_ctl -o`. No pipe for `pg_ctl start` - the daemonised server inherits the handle and holds it open forever, so the caller blocks on an EOF that never comes. And decode output with `errors="replace"`, because postgres emits messages in the operating system's language and a UTF-8 assumption dies on the first umlaut.
