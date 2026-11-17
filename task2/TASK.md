# Task 2 — reservations that survive real life

**Incident:** a reservation was saved, the notification was delivered, then its
acknowledgement was lost. The reporting service must survive the retry. An older
database and an online reporting rebuild make the recovery more complicated.

**First action:** from this folder run:

```sh
python3 incident.py
```

This creates an isolated temporary source database, delivers a notification,
simulates a lost acknowledgement, reopens the source, and prints what a retry
observed. The starter shows a lost notification. Its fake receiver uses memory,
so this reproduction does not establish durable reporting or dedup. Ask your
agent what happened and what check would prove the repair, then investigate.
To run one focused test, use `python3 -m unittest discover -s tests -p test_recovery.py -k lost_ack -v`.
The complete suite is `python3 -m unittest discover -s tests -v`. The detailed
contract below is available when needed; you do not need to read it all before
running the first check. Save the interaction and run a fresh-chat retro. One
well-examined failure or partial improvement is useful even with tests still red.

## Public contract

The fixture creates SQLite tables with `inventory.storage.connect(path)`; use
`seed(conn, sku, quantity)` only for initial setup. `Service(conn)` operates on
that database. Preserve public signatures and supplied tests. You may restructure
implementation and add tests. All requirements are here; there is no later reveal.

All quantities, versions, event IDs, dispatch limits, and timestamps accepted by
the public interfaces must be Python integers excluding bool within SQLite's
signed 64-bit range (`-2**63` through `2**63-1`). Quantities, versions, IDs and
limits are positive; timestamps may be negative. Reject malformed/out-of-range
inputs with **plain `ValueError`** before replay, key lookup, domain conflicts, or
mutation. `Conflict` and `Unavailable` are subclasses of `ValueError` but are
reserved for the separately described domain outcomes. The fixture's `seed`
only supplies nonnegative in-range integers. An operation that would create an
out-of-range counter or increment version beyond `2**63-1` raises `Conflict` and
rolls back. A v1 database whose available stock plus active reserved quantity
exceeds `2**63-1` for any SKU is invalid and its migration raises `MigrationError`.
All user-supplied keys, SKUs, change IDs, rebuild tokens and string cursors must
be nonempty UTF-8-encodable strings; invalid text, including an unpaired
surrogate, raises plain `ValueError` before lookup or mutation.

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
   Specifically, validate input types/ranges first, then check existing key for
   exact replay or `Conflict`, then require a future expiry for new keys only.
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
  reopen. Added database columns are internal, not returned fields.

## Upgrade and interrupted delivery incident

The old release used SQLite `PRAGMA user_version=1` and these tables:

```sql
CREATE TABLE stock(sku TEXT PRIMARY KEY, available INTEGER NOT NULL);
CREATE TABLE reservations(key TEXT PRIMARY KEY, sku TEXT NOT NULL, qty INTEGER NOT NULL,
                          expires_at INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE events(id INTEGER PRIMARY KEY, key TEXT NOT NULL, kind TEXT NOT NULL);
```

`inventory.storage.connect(path, *, migration_hook=None)` opens a connection in autocommit mode with
row access by name. A brand-new empty database initializes as version 2. Upgrade
an existing v1 database atomically to version 2 and leave it usable on reopen;
multiple connections may attempt the upgrade concurrently. A v2 reopen must not
duplicate records or repeat effects. Reject unsupported `user_version` values and
nonempty unversioned databases with `inventory.storage.MigrationError`.

Preserve v1 stock counters, reservation keys/SKUs/quantities/expiry/status, and
the event IDs, order, key, and kind. A migrated reservation's initial `version`
is 1 and its immutable original qty/expiry are its v1 qty/expiry. Historical event
IDs remain reserved, but old events are historical and are **not** republished.
Preserve historical kinds as-is, even if outside the current transition list;
historical event IDs can be negative.
Add the tables/columns required for amendments and delivery. Before committing,
reject v1 rows with empty/non-string keys or SKUs, non-integer/negative available
stock, non-positive/non-integer reservation quantities, non-integer expiry,
unknown reservation SKU, or status other than active/cancelled/expired. Invalid
data raises `MigrationError` without changing schema, rows, or user_version. A
SQLite failure during migration also rolls the whole upgrade back and propagates
the failure. Do not drop, silently repair, or reinterpret legacy rows. For this
exercise v1 contains no amendment records; its fields are the original request.
If a `migration_hook` callback is supplied, invoke `migration_hook(conn)` exactly
once after v1 schema/data work but before committing the upgrade. An exception
from this callback propagates and rolls the entire upgrade back. Do not call it
for fresh databases or v2 reopens. The hook is a local fault-injection seam;
it does not prescribe whether migration uses row updates or replacement tables.

