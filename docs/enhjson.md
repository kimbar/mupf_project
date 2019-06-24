# Enhanced JSON escape structures

**What**: modifications of a given JSON, but staying in JSON specification.

**Why**: to carry non-specification values in a JSON.

**How**: very similarly how escape sequences in a string literal work.

JSON format is able to transport a lot of common, immutable, by-value data
between Python and JS. However, also mutable by-reference data and uncommon
types must be transported and referenced on both sides. Appropriate values are
held permanently in a special container or are created on-the-fly and are
addressed with **escape structures** in JSON. This **escape structures** have
form and function very similar to the escape sequences in strings such as
`'\t'`.

**Escape structure** has the form of two element array: `["~`<span
style="font-size:90%; border: 1px solid; border-radius:1em; padding: 0
0.5em">characters</span>`", ` <span style="font-size:90%; border: 1px solid;
border-radius:1em; padding: 0 0.5em">elements</span>`]`, where <span
style="font-size:90%; border: 1px solid; border-radius:1em; padding: 0
0.5em">characters</span> and <span style="font-size:90%; border: 1px solid;
border-radius:1em; padding: 0 0.5em">elements</span> are productions as defined
in JSON specification. The former chooses the **escape handler** and the latter
are arguments which are passed to this handler. The **escape structure** is
always at least two element array with first element being a string starting
with `~`. The second and subsequent elements are arbitrary JSON values, which
may contain further nested and recursively resolved **escape structures**.

## Basic handlers

The most basic **escape handler** is `"-"`. That is `["~-", `<span
style="font-size:90%; border: 1px solid; border-radius:1em; padding: 0
0.5em">value</span>`]` is escaped to <span style="font-size:90%; border: 1px
solid; border-radius:1em; padding: 0 0.5em">value</span>. No recursive decoding
is done on this value, so this **escape structure** inhibits all eventual
escaping sequences inside. It is very simple, but is not enough to escape
everything.

Therefore the `"~"` **escape handler** exists. The `["~~", `<span
style="font-size:90%; border: 1px solid; border-radius:1em; padding: 0
0.5em">array</span>`]` is escaped to <span style="font-size:90%; border: 1px
solid; border-radius:1em; padding: 0 0.5em">array</span>, but all elements of this
array are recursively escaped if needed. The array as a whole is not
processed as an **escape structure** even if it matches an appropriate form.
That is in `["~~", [100, ["~~", ["~~", 300]]]]]` the second escape will also be
processed and the result will be `[100, ["~~", 300]]`. This way, arbitrary
array that matches the format of an **escape structure** can be escaped as
`["~~", ["~`<span style="font-size:90%; border: 1px solid; border-radius:1em;
padding: 0 0.5em">characters</span>`", ` <span style="font-size:90%; border:
1px solid; border-radius:1em; padding: 0 0.5em"> elements</span>`]]`. In fact,
this is the only practical (albeit rare) use-case for this **escape handler**.
It is a functional equivalent of the `"\\"` escape sequence in strings, which
encodes a single `\`.

The most common **escape handler** is `"@"` which references JS object by id.
For example `["~@",562]` is escaped to `mupf.obj.byid(562)`. Appropriate
object must be stored under `562` beforehand.

Special values handler `"S"` provides for passing values such as `undefined` or
`NaN` which cannot be directly represented in JSON. Values returned by this
handler can be easily added by extending the `mupf.esc.special` object.

Exception handler `"?"` is produced if encoded object could not provide
appropriate handler name and argument for the handler. The value for the
unknown handler is the `repr()` of the object (a string). for example
`["~?","<built-in function print>"]`.

## Explicit enhanced block handler

Explicit enhanced block `["~", `<span style="font-size:90%; border: 1px solid;
border-radius:1em; padding: 0 0.5em">value</span>`, `<span
style="font-size:90%; border: 1px solid; border-radius:1em; padding: 0
0.5em">object</span>`]` is equivalent to just the <span style="font-size:90%;
border: 1px solid; border-radius:1em; padding: 0 0.5em">value</span>, however
information given in <span style="font-size:90%; border: 1px solid;
border-radius:1em; padding: 0 0.5em">object</span> is applied during escape
resolution for optimization. For example, resolution of:

```JSON
["~",
    [100, ["~@",23], ["~@",30], 23, 23, 100, 32],
    {"c":2}
]
```

is finished right after `["~@",30]` because `"c":2` informs the transformation
engine that there are only two **escape structures** inside and all subsequent
values can be copied as-are. The optimization information <span
style="font-size:90%; border: 1px solid; border-radius:1em; padding: 0
0.5em">object</span> may be empty, but is always present.

**Explicit enhanced block** is encoded always when a structure contains any
**escape structures**. This way if a decoder expects an enhanced format and
finds no **explicit enhanced block**, it may safely assume than no **escape
structures** are present inside and all the data can be copied as-is.

## Custom handlers

Custom transformation handlers for Python&nbsp;→&nbsp;JS transport can be added
in `mupf.tr` on the JS side. On the Python side they should be implemented as
objects which implement `.json_esc()` method. Only a single argument (two
element **escape structure**) is supported for custom handlers. Transport in
the other direction is not supported − all uncommon objects should be stored in
`mupf.obj` and referenced on the Python side by `RemoteObj`.
