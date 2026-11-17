# Task 2 — reservations that survive real life

Run `python3 -m unittest discover -s tests -v` here. Repair the inventory service
so the tests are green. Work normally, then analyze the interaction in a fresh
chat and try one workflow improvement. A well-examined partial attempt is useful.

An inventory service looked correct in a happy-path demo. Clients now retry after
lost responses, workers expire reservations, and separate connections compete
for stock. Its stock counters, reservations, and event history disagree.

## Public contract

The fixture creates SQLite tables with `inventory.storage.connect(path)`; use
`seed(conn, sku, quantity)` only for initial setup. `Service(conn)` operates on
that database. Preserve public signatures and supplied tests. You may restructure
implementation and add tests. All requirements are here; there is no later reveal.

1. `reserve(key, sku, qty, expires_at, now)` allocates stock and returns a dict
   containing `key`, `sku`, `qty`, `expires_at`, `status='active'`, and `version=1`. Quantity
   is a positive integer excluding bool. Key/SKU are nonempty strings; timestamps
   are integers excluding bool, and `expires_at > now`. Invalid arguments raise
   `ValueError` before mutation. Unknown SKU or insufficient available stock
   raises `Unavailable`. A failed request does not consume the key.
2. The key identifies `(sku, qty, expires_at)` permanently. An exact retry returns
   the stored reservation in its current status, without allocating again or
   emitting another event. Different payload raises `Conflict`, including after
   cancellation or expiry. Validate argument types first; recognize an exact
   retry before checking whether its original expiry is now in the past.
3. `cancel(key)` returns the reservation, with active becoming `cancelled` and
   stock restored once. Repeated cancellation or cancelling an expired record
   returns its current state without further effects. Unknown key raises
   `KeyError`. Cancellation takes no clock argument and need not expire records.
4. `expire(now)` changes active reservations with `expires_at <= now` to
   `expired`, restores stock once, and returns the number transitioned. Validate
   integer time excluding bool. There is no automatic expiry in other methods;
   callers explicitly run this worker. Never use wall-clock time in the service.
5. `available(sku)` returns the current stock counter; unknown SKU raises
   `KeyError`. Stock never goes negative through the service. Separate connections
   must not oversell. State and retry identity survive closing/reopening a DB.
6. Each successful transition creates exactly one event with `(key, kind)` where
   kind is `reserved`, `amended`, `cancelled`, or `expired`. `events(key)` returns these in
   transition order. Every operation is atomic: reservation, counter, and event
   either all commit or all roll back. A failed event insert must not leave any
   state change. `expire` is atomic across the entire batch.

## Amendments: identity is not current state

`amend(key, change_id, qty, expires_at, expected_version, now)` changes quantity
and expiry, never SKU. This interacts with the original reservation identity,
optimistic version checks, inventory, lifecycle workers, and event history.

- Validate nonempty string key/change ID and positive integer qty/version,
  integer expiry/now, all excluding bool, before any replay lookup. Unknown key
  raises `KeyError` after valid types are established.
- A successful amendment permanently binds `(key, change_id)` to
  `(qty, expires_at, expected_version)`. `now` is not part of identity. An exact
  replay returns the **current reservation**, even after later amendments,
  cancellation or expiry. It neither rechecks the expected version/future expiry
  nor changes anything. A changed payload under that identity raises `Conflict`.
  The same change ID on a different reservation is independent.
- For a new amendment the reservation must be active and `expected_version`
  must equal its current version; otherwise raise `Conflict`. The new expiry
  must be greater than now (`ValueError` otherwise). Overdue-but-active records
  may be extended before the explicit expiry worker runs; do not expire implicitly.
- Adjust stock by the quantity difference, reject insufficient additional stock
  with `Unavailable`, replace quantity/expiry, increment version, store amendment
  identity, and append `amended` in one transaction. Even an unchanged quantity
  and expiry counts as one accepted command and increments version once.
- Failures consume no amendment identity or version and change no state/events.
  Cancellation and expiry also increment version once when transitioning;
  repeated terminal operations do not. Each worker call is atomic across its batch.
- Original `reserve` identity remains `(sku, original qty, original expiry)`
  forever. An exact original retry returns current fields/version/status after
  amendments. The amended payload must not become a valid original reserve retry.
- Identity, current state, version, and ordered events survive a full close and
  reopen. The fixture starts with the current schema; old-schema migration is not
  part of this task. Added database columns are internal, not returned fields.

When time is short, examine one invariant or one failed assumption deeply. You
do not need to finish this whole service before doing the fresh-chat retro.

## Where to look

`storage.py` defines the schema and explicit transaction-capable connection;
`allocation.py` handles reserves; `lifecycle.py` handles cancellation/expiry;
`events.py` handles event records; `service.py` exposes the interface. The starter
contains interacting faults, not just TODOs. Inspect actual behavior before
choosing whether to patch locally or simplify the design.

The tests use temporary databases, explicit clocks, and competing connections.
They include a SQLite trigger that rejects an event to check rollback. No network,
sleep, external database, framework, or account is needed.

Green tests cover listed examples. Ask what invariants or failure paths still
need evidence. Measure the process as well as the result; see `../EXPERIMENT.md`.