Every **new** successful reservation transition writes an immutable notification
to a durable outbox in the **same** local transaction as the state/counter change.
Exact command retries and rejected/rolled-back operations emit nothing. The
outbox can live in the existing `events` table; `events(key)` keeps its original
`[{"key": ..., "kind": ...}, ...]` interface and includes historical events.
An existing audit integration reads `SELECT id,key,kind FROM events ORDER BY id`
directly. Preserve that SQL interface and insert exactly one row into the existing
`events` table for each successful reservation transition in the same local
transaction. Outbox payload and delivery bookkeeping may live in that table or a
separate table; a dispatched notification's `id` is its corresponding `events.id`.
The audit integration also uses `SELECT COUNT(*) FROM reservations` and
`SELECT COUNT(*) FROM events`; keep these legacy read-only queries supported.

`Service.dispatch(publisher, limit=100)` reads at most `limit` pending events in
ID order. `limit` is a positive integer excluding bool; invalid values raise
`ValueError` before doing work. For each it calls `publisher(envelope)`, where the
dictionary contains exactly `id`, `key`, `sku`, `qty`, `expires_at`, `status`,
`version`, and `kind`, all captured at that transition. Event IDs are stable
positive integers from this one source database and payloads never change. Mark
an event delivered only after the callback returns normally; return the number
acknowledged. If it raises, propagate the exception, leave that event pending,
and retain acknowledgements of earlier events. A publisher can deliver remotely
and then raise because the acknowledgement was lost: the next dispatch may send
the same event again. No SQLite transaction can undo that remote side effect.
Concurrent dispatchers may duplicate delivery; do not claim exactly-once transport.
For every new transition, its event ID must be strictly greater than
`max(0, all existing event IDs)` at the time of insertion, even if v1 contains
negative historical IDs. At the signed-64-bit maximum, raise `Conflict` and
roll back the entire transition. Never reuse, renumber, or delete historical IDs.

## Separate reporting database

`inventory.projection.connect_projection(path)` opens/initializes a separate
durable SQLite database, with row access by name, for
`Projection(conn, *, apply_hook=None)`.
`Projection.get(key)` returns a public reservation snapshot (`key`, `sku`, `qty`,
`expires_at`, `status`, `version`) or raises `KeyError`.

`Service.snapshots()` returns those public snapshots sorted by key. For v1 cutover,
call `projection.bootstrap(snapshot)` for every snapshot **before** post-upgrade
producers/deliveries and while there are no concurrent source writers. Bootstrap
creates that projection record; repeating an identical snapshot is a no-op and
returns it; a different snapshot for an existing key raises `Conflict` without
mutation. This explicit cutover avoids inventing old notification payloads.

`projection.apply(envelope)` atomically deduplicates and applies one notification:

- First application returns `True`; a previously applied ID with an identical
  complete envelope returns `False`, even after later versions and reopen.
- A previously applied ID with any different field raises `Conflict` and changes
  nothing. One source DB supplies the globally meaningful event IDs in this lab.
- For a new ID, the envelope version must be exactly one greater than the
  projection's current version for that key; a key absent from the projection
  expects version 1. Earlier, duplicate-with-new-ID, and future versions raise
  `inventory.projection.Gap`, changing neither projection nor dedup state. The
  caller can retry a gap after delivering missing events. No global checkpoint
  may skip the unresolved event.
- On success persist the public snapshot from the envelope and its full identity
  in the same consumer transaction. A crash after delivery but before producer
  acknowledgement may redeliver; the consumer must apply its effect once.
- Separate projection connections may apply the same envelope concurrently. Both
  calls must complete: one returns `True`, the other `False`, with one durable
  state effect. No scheduler-specific winner is required.
