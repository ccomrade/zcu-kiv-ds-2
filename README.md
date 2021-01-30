# zcu-kiv-ds-2

This is the second KIV/DS project. It demonstrates the
[Chandy–Lamport algorithm](https://en.wikipedia.org/wiki/Chandy%E2%80%93Lamport_algorithm)
for obtaining consistent global state snapshot of a distributed system. The underlying application is a simple distributed
simulation of bank account transactions. It is built on top of the [ZeroMQ](https://zeromq.org/) messaging library.

Note that this is just a school project without any practical use.

## Architecture

```
┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓
┃      Node 1      ┃   ┃      Node 2      ┃   ┃      Node 3      ┃   ┃      Node 4      ┃   ┃      Node 5      ┃
┃                  ┃   ┃                  ┃   ┃                  ┃   ┃                  ┃   ┃                  ┃
┃  192.168.152.11  ┃   ┃  192.168.152.12  ┃   ┃  192.168.152.13  ┃   ┃  192.168.152.14  ┃   ┃  192.168.152.15  ┃
┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫
┃     ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃     ┃
┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛
           ┃    ┃         ┃    ┃  ┃    ┃         ┃    ┃  ┃    ┃         ┃    ┃  ┃    ┃         ┃    ┃
           ┃    ┗━━━━━━❯❯━━━━━━┛  ┗━━━━━━❮❮━━━━━━┛    ┃  ┃    ┗━━━━━━❯❯━━━━━━┛  ┗━━━━━━❮❮━━━━━━┛    ┃
           ┗━━━━━━❮❮━━━━━━┛            ┗━━━━━━❯❯━━━━━━┛  ┗━━━━━━❮❮━━━━━━┛            ┗━━━━━━❯❯━━━━━━┛
```

All connections in the system are shown above. There are no other connections between the nodes.

Nodes have at most 3 sockets. One IN socket for receiving messages and one or two OUT sockets for sending messages.
Each IN socket is a **ZeroMQ ROUTER** socket. Each OUT socket is a **ZeroMQ DEALER** socket.
The left OUT socket of each node is connected to the node with the previous ID.
The right OUT socket of each node is connected to the node with the next ID.
This simplifies message routing between the nodes.
All IN sockets are bound to `tcp://*:55502`.

## Message types

```json
{
	"type": "CREDIT",
	"src_node_id': 1,
	"dst_node_id': 2,
	"amount": 10000
}
```

```json
{
	"type": "DEBIT",
	"src_node_id': 1,
	"dst_node_id': 2,
	"amount": 10000
}
```

```json
{
	"type": "MARKER",
	"src_node_id": 1,
	"dst_node_id": 2,
	"snapshot_id": 1
}
```

```json
{
	"type": "STATE",
	"src_node_id": 1,
	"dst_node_id": 2,
	"account_balance": 5000000
}
```


