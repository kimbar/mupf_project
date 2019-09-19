The logging subsystem
=====================

**What**: a subsystem for monitoring what, and in what order happened

**Why**: multiple things are happening asynchronously on multiple processes and
threads

**How**: user requests for entry points and waits for a log output; also:
**tracks!**

The subsystem consist of three main parts: The **manager**, **sentinel** and
**writer** objects.

Manager objects are entry points for the user. Each manager have a unique
**address** by which the manager can be switched on or off. A manager is called
**simple** if it has a single sentinel object; when it has multiple sentinels
it is called **childless**. When a simple manager is switched on it produces a
sentinel. Sentinel wraps a function (unbound method, accessor, etc.) and
subsequently hijacks all calls to this function. When the manager is switched
off the function is unwrapped and the sentinel is destroyed, so no overhead is
kept when not logging. The simple manager that created the sentinel is its
**parent**. Other managers that use the sentinel are its **aunts**. All aunts
are childless − this requirement is superficial and could be removed, but is
there for simplicity of the system. When a childless manager is switched on it
request from simple managers to **borrow** their sentinels. If the simple
manager of the requested sentinel is not switched on at the moment it flags the
state of its sentinel as borrowed.

When a sentinel is in place and the wrapped function would be called the
sentinel is called. The sentinel reports this (**enter**) event to its parent
and aunts and then immediately calls the wrapped function. When the function
finishes, the sentinel once again reports (**exit**) event to its parent and
aunts and returns the function return value. Enter and exit events are
unambiguously paired (**HOW**) in the eyes of parents and aunts.

Managers, when informed by their sentinels (own or borrowed) about enter and
exit events produce, update or destroy some writer objects. A writer object
directly represents few lines in the logging output. Each line represents a
single (enter or exit) event of a sentinel. The lines are graphically connected
by **tracks** in the log output.

```txt
 ┌─< A fictitious example of a logging output ...
 │┌─< Each line may by connected to its ...
 ││┌─< This way events not in sequence can
 ││└─> still be tracket easily(-ish).
 ││ ── Traditional single line logs can also be produced
 │├── middle events and ...
 ││┌─< Tracks can be grouped, for example to denote separate threads
 │││       ┌─< Events in another thread have the track indented
 │││       ├── That works most of the time (indentation may run off)
 │││       ├── but no worries - the tracks are still ok
 │││       └─> only the grouping is no longer visible
 │││       ┌─< Events from different groups can ...
 ││└───────┼─> Position of the vertical track matters, not the location of the message
 ││        └─> ... be intervoven.
─┼┼┐─> Another format of a writer output
 ││├── It has no intrinsic meaning, just looks different and can be used
─┼┼┘─< for different things, like incoming messages
 │└─> ending.
 └─> with tracks.
```

Tracks are owned by writers. After receiving an event, a manager decides if to
create new writer (a track is assigned automatically), destroy an existing one
or request from existing writer a middle message. All of these are connected
by a graph as shown above.