- If supplied, call `apply_hook(conn, envelope)` once after the first application
  has staged both state and dedup writes, before its consumer transaction commits.
  If it raises, propagate the exception and roll back both writes. Do not invoke
  the hook for duplicate or rejected envelopes. This is a local failure-injection
  seam; it does not require a particular database schema or SQL statement order.

Before any lookup or mutation, `apply` validates that the argument is a dict
containing exactly the eight envelope fields, nonempty string key/SKU, a kind in
`reserved/amended/cancelled/expired`, a status in `active/cancelled/expired`, and
valid in-range numeric fields as above. `bootstrap` similarly validates a dict
with exactly the six public snapshot fields and matching value rules. Invalid
input raises plain `ValueError`. This ensures malformed retries cannot pass as
valid Python booleans or leak `OverflowError` from the SQLite binding.
The same validation comes before the active-rebuild check: malformed payloads
raise plain `ValueError` even during a rebuild. Valid `bootstrap` or `apply`
payloads during an active rebuild raise `Conflict` as specified below.

Callbacks are local fakes; no server, account, network, or sleeps are needed.
Review failure cases at both databases and across process restart. The local
source transaction and reporting transaction cannot be combined into one commit.

## Online reporting rebuild: no missed notifications

Operations now need to rebuild reporting while source writes continue. Rebuilds
use separate durable source and reporting databases. At no point is there a
distributed transaction between them. Keep the old reporting view readable while
staging a replacement; it may be stale until cutover. Source writers continue.

The token is a nonempty string chosen by the caller; a token identifies one
immutable capture and must survive connection/process reopen. Invalid token, page
cursor or limit types raise plain `ValueError` before lookup. Unknown token raises
`KeyError`. Limits are positive signed-64-bit integers excluding bool. Snapshot
cursors are `None` or nonempty strings; event cursors are `None` or positive
signed-64-bit integers excluding bool. A cursor is exclusive and need not name
an existing item. Each paging method returns `{'items': [...], 'next': cursor}`:
`next` is the last returned key/ID only when additional matching items remain;
otherwise it is `None`. Empty results have `items=[]` and `next=None`.

The canonical digest of a list is the lowercase SHA-256 hex digest of its UTF-8
`json.dumps(items, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`.
Sort snapshots by key and envelopes by integer event ID before hashing. Empty
lists are valid and hashed the same way. This is a consistency check, not a
cryptographic proof against an attacker controlling both source and manifest.

### Source capture and fence

The operator coordinates delivery routing across the two databases. Before
capturing W, pause the start of new delivery callbacks and let any in-flight
callbacks finish. Capture the source snapshot, begin the projection rebuild,
and install the durable staging callback described below. Only then resume
delivery callbacks and obtain the fence F. Source writers remain active during
this brief delivery pause and throughout the rebuild. This routing barrier is a
caller responsibility, not a cross-database transaction and not something either
database API can enforce by itself. Without it, an event after F could be applied
and acknowledged on the old view before staging starts, then lost at cutover.
The supplied tests demonstrate compliant orchestration; they cannot enforce an
external caller's pause, drain, or routing decisions.

- `Service.begin_rebuild(token)` atomically captures all public reservation
  snapshots, watermark `W=max(0,all source event IDs)` and immutable complete
  envelopes for **all nonhistorical** events with ID <= W, in one local source
  transaction. The captured data is durable and independent of later writes.
  It returns exactly `{'token', 'watermark', 'count', 'digest', 'seen_count',
  'seen_digest'}`: the counts/digests cover key-sorted snapshots and ID-sorted
  nonhistorical envelopes respectively. Migrated v1 historical events have no
  invented envelope and cannot be republished. Include nonhistorical events
  whether their delivery has already been acknowledged or is still pending.
  Repeat with the same token returns
  the original manifest, including after source reopen. Different tokens may
  coexist and have independent captures.
- `Service.snapshot_page(token, after=None, limit=100)` pages frozen snapshots;
  `Service.seen_page(token, after=None, limit=100)` pages frozen envelopes from
  that capture. Neither returns current/live data. Capturing prior identities is
  necessary when a producer delivered an event before W but lost its ACK: after
  cutover, exact redelivery must still deduplicate and changed redelivery conflict.
