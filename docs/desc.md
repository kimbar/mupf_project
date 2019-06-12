How it works
============

## How it starts

1. You create an `App` class object

    You can think of an `App` class object as an server residing on a system
    port and also a python thread on which this server and asynchronous loop is
    run on. So yeah, it is a thread a port a server and a "async loop" in one.
    It groups all these low-level functionalities so you don't need to think
    about them.

2. You summon an `Client` class object from the `App`

    The `Client` class object represents a browser window. It is not called
    "window" because in JavaScript `window` is a reserved name for top level
    context object. You can access this `window` object easily through the
    `Client` class object however. `Client` class object has its unique ID.

    At this moment `Client` class object is not ready yet to use. However, you
    don't need to wait for it to be fully initialized (although you can --
    there's a feature for this). All commands invoked from now on will be
    stored until the client is ready.

3. `Client` class object opens a local address in the browser

4. Browser loads the `bootsrap.js` file

5. `bootstrap.js` creates minimal `mupf` environment

6. `*first*` command is run

    The `*first*` command is a little special. It looks as it is run by the
    `Client` class object at initialization normally as any other command.
    However, at this point the web-socket is still not avaliable. This is due
    to a fact, that the `*first*` command is the one that creates the
    web-socket. This chicken-egg problem is resolved by suppressing sending of
    this command on the Python side and artificially recreating effects that
    this send would have in the very last line of the `bootstrap.js` `main()`
    function.

    The `*first*` command deletes the `bootstrap.js` script from the browser
    DOM, creates a web-socket and finishes with a return value, which contains
    ID of the client and browser identification string.

7. Web-socket is created

8. Web-socket is assigned to the `Client` class object

9. Communication is established

10. `core.js` is installed

11. You can access DOM objects

## How it operates

## How it ends

### By closing browser window

Closing of browser window triggers a `*close*` notification, thus a
`ClientClosedUnexpectedly` exception is raised on the Python side.

### By closing the client object

Python side sends a `*last*` command which gracefully closes the communication.

### By lost connection

Lost connection triggers an unexpected break in websocket communication, thus a
`???` exception is raised on the Python side.
