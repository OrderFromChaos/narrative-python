# Task P8 — memcached-compatible cache server

Serve a subset of the memcached text protocol over TCP with asyncio, with expiry and a memory limit
enforced by least-recently-used eviction.

Use the standard library only.

## Running

`python3 -m <package> --port 11311 --max-bytes 1048576`. It listens on 127.0.0.1 and serves any
number of clients at once. It runs until interrupted, then closes every connection and exits 0.

## The protocol

A client sends command lines ending in `\r\n`. A storage command is followed by a data block of
exactly the announced number of bytes, then `\r\n`.

| command | reply |
|---|---|
| `set <key> <flags> <exptime> <bytes> [noreply]` | `STORED` |
| `add …` same arguments | `STORED`, or `NOT_STORED` when the key exists |
| `replace …` same arguments | `STORED`, or `NOT_STORED` when the key does not exist |
| `cas <key> <flags> <exptime> <bytes> <cas> [noreply]` | `STORED`, `EXISTS` when the cas value is stale, `NOT_FOUND` |
| `get <key>…` | one `VALUE <key> <flags> <bytes>` line and the data per key found, then `END` |
| `gets <key>…` | as `get`, with the cas value as a fifth field of each `VALUE` line |
| `delete <key> [noreply]` | `DELETED` or `NOT_FOUND` |
| `incr <key> <amount> [noreply]`, `decr …` | the new value, or `NOT_FOUND` |
| `quit` | closes the connection, no reply |

Every reply line ends in `\r\n`. `noreply` suppresses the reply of a command that succeeds or fails
normally. It does not suppress an error.

- **Keys** are 1 to 250 bytes with no control characters and no space.
- **Flags** are an unsigned 32-bit integer, stored and returned unchanged.
- **Exptime**: `0` means never. A value up to 2,592,000 (30 days) is a number of seconds from now. A
  larger value is an absolute Unix time. A negative value means the item is already expired. An
  expired item behaves as absent for every command and takes no memory.
- **Cas values** are unsigned 64-bit integers. The first stored version of any item gets 1, and every
  later change to any item takes the next integer.
- **incr and decr** work on a value that is the decimal form of an unsigned 64-bit integer. incr
  wraps around at 2^64. decr stops at 0. The stored value is the result's decimal form, with no
  padding.
- **Errors**: an unknown command gets `ERROR`. A malformed command line, a bad key, a data block
  whose length does not match or that is not followed by `\r\n`, or incr and decr on a non-numeric
  value get `CLIENT_ERROR <message>`. After a bad data block, the server reads on from the next
  `\r\n`. A command line longer than 2,048 bytes gets `CLIENT_ERROR line too long` and the
  connection is closed.

## Memory limit

The size of an item is its key length plus its data length plus 50 bytes. When storing an item
would take the total over `--max-bytes`, the least recently used items are evicted until it fits.
Storing an item and reading it with `get`, `gets`, `incr` or `decr` both count as use. An item
larger than `--max-bytes` on its own gets `SERVER_ERROR object too large for cache` and nothing is
evicted.

## Logging

Log a connection opening and closing at DEBUG, and every eviction at INFO with the key and its size.

## What is left to you

The package and module layout, the `CLIENT_ERROR` messages, how the server tracks time, and any
behaviour this specification does not fix.

## The fixture

`fixture/session.txt` is a scripted session: lines starting `> ` are sent, and lines starting `< `
are the expected reply. `\r\n` is implied at each line end. The server under test runs with
`--max-bytes 300`. Its cases: `add` on an existing key, `cas` with a stale value, an absolute
exptime in the past, an exptime of exactly 2,592,000, a negative exptime, a multi-key `get` with a
miss, incr past 2^64, decr below 0, incr on a non-numeric value, a short data block, `noreply`,
LRU eviction where a `get` changes which item goes, an item too large for the cache, and an
unknown command.
