# zcu-kiv-ds-2

This is the second KIV/DS project. It demonstrates the
[Chandy–Lamport algorithm](https://en.wikipedia.org/wiki/Chandy%E2%80%93Lamport_algorithm)
for obtaining consistent global state snapshot of a distributed system. The underlying application is a simple distributed
simulation of bank account transactions. It is built on top of the [ZeroMQ](https://zeromq.org/) messaging library.

Note that this is just a school project without any practical use.

## Architecture

Here's an overview of the system:

```
┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━┓
┃      Node 1      ┃   ┃      Node 2      ┃   ┃      Node 3      ┃   ┃      Node 4      ┃
┃                  ┃   ┃                  ┃   ┃                  ┃   ┃                  ┃
┃  192.168.152.11  ┃   ┃  192.168.152.12  ┃   ┃  192.168.152.13  ┃   ┃  192.168.152.14  ┃
┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫   ┣━━━━━┳━━━━━━┳━━━━━┫
┃     ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃ OUT ┃   ┃ OUT ┃  IN  ┃     ┃
┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛   ┗━━━━━┻━━━━━━┻━━━━━┛
           ┃    ┃         ┃    ┃  ┃    ┃         ┃    ┃  ┃    ┃         ┃    ┃
           ┃    ┗━━━━━━❯❯━━━━━━┛  ┗━━━━━━❮❮━━━━━━┛    ┃  ┃    ┗━━━━━━❯❯━━━━━━┛
           ┗━━━━━━❮❮━━━━━━┛            ┗━━━━━━❯❯━━━━━━┛  ┗━━━━━━❮❮━━━━━━┛
```

Each node maintains a single bank account and randomly generates transactions with all other nodes.

There are no other connections between the nodes except those shown above.
Nodes have at most 3 sockets. One IN socket for receiving messages and one or two OUT sockets for sending messages.
Each IN socket is a **ZeroMQ ROUTER** socket. Each OUT socket is a **ZeroMQ DEALER** socket.
The left OUT socket of each node is connected to the node with the previous ID.
The right OUT socket of each node is connected to the node with the next ID.
This simplifies message routing between the nodes.

In addition, every node has one service socket used to perform service operations on the node.
This is a **ZeroMQ REP** socket and is not accessible from the other nodes.
The only implemented service operation is obtaining a global state snapshot of the system within the node.

All IN sockets are bound to `tcp://*:55502`.
All service sockets are bound to `tcp://127.0.0.1:55512`.

## Message types

Examples of all message types are listed below. All messages are in JSON format.

### IN/OUT socket messages

`CREDIT` message used to send a certain amount from one bank account to another.

```json
{
	"type": "CREDIT",
	"src_node_id": 1,
	"dst_node_id": 2,
	"amount": 10000
}
```

`DEBIT` message used to request a certain amount from another bank account.
The target node replies with a `CREDIT` message if it has a sufficient balance in its bank account.

```json
{
	"type": "DEBIT",
	"src_node_id": 1,
	"dst_node_id": 2,
	"amount": 10000
}
```

`MARKER` message used to obtain a consistent snapshot of all bank account balances.
See the [Chandy–Lamport algorithm](https://en.wikipedia.org/wiki/Chandy%E2%80%93Lamport_algorithm) for more information.

```json
{
	"type": "MARKER",
	"src_node_id": 1,
	"dst_node_id": 2,
	"snapshot_id": 1
}
```

`STATE` message used to send the resulting bank account balance to the node trying to obtain a snapshot.

```json
{
	"type": "STATE",
	"src_node_id": 1,
	"dst_node_id": 2,
	"account_balance": 5000000
}
```

### Service socket messages

The service command used obtain a global state snapshot:

```json
{
	"cmd": "snapshot"
}
```

The result received from the service socket after sending the previous command:

```json
{
	"snapshot":
	{
		"nodes":
		{
			"1": 5000000,
			"2": 5000000,
			"3": 5000000,
			"4": 5000000
		}
	}
}
```

## Usage

### Setup

First of all, the infrastructure has to be created. Use the following command to create and run a VM for each node:

```
vagrant up
```

When a node is booted up and fully configured, it immediately starts to send random transactions to the other nodes.

### Testing

To see bank account balances, you need to access the command line on any node. Use the command below:

```
vagrant ssh node-2
```

Now you can run the following command to obtain a snapshot with the current balances:

```
get_snapshot
```

Here's an example of possible output:

```
1:  4249032
2:  6163726
3:  4580888
4:  5006354
===========
   20000000
```

You can also view individual transactions on the node in real-time by watching the system log:

```
journalctl -f
```

Here's an example of possible output:

```
Jan 31 16:09:30 node-2 node[396]:  DEBIT  to  4 with amount  11617
Jan 31 16:09:30 node-2 node[396]: CREDIT from 4 with amount +11617 (= 4909617)
Jan 31 16:09:30 node-2 node[396]: CREDIT from 1 with amount +35971 (= 4945588)
Jan 31 16:09:30 node-2 node[396]: CREDIT from 1 with amount +19899 (= 4965487)
Jan 31 16:09:31 node-2 node[396]:  DEBIT  to  1 with amount  19693
Jan 31 16:09:31 node-2 node[396]: CREDIT from 1 with amount +19693 (= 4985180)
Jan 31 16:09:31 node-2 node[396]:  DEBIT from 1 with amount -36881 (= 4948299)
Jan 31 16:09:31 node-2 node[396]:  DEBIT from 1 with amount -47297 (= 4901002)
Jan 31 16:09:32 node-2 node[396]: CREDIT  to  3 with amount -41148 (= 4859854)
Jan 31 16:09:32 node-2 node[396]: CREDIT from 1 with amount +37395 (= 4897249)
Jan 31 16:09:33 node-2 node[396]:  DEBIT  to  4 with amount  20444
Jan 31 16:09:33 node-2 node[396]: CREDIT from 4 with amount +20444 (= 4917693)
Jan 31 16:09:33 node-2 node[396]:  DEBIT  to  3 with amount  34603
Jan 31 16:09:33 node-2 node[396]: CREDIT from 3 with amount +34603 (= 4952296)
Jan 31 16:09:34 node-2 node[396]:  DEBIT  to  1 with amount  28827
Jan 31 16:09:34 node-2 node[396]: CREDIT from 1 with amount +28827 (= 4981123)
Jan 31 16:09:34 node-2 node[396]: CREDIT from 3 with amount +36224 (= 5017347)
Jan 31 16:09:35 node-2 node[396]: CREDIT from 4 with amount +12980 (= 5030327)
```

### Cleanup

Finally, to shut down and remove all created VMs, use the following command:

```
vagrant destroy -f
```