- `Service.fence_rebuild(token)` atomically freezes a later source high-water F
  and all complete envelopes with W < ID <= F. It returns exactly `{'token',
  'watermark', 'through', 'event_ids', 'digest'}`, where `through=F`, `event_ids`
  is the complete ID-sorted list, and digest covers the ordered envelope list.
  This frozen fence is authoritative; repeating it returns the same result even
  if later writes occur. `Service.rebuild_events(token, after=None, limit=100)`
  pages those frozen envelopes in ID order; calling it before fencing is `Conflict`.
  A fence may be empty. Normal source writes after F are not part of this cutover.

### Reporting staging and atomic cutover

`Projection(conn, *, apply_hook=None, cutover_hook=None)` accepts both optional
hooks; existing API behavior is unchanged outside a rebuild.

- `begin_rebuild(manifest)` persists a new staging generation; it returns `True`
  for creation and `False` for an identical retry, including after reopen or
  completion. The same token with a different manifest raises `Conflict`. At most
  one rebuild can be active per projection; a different token while it is active
  raises `Conflict`. Existing reporting data remains readable. While a rebuild is
  active, ordinary `Projection.apply` raises `Conflict`. The delivery callback
  routes events with ID <= W to `stage_seen` and events with ID > W to
  `stage_event`. Before acknowledging a pre-W delivery, the caller must compare
  its complete envelope to the source's frozen `seen_page` data; a missing or
  changed identity must raise instead of returning normally. `get` stays available.
  `view()` returns one atomic list of
  public snapshots sorted by key; separate `get` calls may straddle a cutover.
  `Projection.bootstrap` also raises `Conflict` while any rebuild is active,
  including for an identical existing snapshot; it must not mutate the old view.
- `stage_snapshot(token, snapshot)`, `stage_seen(token, envelope)`, and
  `stage_event(token, envelope)` durably store items in arbitrary order and return
  `True` on first insertion or `False` for an identical retry. The identity is
  snapshot key or event ID respectively; a changed payload under an existing
  identity raises `Conflict`. Apply the same shape/range validation as bootstrap
  and apply. A seen event must have ID <= W; a staged event must have ID > W.
  They may arrive before snapshot pages. New snapshots/seen records cannot be
  inserted after cutover; exact retries remain `False`, changed payloads conflict.
- `cutover(token, fence)` first validates token/fence shapes and ranges, then
  looks up the token (`KeyError` if unknown), then compares fence token/watermark
  to the stored manifest (`Conflict` on mismatch). It then
  checks complete snapshot/seen counts and canonical digests, exact fenced event
  IDs and canonical digest, and contiguous per-key versions. Missing/extra data
  within the fence, changed identities, mismatched manifest/fence or digest raise
  `Conflict`; only after the completeness/digest checks pass do missing
  predecessor versions raise `Gap`. Validation failure leaves
  the visible view and active staging intact. Events staged with ID > F do not
  prevent cutover and remain durable as pending, rather than being silently lost.
- After successful validation, atomically install the snapshots plus **all**
  captured pre-W identities as dedup history, then apply fenced events in ID order.
  Readers of `view()` see the whole old or whole new generation. Return `True` on
  first cutover, `False` on identical repeat including after reopen; a different
  fence for an already cut-over token raises `Conflict`. If supplied, call
  `cutover_hook(conn, token)` once after replacement is staged but before its
  commit. An exception propagates and rolls back replacement and cutover marker.
  Do not invoke this hook on repeat or rejected cutovers.
- `pending(token)` returns staged envelopes with ID > F not yet acknowledged,
  sorted by ID; it is available after cutover. The caller applies them through
  ordinary `apply` in order after supplying any missing post-F events. A gap is
  retryable and must not be acknowledged. `ack_pending(token, id)` removes one
  pending item only when its **exact** envelope is already in applied dedup state;
  it returns `True` once and `False` on an identical repeated acknowledgement.
  A known but unapplied/different pending item raises `Conflict`; an unknown ID
  raises `KeyError`. Crashing after `apply` and before acknowledgement is safe:
  applying the identical event again returns `False`, then acknowledgement works.
  Before cutover, `pending` and `ack_pending` raise `Conflict`. An exact
  `stage_event` retry for an already acknowledged post-F ID returns `False`
  without recreating pending work; a changed payload for that ID raises `Conflict`.

