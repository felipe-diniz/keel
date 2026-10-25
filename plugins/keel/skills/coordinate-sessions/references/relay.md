# Autonomous run: relay instead of `/clear`

Read when the owner leaves the coordination running for hours with nobody supervising, or when taking over as the
successor of a relay.

The coordinator runs as a background session, `<prefix>-coord-<n>`, opened with the same command as the fronts (§2)
and the prompt "run the keel:coordinate-sessions skill and resume coordination; autonomous run, relay on". In the
terminal it could not stop itself, and pending notices would wake it. At the end-of-round checkpoint, in place of the
`/clear` notice:

1. it writes the checkpoint (§3) and deletes its tick (`CronList`, `CronDelete`);
2. it opens the successor `<prefix>-coord-<n+1>` with the same command and the same prompt;
3. it checks in `agents --json` that it is alive;
4. it ends itself with `"$C" stop <its own id, found by name in the same JSON>` and does nothing more.

The successor follows "Resuming after the `/clear`" (§9): it sends the new name to each live session, with
`notify_when_idle`, and arms its own tick when a front is live. Measured on 2026-10-20: the successor is born and takes
over, the old one leaves the list, and the front answers the new one by name.

In the autonomous run nobody answers questions: the doubts of all the foreseen fronts are cleared before releasing the
run (§4); what comes up afterwards goes to the owner's pending items in `queue.md`, and the coordinator moves on to
another front.
