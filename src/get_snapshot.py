#!/usr/bin/env python3

import zmq

def run():
	context = zmq.Context()

	socket = context.socket(zmq.REQ)
	socket.connect('tcp://127.0.0.1:55512')

	socket.send_json({
		'cmd': 'snapshot'
	})

	result = socket.recv_json()

	total_balance = 0

	for node_id, account_balance in result['snapshot']['nodes'].items():
		print('{}: {:>8}'.format(node_id, account_balance))
		total_balance += account_balance

	print('===========')
	print('{:>11}'.format(total_balance))

if __name__ == '__main__':
	run()