Rebuild state, pages, captured identity history, fence, pending events, and
completed-token idempotency survive reopen. No write to one database can commit
the other. The caller remains responsible for subsequent delivery after F.
The source dispatcher must only receive a normal callback return after the
corresponding event has been durably staged or applied; returning after adding it
to an in-memory list can lose it on crash. A successful stage acknowledges durable
staging, not application to the visible view. If the callback stages then loses
its acknowledgement, the dispatcher may retry; an identical staged record is
accepted as a duplicate and the callback can then return normally. `stage_seen`
does not itself prove membership in the captured list: it can accept an otherwise
valid provisional ID, so the caller validates against frozen pages before an ACK.
Any extra or changed captured identity fails the complete digest check at cutover.
`stage_event` accepts new IDs > F both before and after cutover. After cutover,
an exact retry of an already-staged event at or below F returns `False`, while a
previously unstaged event at or below F raises `Conflict`.

Validate input shapes before state lookup: manifest and fence must be dictionaries
with exactly the named fields; digest fields are 64 lowercase hexadecimal
characters; counts and watermarks are nonnegative signed-64-bit integers excluding
bool. Fence `through` is >= watermark, and `event_ids` is an ascending, unique
list of positive signed-64-bit integers in (watermark, through]. Invalid shape or
range raises plain `ValueError`. A structurally valid but changed manifest for an
existing token, or a fence with a different token/watermark, raises `Conflict`.
The seen list includes all nonhistorical identities through W, regardless of
whether a dispatcher has acknowledged their delivery.

### Operator repair of poisoned staging

A wrongly staged but valid-shaped item can otherwise prevent cutover forever.
`repair_staged(token, category, expected, replacement=None)` is an explicit
compare-and-swap repair, allowed only while the token is active. `category` is
`snapshot`, `seen`, or `event`; identity is the snapshot key or event ID.
Validate token/category and both payload shapes/ranges before lookup. A missing
token or staged identity raises `KeyError`. If the stored payload is not exactly
`expected`, or `replacement` has a different identity, raise `Conflict` without
changes. A replacement identical to the stored payload returns `False` without
changes. Any other replacement with the same identity atomically swaps the
staged payload and returns `True`. If `replacement` is `None`, remove that item
from the active staging generation and return `True`.

Every successful repair atomically appends the complete original payload and
replacement (or `None`) to durable `quarantined(token)` records. That method
returns the records in repair order as dictionaries containing exactly
`category`, `original`, and `replacement`. Records survive restart and cutover,
are visible to the operator for recovery, and are never automatically replayed
or acknowledged. Quarantining a source-acknowledged event therefore does not
silently discard its payload. Cutover still verifies the authoritative complete
manifest and fence: removing a required item leaves it missing and blocks
cutover until the correct item is staged. After successful cutover, repair is
rejected with `Conflict`; quarantine remains readable. No database schema for
these records is prescribed.
After shape/range validation and token lookup, check whether the token has
completed before looking up a staged identity: completed tokens raise `Conflict`,
including when the requested identity is absent. `KeyError` for a missing staged
identity applies to active tokens only.

A valid-shaped but corrupted manifest can also wedge an active rebuild.
`repair_manifest(token, expected, replacement)` explicitly compares and repairs
that metadata without removing staged items. Validate both complete manifests and
token before lookup. An unknown token raises `KeyError`; a non-active/completed
token, stored manifest different from `expected`, or replacement whose token
differs raises `Conflict`. If the replacement watermark would make an already
staged seen ID greater than W or a staged event ID less than or equal to W,
raise `Conflict` without changing anything. Identical replacement returns
`False`; otherwise atomically replace the manifest, append
`{'category': 'manifest', 'original': expected, 'replacement': replacement}`
to the same durable `quarantined(token)` audit list, and return `True`.
The operator supplies the authoritative replacement from the source; cutover's
normal identity, digest and completeness checks still apply. No source-ACKed
staged payload is removed or automatically acknowledged by manifest repair.

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
