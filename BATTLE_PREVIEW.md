# RankArc two-player practice

Source-only prototype. Not deployed.

## Behavior

- Two authenticated users join a friend room by code. Both must be ready before a shared timer starts.
- A room freezes the selected paper's questions, A-D/A-E choices, answer key, duration and original images. The creator explicitly confirms sharing that snapshot with the invited opponent. Neither player gains access to the other's paper library.
- Correct +1, wrong/skipped 0. Equal scores draw. An incomplete answer key means unscored practice with no winner.
- Choices are saved incrementally. Only server-confirmed answers count. Refresh and reconnect recover saved choices; losing a connection does not pause the timer.
- Both submissions or the deadline end the match. Keys and final scores are withheld until then.
- Open matches cancel after a process restart, with no winner. Finished rooms remain readable only if their storage survives.
- The separate stranger development queue pairs real users using the bundled synthetic four-question pool. It does not use private uploaded papers or invent opponents. A real common exam-question pool still needs permission and a verified key.

## Limits

Run exactly one application process/worker. SQLite transactions serialize join, ready, answer and finalization. This is not a distributed matchmaking system.

`BATTLE_DB` selects the separate room/asset SQLite file; by default it is under `UPLOAD_DIR`. Existing paper/auth data still use `DATABASE_URL`; battle does not change their database schema.

The UI polls every two seconds. Deadlines and scoring are decided by the server. This is casual practice, not anti-cheat: a paper creator may already know the key, and original source images may contain ticks or printed answers.

Preview limits: 1-500 questions; complete A-D/A-E choices; unique question numbers; 20 MB source images per room; 200 room records; a 64 MB database admission threshold. A single insertion can cross the threshold by one room. No automatic record purge. Separate option images are rejected rather than dropped. Waiting rooms expire after 30 minutes. Keep the room URL; no battle-history list is implemented.

There is no ranking, chat, payment, bot opponent, moderation, high-capacity claim or durable-hosting promise. Temporary hosting can lose accounts, uploads and results on a redeploy/restart. Publishing source does not deploy it or make current hosting durable.

## Verification

On November 16, 2026, the recovered implementation on rebranded repair base `3db4654392674f7186dc090a6b02c5171c8b2e54` passed a fresh frontend production build and 21 API/regression tests. One existing opt-in actual-paper test was skipped because its private PDF was not present.

Fresh local browser checks covered independent player sessions, an unauthorized third user, saved-answer reload, offline/reconnect, a 2:2 draw, synthetic queue pairing, an actual process restart, a frozen private geometry image, light/mobile views and a real 60-second deadline with a 1:0 result. No hosted battle test has occurred.

Run API checks from `backend`:

```
python -m pytest tests/test_battles.py tests/test_paper_repair.py -q
```

Build the frontend from `frontend`:

```
npm ci
npm run build
```
