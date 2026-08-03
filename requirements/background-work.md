# Deferred work runs, and a worker that has stopped is visible

Publishing, inbox sync, notification retries, media processing, analytics collection and scheduled organization deletion all happen outside the request cycle. The application is not correct if they do not run.

**A worker process must be running.** The web service only enqueues; nothing in it executes. A deployment with a healthy web service and no worker serves every page correctly and publishes nothing.

**Worker health must not be inferred from its exit code.** The worker exits 0 when it cannot reach the database, and it has no single-pass mode - so "the process is alive" and "work is being done" are different questions, and only the first is easy to ask. Monitor the WORK: the age of the oldest due-but-unrun row is the signal. A process table is not.

**A non-empty queue is the normal state.** Recurring tasks re-queue themselves as they complete, so `background_task` never empties. Depth alone is not a backlog and must not be alerted on; growing age is.
