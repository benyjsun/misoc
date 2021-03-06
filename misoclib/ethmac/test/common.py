import random, copy

from migen.fhdl.std import *
from migen.flow.actor import Sink, Source
from migen.genlib.record import *

from misoclib.ethmac.common import *

def seed_to_data(seed, random=True):
	if random:
		return (seed * 0x31415979 + 1) & 0xffffffff
	else:
		return seed

def check(p1, p2):
	p1 = copy.deepcopy(p1)
	p2 = copy.deepcopy(p2)
	if isinstance(p1, int):
		return 0, 1, int(p1 != p2)
	else:
		if len(p1) >= len(p2):
			ref, res = p1, p2
		else:
			ref, res = p2, p1
		shift = 0
		while((ref[0] != res[0]) and (len(res)>1)):
			res.pop(0)
			shift += 1
		length = min(len(ref), len(res))
		errors = 0
		for i in range(length):
			if ref.pop(0) != res.pop(0):
				errors += 1
		return shift, length, errors

def randn(max_n):
	return random.randint(0, max_n-1)

class Packet(list):
	def __init__(self, init=[]):
		self.ongoing = False
		self.done = False
		for data in init:
			self.append(data)

class PacketStreamer(Module):
	def __init__(self, description):
		self.source = Source(description)
		###
		self.packets = []
		self.packet = Packet()
		self.packet.done = 1

	def send(self, packet):
		packet = copy.deepcopy(packet)
		self.packets.append(packet)

	def do_simulation(self, selfp):
		if len(self.packets) and self.packet.done:
			self.packet = self.packets.pop(0)
		if not self.packet.ongoing and not self.packet.done:
			selfp.source.stb = 1
			selfp.source.sop = 1
			selfp.source.d = self.packet.pop(0)
			self.packet.ongoing = True
		elif selfp.source.stb == 1 and selfp.source.ack == 1:
			selfp.source.sop = 0
			selfp.source.eop = (len(self.packet) == 1)
			if len(self.packet) > 0:
				selfp.source.stb = 1
				selfp.source.d = self.packet.pop(0)
			else:
				self.packet.done = 1
				selfp.source.stb = 0

class PacketLogger(Module):
	def __init__(self, description):
		self.sink = Sink(description)
		###
		self.packet = Packet()

	def receive(self):
		self.packet.done = 0
		while self.packet.done == 0:
			yield

	def do_simulation(self, selfp):
		selfp.sink.ack = 1
		if selfp.sink.stb == 1 and selfp.sink.sop == 1:
			self.packet = Packet()
			self.packet.append(selfp.sink.d)
		elif selfp.sink.stb:
			self.packet.append(selfp.sink.d)
		if selfp.sink.stb == 1 and selfp.sink.eop == 1:
			self.packet.done = True

class AckRandomizer(Module):
	def __init__(self, description, level=0):
		self.level = level

		self.sink = Sink(description)
		self.source = Source(description)

		self.run = Signal()

		self.comb += \
			If(self.run,
				Record.connect(self.sink, self.source)
			).Else(
				self.source.stb.eq(0),
				self.sink.ack.eq(0),
			)

	def do_simulation(self, selfp):
		n = randn(100)
		if n < self.level:
			selfp.run = 0
		else:
			selfp.run = 1

