#!/usr/bin/env python3

import os
import logging
import random
import time
import json
import zmq

INITIAL_BALANCE = 5000000

TRANSACTION_MIN_AMOUNT = 10000
TRANSACTION_MAX_AMOUNT = 50000

# milliseconds
SEND_MIN_DELAY = 20
SEND_MAX_DELAY = 2000

NODE_ID           = int(os.environ['NODE_ID'])
NODE_COUNT        = int(os.environ['NODE_COUNT'])
NODE_PORT         = int(os.environ['NODE_PORT'])
NODE_SERVICE_PORT = int(os.environ['NODE_SERVICE_PORT'])

def get_all_other_nodes_ids():
	return [i for i in range(1, NODE_COUNT + 1) if i != NODE_ID]

def get_current_time_ms():
	return int(time.time() * 1000)

def calculate_timeout_ms(time_point_ms):
	current_time_ms = get_current_time_ms()

	if time_point_ms <= current_time_ms:
		return 1

	return time_point_ms - current_time_ms

class Snapshot:
	def __init__(self, account_balance):
		# one entry for each node
		self.is_channel_empty = {i: False for i in range(1, NODE_COUNT + 1)}
		self.is_node_complete = {i: False for i in range(1, NODE_COUNT + 1)}
		self.node_states = {i: 0 for i in range(1, NODE_COUNT + 1)}

		self.is_channel_empty[NODE_ID] = True
		self.is_node_complete[NODE_ID] = True
		self.node_states[NODE_ID] = account_balance

	def all_channels_empty(self):
		return all(self.is_channel_empty.values())

	def all_nodes_complete(self):
		return all(self.is_node_complete.values())

