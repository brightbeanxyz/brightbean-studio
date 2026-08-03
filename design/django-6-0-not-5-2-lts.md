# Target Django 6.0 rather than the 5.2 LTS

**Chosen:** Django 6.0.7.

**The comparison is NOT 6.0 against a supported 5.2, and reading it that way inverts the answer.** This application is on **5.1**, which left extended support in December 2025. There is no do-nothing option and no cheap option: both candidate targets cost exactly one migration from here.

So the question is which line that migration puts us ON. 5.2 is a terminal branch - it is supported to April 2028 and then has to be left, at the cost of a SECOND migration, to reach whatever LTS follows. 6.0 is the live line, and 6.2 LTS is reachable directly from it. Taking 6.0 now is the shortest path to LTS status, not a detour from one.

**What it costs, stated plainly.** 6.0's mainstream support ended in August 2026; it receives security fixes only, until April 2027. That is a real window and it is short, which is why the 6.2 step below is a commitment rather than an aspiration. It is not, however, 'eight months less runway than the LTS' - that phrasing compares against a position this application has never occupied.

**What it buys, and this is smaller than it was.** Core CSP lands in 6.0, and it lets this migration DELETE `django-csp` instead of upgrading it. The settings have to be rewritten either way - moving to django-csp 4.x means the same flat-to-nested rewrite - so the identical work buys a dependency removal on 6.0 and a dependency retention on 5.2.

That is the whole of the technical differentiator. The background task system is explicitly NOT one: `django-background-tasks` is retained and runs unchanged on either target, so it gives no reason to prefer 6.0 over 5.2. Core `django.tasks` is not a factor here - it ships no durable backend and no scheduler, so adopting it would be a project of its own rather than a benefit of arriving.

**So state the cost without the false comparison.** It is NOT '6.0 has less runway than 5.2'. That sets 6.0's window against a position this application has never held, and it prices the two targets as though they were the same KIND of thing. They are not: 5.2 is terminal, and reaching an LTS from there costs a SECOND migration about the size of this one, while from 6.0 the LTS is a minor-version step. Counting calendar months to 2028 and stopping there hides that second migration entirely.

The real cost is DISCIPLINE. Taking 6.0 obliges the project to move through 6.1 and 6.2 roughly on schedule - and that is the same obligation which was not met on 5.1, which is the only reason this migration exists. If minor upgrades will not be taken on time, 5.2 buys idle years and then presents the same bill with interest. That is the question worth re-opening, and it is a question about how the project is run, not about which dates are printed on a support table.

**Consequence to plan for.** 6.2 LTS is due April 2027, inside 6.0's security window. The intended path is 6.0 -> 6.2 LTS, not 6.0 -> 6.1.
