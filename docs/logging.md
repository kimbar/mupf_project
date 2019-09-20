The logging subsystem
=====================

**What**: a subsystem for monitoring what, and in what order happened

**Why**: multiple things are happening asynchronously on multiple processes and
threads

**How**: user requests for entry points and waits for a log output; also:
**tracks!**

Overview
--------

The subsystem consist of three main parts: The **manager**, **sentinel** and
**writer** objects.

Manager objects are entry points for the user. Each manager have a unique
**address** by which the manager can be switched on or off. A manager is called
**simple** if it has a single sentinel object; when it has multiple sentinels
it is called **childless** (childless managers are "compound" or "complex", and
simple managers are always "with a child"). When a simple manager is switched
on it produces a sentinel. Sentinel wraps a function (unbound method, accessor,
etc.) and subsequently hijacks all calls to this function. When the manager is
switched off the function is unwrapped and the sentinel is destroyed, so no
overhead is kept when not logging. The simple manager that created the sentinel
is its **parent**. Other managers that use the sentinel are its **aunts**. All
aunts are childless − this requirement is superficial and could be removed, but
is there for simplicity of the system. When a childless manager is switched on
it request from one or more simple managers to **borrow** their sentinels. If
the simple manager of the requested sentinel is not switched on at the moment
it flags sentinel state as "borrowed" but does not switch on itself. The
relation parent-sentinel is one-to-one, and relation aunt-sentinel
many-to-many.

When a sentinel is in place and the wrapped function would be called the
sentinel is called. The sentinel reports this (**enter**) event to its parent
and aunts and then immediately calls the wrapped function. When the function
finishes, the sentinel once again reports (**exit**) event to its parent and
aunts and returns the function return value. Enter and exit events are
unambiguously paired (**HOW**: the counting number of a writer) in the eyes of
parents and aunts.

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
 ││ ─> Traditional single line logs can also be produced
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
or request from existing writer a middle message. All of these are connected by
a graph as shown above.

TODO: additional feature − connecting the tracks (writers) based on the current
execution stack.

All this flexibility is greatly reduced in the case of simple managers (hence
the name). They never request a middle message from its writer − only enter and
exit messages are printed. One of this two messages can be turned off, and that
is an only option a simple manager has (some functions have uninteresting
arguments or results and logging both only clutters the log.) Moreover, a
simple manager always logs an event. If a more flexible manager is needed (for
example one that logs only erroneous results and good ones passes silently) an
additional childless manager must be created that implements this logic. A
childless manager can after all borrow just a single sentinel to implement this
behaviour. This approach clearly separates managers directly connected to some
piece of code (simple) and those operating on higher level of application logic
(childless).

Manager address
---------------

A manager address consists of one or more **parts** separated with `/`; each
part can consist of **subparts** separated with `.`. A subpart can be appended
with zero or more **specifiers** enclosed in `<>`.

```txt
part/part/subpart.subpart/subpart<specifier>.subpart.subpart<specifier><specifier>
```

Each of these can be used freely, but they have designed purpose for simple
managers. Parts should mimic the structure of application, that is packages,
modules and files. Last part describes a function that is managed by the
manager with `.` separating names of classes, methods, properties and accessors
(hence these are subparts). Specifiers are reserved for runtime dynamically
created entities such as objects or files. A writer at its creation inherits
the address from its manager, who fills in specifiers and appends the address
with one last part (**currently subpart - to change**). The last part is a
counter of writers produced by the manager. This writer address is written
after the tracks in a logfile.

```txt
╭─< app.py/App<36252B0>.enter/1
│╭─< app.py/App<36252B0>.is_opened/2
│╰─> app.py/App<36252B0>.is_opened/2
╰─> app.py/App<36252B0>.enter/1
╭─< client/command.py/Command<wR45mj><?-36250B8>.init/4
╰─> client/command.py/Command<wR45mj><?-36250B8>.init/4
```

In above example `36252B0` is an id of an `App` classed object, `enter` and
`is_opened` are methods. Likewise `Command<wR45mj>` is a dynamically created
class and `?-36250B8` an id of its object and `Command` a metaclass. Subparts
of `app.py` and `command.py` have normal meaning for a filename.

This way a writer address is guaranteed to be exactly constant and unique for a
given writer, however after removing the last part and reducing specifiers to
`<>` the original address of the manager can be obtained, and the parts lead
the reader to the exact place in the codebase that produced the log entry.

The childless managers sometimes do not represent any specific portion of the
code, and can be quite abstract, however they should somehow follow above
guidelines. It is recommended for parts of their addresses to lead to a
documentation chapter where the specific application behaviour is described.

Applying managers
-----------------

There is only a single class of simple managers and it is applied by decorating
a function, class, method etc. This creates a manager object at the module load
and it can be then switched on. Simple managers are not designed to be directly
attached to objects, they operate through their classes and objects are
identified in specifier parts of writer/manager address. However simple
managers can be dynamically created during the runtime if new classes are
dynamically created.

Since childless managers require some additional code to function they are
constructed as classes derived from `LogManager` class, however they remain
singletons. New class must implement `on_on` (TODO: reconsider this to be just
the `__init__`) method where borrowing happen, optionally `on_off` method for
clean up, and `on_event` method where sentinels events land. It can request a
(prefiltered) list of `get_simple_managers`, a `new_writer` or iterate through
existing `writers`.