class Node:
	def __init__(self):
		self.context = zmq.Context()
		self.account_balance = INITIAL_BALANCE
		self.snapshots = {}

		logging.info('Account balance is %d', self.account_balance)

		self.socket_in = self.context.socket(zmq.ROUTER)
		self.socket_in.bind('tcp://*:' + str(NODE_PORT))

		logging.info('Listening on port %d', NODE_PORT)

		self.socket_service = self.context.socket(zmq.REP)
		self.socket_service.bind('tcp://127.0.0.1:' + str(NODE_SERVICE_PORT))

		logging.info('Listening on service port %d', NODE_SERVICE_PORT)

		# connect to the node on the left side
		if NODE_ID > 1:
			address = os.environ['NODE_PREV_ADDRESS']

			logging.info('Connecting to prev-node at %s', address)

			self.socket_out_prev = self.context.socket(zmq.DEALER)
			self.socket_out_prev.connect('tcp://' + address)
		else:
			self.socket_out_prev = None

		# connect to the node on the right side
		if NODE_ID < NODE_COUNT:
			address = os.environ['NODE_NEXT_ADDRESS']

			logging.info('Connecting to next-node at %s', address)

			self.socket_out_next = self.context.socket(zmq.DEALER)
			self.socket_out_next.connect('tcp://' + address)
		else:
			self.socket_out_next = None

		self.poller = zmq.Poller()
		self.poller.register(self.socket_in, zmq.POLLIN)
		self.poller.register(self.socket_service, zmq.POLLIN)

		logging.info('Node initialized')

	def send_message(self, msg):
		dst_node_id = int(msg['dst_node_id'])

		assert dst_node_id != NODE_ID

		if dst_node_id > NODE_ID:
			self.socket_out_next.send_json(msg)
		elif dst_node_id < NODE_ID:
			self.socket_out_prev.send_json(msg)

	def receive_message(self):
		# ignore the address frame from ROUTER socket
		self.socket_in.recv()

		return self.socket_in.recv_json()

	def update_my_state_in_snapshots(self, src_node_id, amount):
		for snapshot in self.snapshots.values():
			if not snapshot.is_channel_empty[src_node_id]:
				snapshot.node_states[NODE_ID] += amount

	def credit(self, src_node_id, amount):
		if src_node_id < 1 or src_node_id > NODE_COUNT or src_node_id == NODE_ID or amount <= 0:
			return

		self.account_balance += amount

		# record this message in active snapshots if needed
		self.update_my_state_in_snapshots(src_node_id, amount)

		logging.info('CREDIT from %d with amount +%d (= %d)', src_node_id, amount, self.account_balance)

	def debit(self, src_node_id, amount):
		if src_node_id < 1 or src_node_id > NODE_COUNT or src_node_id == NODE_ID or amount <= 0:
			return

		if self.account_balance < amount:
			logging.warning('Insufficient balance to perform DEBIT with amount %d from %d', amount, src_node_id)
			return

		self.send_message({
			'type': 'CREDIT',
			'src_node_id': NODE_ID,
			'dst_node_id': src_node_id,
			'amount': amount
		})

		self.account_balance -= amount

		# record this message in active snapshots if needed
		self.update_my_state_in_snapshots(src_node_id, -amount)

		logging.info(' DEBIT from %d with amount -%d (= %d)', src_node_id, amount, self.account_balance)

	def send_marker_to_all_nodes(self, snapshot_id):
		for dst_node_id in get_all_other_nodes_ids():
			self.send_message({
				'type': 'MARKER',
				'src_node_id': NODE_ID,
				'dst_node_id': dst_node_id,
				'snapshot_id': snapshot_id
			})

	def process_marker(self, src_node_id, snapshot_id):
		# snapshot ID is always ID of the node that initiated the snapshot
		if src_node_id < 1 or src_node_id > NODE_COUNT or snapshot_id < 1 or snapshot_id > NODE_COUNT:
			return

		# marker received for the first time
		if snapshot_id not in self.snapshots:
			# step 1: save our state
			self.snapshots[snapshot_id] = Snapshot(self.account_balance)

			# step 2: send the marker to all channels
			self.send_marker_to_all_nodes(snapshot_id)

		self.snapshots[snapshot_id].is_channel_empty[src_node_id] = True

		if snapshot_id != NODE_ID and self.snapshots[snapshot_id].all_channels_empty():
			# we are done
			account_balance = self.snapshots[snapshot_id].node_states[NODE_ID]

			del self.snapshots[snapshot_id]

			# send our state to the node that initiated the snapshot
			self.send_message({
				'type': 'STATE',
				'src_node_id': NODE_ID,
				'dst_node_id': snapshot_id,
				'account_balance': account_balance
			})

	def snapshot_begin(self):
		if NODE_ID in self.snapshots:
			return

		self.snapshots[NODE_ID] = Snapshot(self.account_balance)

		self.send_marker_to_all_nodes(NODE_ID)

		# single node system
		if self.snapshots[NODE_ID].all_nodes_complete():
			self.snapshot_end()

	def snapshot_end(self):
		if NODE_ID not in self.snapshots:
			return

		self.socket_service.send_json({
			'snapshot': {
				'nodes': self.snapshots[NODE_ID].node_states
			}
		})

		del self.snapshots[NODE_ID]

	def collect_state(self, src_node_id, account_balance):
		if src_node_id < 1 or src_node_id > NODE_COUNT or src_node_id == NODE_ID or NODE_ID not in self.snapshots:
			return

		self.snapshots[NODE_ID].node_states[src_node_id] = account_balance
		self.snapshots[NODE_ID].is_node_complete[src_node_id] = True

		if self.snapshots[NODE_ID].all_nodes_complete():
			self.snapshot_end()

	def on_message(self, msg):
		msg_type = str(msg['type'])
		src_node_id = int(msg['src_node_id'])
		dst_node_id = int(msg['dst_node_id'])

		if dst_node_id == NODE_ID:
			if msg_type == 'CREDIT':
				self.credit(src_node_id, int(msg['amount']))
			elif msg_type == 'DEBIT':
				self.debit(src_node_id, int(msg['amount']))
			elif msg_type == 'MARKER':
				self.process_marker(src_node_id, int(msg['snapshot_id']))
			elif msg_type == 'STATE':
				self.collect_state(src_node_id, int(msg['account_balance']))
			else:
				logging.warning('Unknown message of type %s from %d', msg_type, src_node_id)
		else:
			# route message
			self.send_message(msg)

	def send_random_transaction(self):
		if NODE_COUNT < 2:
			return

		operation = random.choice(['CREDIT', 'DEBIT'])
		amount = random.randint(TRANSACTION_MIN_AMOUNT, TRANSACTION_MAX_AMOUNT)

		if operation == 'CREDIT' and self.account_balance < amount:
			operation = 'DEBIT'

		dst_node_id = random.choice(get_all_other_nodes_ids())

		self.send_message({
			'type': operation,
			'src_node_id': NODE_ID,
			'dst_node_id': dst_node_id,
			'amount': amount
		})

		if operation == 'CREDIT':
			self.account_balance -= amount

			logging.info('CREDIT  to  %d with amount -%d (= %d)', dst_node_id, amount, self.account_balance)
		else:
			logging.info(' DEBIT  to  %d with amount  %d', dst_node_id, amount)

	def run(self):
		next_send_ms = get_current_time_ms() + random.randint(SEND_MIN_DELAY, SEND_MAX_DELAY)

		while True:
			events = dict(self.poller.poll(timeout=calculate_timeout_ms(next_send_ms)))

			if not events:
				# poll timeout
				self.send_random_transaction()

				next_send_ms = get_current_time_ms() + random.randint(SEND_MIN_DELAY, SEND_MAX_DELAY)
			else:
				if self.socket_in in events:
					try:
						msg = self.receive_message()

						self.on_message(msg)

					except (json.JSONDecodeError, KeyError, ValueError):
						logging.warning('Invalid message')

				elif self.socket_service in events:
					try:
						msg = self.socket_service.recv_json()
						cmd = msg['cmd']

						if cmd == 'snapshot':
							self.snapshot_begin()
						else:
							logging.warning('Unknown service command %s', cmd)

					except (json.JSONDecodeError, KeyError, ValueError):
						logging.warning('Invalid service command')

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO, format='')
	Node().run()
