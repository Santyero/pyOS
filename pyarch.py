import curses
import sys
import pycfg
import os

def extract_bits (num, bit_init, bit_len):
	num = num >> bit_init
	mask = (1 << bit_len) - 1
	return num & mask

class terminal_video_buffer_t:
	def __init__ (self, win):
		self.win = win
		self.win.box()
		self.h, self.w = self.win.getmaxyx()
		self.h = self.h - 2
		self.w = self.w - 2
		self.pos_x = 0
		self.pos_y = self.h - 1
		self.buffer = [[0 for x in range(self.w)] for y in range(self.h)]
		for y in range(self.h):
			for x in range(self.w):
				self.buffer[y][x] = ' '

	def next_line (self):
		for y in range(0, self.h-1):
			for x in range(self.w):
				self.buffer[y][x] = self.buffer[y+1][x]
		self.pos_x = 1
		for x in range(self.w):
			self.buffer[self.pos_y][x] = ' '

	def print_str (self, s):
		for c in s:
			if c == '\n':
				self.next_line()
			elif c == '\r':
				self.pos_x = 0
				for x in range(self.w):
					self.buffer[self.pos_y][x] = ' '
			else:
				if self.pos_x >= self.w:
					self.next_line()
				if c == '\t':
					c = ' '
				self.buffer[ self.pos_y ][ self.pos_x ] = c
				self.pos_x = self.pos_x + 1
		self.refresh()

	def refresh (self):
		for y in range(self.h):
			for x in range(self.w):
				#print(str(y)+" "+str(x))
				self.win.addch(y+1, x+1, self.buffer[y][x])
		#self.win.clear()
		#self.win.addstr(s)
		self.win.refresh()

class terminal_t:
	# python curses tutorial
	# https://github.com/dougsland/python-by-examples/blob/master/curses/subwin.py

	def __init__ (self):
		self.curses_on = 0
		self.sim_mode_os = 0
		self.key_buffer_filled = False
		self.key_buffer = 0

	def enable_curses (self):
		self.curses_on = 1

		self.stdscr = curses.initscr()
		self.stdscr.nodelay(True)

		# Enable the keypad ncurses return (instead of 16 bit value)
		self.stdscr.keypad(True)

		# Refresh after attributes
		self.stdscr.refresh()

		# No echo to screen
		curses.noecho()

		# Remove cursor
		curses.curs_set(0)

		y, x = self.stdscr.getmaxyx()
		subwin_x = x/3

		self.wins = []

		self.wins.append( terminal_video_buffer_t(self.stdscr.subwin(y, subwin_x, 0, subwin_x*0)) )
		self.wins.append( terminal_video_buffer_t(self.stdscr.subwin(y - (y/4)*3, subwin_x, (y/4)*3, subwin_x*1)) )
		self.wins.append( terminal_video_buffer_t(self.stdscr.subwin(y, subwin_x, 0, subwin_x*2)) )
		self.wins.append( terminal_video_buffer_t(self.stdscr.subwin((y/4)*3, subwin_x, 0, subwin_x*1)) )

	def set_cpu (self, cpu):
		self.cpu = cpu

	def set_os (self, os):
		self.sim_mode_os = 1
		self.os = os

	def get_key_buffer (self):
		return self.key_buffer

	def run_cycle (self):
		if self.sim_mode_os == 1:
			if self.key_buffer_filled == True:
				if self.cpu.set_interrupt(pycfg.INTERRUPT_KEYBOARD):
					self.key_buffer_filled = False
			else:
				key = self.stdscr.getch()

				if key != -1:
					self.key_buffer = key
					if self.cpu.set_interrupt(pycfg.INTERRUPT_KEYBOARD) == False:
						self.key_buffer_filled = True

			# while key_pressed != ord('q'):
			# 	self.win0.clear()
			# 	self.win1.clear()
			
			# 	self.win0.addstr("y="+str(y))
			# 	self.win1.addstr("x="+str(x))
			# 	self.win0.refresh()
			# 	self.win1.refresh()

	def dprint (self, s):
		if self.curses_on == 1:
			self.wins[0].print_str(s+"\n")
		else:
			print(s)

	def kernel_print (self, s):
		if self.curses_on == 1:
			self.wins[3].print_str(s)
		else:
			print(s)

	def console_print (self, s):
		if self.curses_on == 1:
			self.wins[1].print_str(s)
		else:
			print(s)

	def app_print (self, s):
		if self.curses_on == 1:
			self.wins[2].print_str(s)
		else:
			print(s)

	def end (self):
		if self.curses_on == 1:
			curses.echo()
			curses.endwin()
			self.curses_on = 0

class timer_t:
	def __init__ (self, cpu):
		self.cpu = cpu
		self.count = 0

	def run_cycle (self):
		if self.count >= pycfg.TIMER_THRESHOLD:
			if self.cpu.set_interrupt(pycfg.INTERRUPT_TIMER) == True:
				self.count = 0
		else:
			self.count = self.count + 1

class memory_t:
	def __init__ (self, terminal, size):
		self.terminal = terminal

		self.data = [ ]
		self.size = size

		for i in range(0, self.size):
			self.data.append(0x0000)
		self.dprint("Memory size (words): " + str(len(self.data)))

	def get_size (self):
		return self.size

	def dprint (self, s):
		self.terminal.dprint(s)

	def run_cycle (self):
		self.dprint("memory cycle")

	def write (self, addr, value):
		if addr >= self.size:
			self.dprint("memory write addr "+str(addr)+" out of bounds")
			cpu.cpu_alive = False
		else:
			self.data[addr] = value

	def read (self, addr):
		if addr >= self.size:
			self.dprint("memory read addr "+str(addr)+" out of bounds")
			cpu.cpu_alive = False
			return 0
		else:
			return self.data[addr]

class cpu_t:
	def __init__ (self, terminal, memory):
		self.terminal = terminal
		self.memory = memory

		# registers for user space
		self.regs = [0, 0, 0, 0, 0, 0, 0, 0]
		self.reg_pc = 0

		# virtual memory config
		self.paddr_offset = 0
		self.paddr_max = self.memory.get_size() - 1 # last address

		self.cpu_alive = True
		self.cycle = 0
		self.reg_inst = 0
		self.interrupt = 0

		self.gpf_vaddr = 0

		self.sim_mode_os = 0
		self.of = 0

		self.decoded_inst = {
			'type'        : 0,
			'opcode'      : 0,
			
			'r_dest'      : 0,
			'r_op1'       : 0,
			'r_op2'       : 0,
			
			'i_reg'       : 0,
			'i_imed'      : 0,
			}

	def dprint (self, s):
		self.terminal.dprint(s)

	def set_paddr_offset (self, paddr_offset):
		self.paddr_offset = paddr_offset

	def set_paddr_max (self, paddr_max):
		self.paddr_max = paddr_max

	def set_os (self, os):
		self.os = os

	def set_pc (self, pc):
		self.reg_pc = pc

	def get_pc (self):
		return self.reg_pc

	def get_reg (self, reg):
		return self.regs[reg]

	def set_reg (self, reg, value):
		self.regs[reg] = value

	def set_interrupt (self, code):
		if self.sim_mode_os == 1:
			if self.interrupt == 0:
				self.interrupt = code
				return True
			else:
				return False
		else:
			return True

	def set_exception (self, code):
		self.interrupt = code

	def memory_load (self, vaddr):
		paddr = vaddr + self.paddr_offset
		if paddr > self.paddr_max:
			self.gpf_vaddr = vaddr
			self.set_exception(pycfg.INTERRUPT_MEMORY_PROTECTION_FAULT)
			data = 0
		else:
			data = self.memory.read(paddr)
		return data

	def memory_store (self, vaddr, data):
		paddr = vaddr + self.paddr_offset
		if paddr > self.paddr_max:
			self.gpf_vaddr = vaddr
			self.set_exception(pycfg.INTERRUPT_MEMORY_PROTECTION_FAULT)
		else:
			self.memory.write(paddr, data)

	def fetch (self):
		self.dprint("Fetch addr " + str(self.reg_pc))
		self.reg_inst = self.memory_load(self.reg_pc)

		if self.interrupt == 0:
			self.reg_pc = self.reg_pc + 1

	def decode (self):
		self.dprint("Decode inst " + str(self.reg_inst))
		
		self.decoded_inst['type'] = extract_bits(self.reg_inst, 15, 1)
		
		if self.decoded_inst['type'] == 0:
			self.decoded_inst['opcode'] = extract_bits(self.reg_inst, 9, 6)
			self.decoded_inst['r_dest'] = extract_bits(self.reg_inst, 6, 3)
			self.decoded_inst['r_op1'] = extract_bits(self.reg_inst, 3, 3)
			self.decoded_inst['r_op2'] = extract_bits(self.reg_inst, 0, 3)
		else:
			self.decoded_inst['opcode'] = extract_bits(self.reg_inst, 13, 2)
			self.decoded_inst['i_reg'] = extract_bits(self.reg_inst, 10, 3)
			self.decoded_inst['i_imed'] = extract_bits(self.reg_inst, 0, 9)

	def execute (self):
		self.dprint("Execute inst")
		self.dprint(str(self.decoded_inst))
		
		if self.decoded_inst['type'] == 0:
			# add
			if self.decoded_inst['opcode'] == 0:
				self.dprint("add r"+str(self.decoded_inst['r_dest'])+", r"+str(self.decoded_inst['r_op1'])+", r"+str(self.decoded_inst['r_op2']))
				self.regs[ self.decoded_inst['r_dest'] ] = self.regs[ self.decoded_inst['r_op1'] ] + self.regs[ self.decoded_inst['r_op2'] ]
				
			# sub
			elif self.decoded_inst['opcode'] == 1:
				self.dprint("sub r"+str(self.decoded_inst['r_dest'])+", r"+str(self.decoded_inst['r_op1'])+", r"+str(self.decoded_inst['r_op2']))
				self.regs[ self.decoded_inst['r_dest'] ] = self.regs[ self.decoded_inst['r_op1'] ] - self.regs[ self.decoded_inst['r_op2'] ]
				
			# mul
			elif self.decoded_inst['opcode'] == 2:
				self.dprint("mul r"+str(self.decoded_inst['r_dest'])+", r"+str(self.decoded_inst['r_op1'])+", r"+str(self.decoded_inst['r_op2']))
				self.regs[ self.decoded_inst['r_dest'] ] = self.regs[ self.decoded_inst['r_op1'] ] * self.regs[ self.decoded_inst['r_op2'] ]
			
			# div
			elif self.decoded_inst['opcode'] == 3:
				self.dprint("sub r"+str(self.decoded_inst['r_dest'])+", r"+str(self.decoded_inst['r_op1'])+", r"+str(self.decoded_inst['r_op2']))
				self.regs[ self.decoded_inst['r_dest'] ] = self.regs[ self.decoded_inst['r_op1'] ] / self.regs[ self.decoded_inst['r_op2'] ]
				
			# cmp_eq
			elif self.decoded_inst['opcode'] == 4:
				self.dprint("cmp_eq r"+str(self.decoded_inst['r_dest'])+", r"+str(self.decoded_inst['r_op1'])+", r"+str(self.decoded_inst['r_op2']))
				if self.regs[ self.decoded_inst['r_op1'] ] == self.regs[ self.decoded_inst['r_op2'] ]:
					self.regs[ self.decoded_inst['r_dest'] ] = 1
				else:
					self.regs[ self.decoded_inst['r_dest'] ] = 0
			
			# cmp_neq
			elif self.decoded_inst['opcode'] == 5:
				self.dprint("cmp_neq r"+str(self.decoded_inst['r_dest'])+", r"+str(self.decoded_inst['r_op1'])+", r"+str(self.decoded_inst['r_op2']))
				if self.regs[ self.decoded_inst['r_op1'] ] != self.regs[ self.decoded_inst['r_op2'] ]:
					self.regs[ self.decoded_inst['r_dest'] ] = 1
				else:
					self.regs[ self.decoded_inst['r_dest'] ] = 0
			
			# load
			elif self.decoded_inst['opcode'] == 15:
				self.dprint("load r"+str(self.decoded_inst['r_dest'])+", [r"+str(self.decoded_inst['r_op1'])+"]")
				addr = self.regs[ self.decoded_inst['r_op1'] ]
				data = self.memory_load(addr)
				if self.interrupt == 0:
					self.regs[ self.decoded_inst['r_dest'] ] = data
			
			# store
			elif self.decoded_inst['opcode'] == 16:
				self.dprint("store [r"+str(self.decoded_inst['r_op1'])+"], "+str(self.decoded_inst['r_op2']))
				addr = self.regs[ self.decoded_inst['r_op1'] ]
				self.memory_store(addr, self.regs[ self.decoded_inst['r_op2'] ] )
			
			# syscall
			elif self.decoded_inst['opcode'] == 63:
				self.dprint("syscall")
				if self.sim_mode_os == 1:
					self.os.syscall()
				else:
					fake_syscall_handler(self);
			
			else:
				self.dprint("opcode " + str(self.decoded_inst['opcode']) + " invalido tipo R")
				self.cpu_alive = False
		elif self.decoded_inst['type'] == 1:
			# jump
			if self.decoded_inst['opcode'] == 0:
				self.dprint("jump "+str(self.decoded_inst['i_imed']))
				self.reg_pc = self.decoded_inst['i_imed']
			
			# jump_cond
			elif self.decoded_inst['opcode'] == 1:
				self.dprint("jump_cond r"+str(self.decoded_inst['i_reg'])+", "+str(self.decoded_inst['i_imed']))
				if self.regs[ self.decoded_inst['i_reg'] ] == 1:
					self.reg_pc = self.decoded_inst['i_imed']
			
			# mov
			elif self.decoded_inst['opcode'] == 3:
				self.dprint("mov r"+str(self.decoded_inst['i_reg'])+", "+str(self.decoded_inst['i_imed']))
				self.regs[ self.decoded_inst['i_reg'] ] = self.decoded_inst['i_imed']
			
			else:
				self.dprint("opcode " + str(self.decoded_inst['opcode']) + " invalido tipo I")
				self.cpu_alive = False
		else:
			self.dprint("instr type " + str(self.decoded_inst['type']) + " invalido")
			self.cpu_alive = False
		
		self.dprint(str(self.regs))


	def run_cycle (self):
		self.dprint("---------------------------------")
		self.dprint("Cycle " + str(self.cycle))
		
		if self.interrupt == 0:
			pc = self.reg_pc
			
			self.fetch()

			if self.interrupt == 0:
				self.decode()

				if self.interrupt == 0:
					self.execute()

					if self.interrupt != 0:
						self.reg_pc = pc
				else:
					self.reg_pc = pc
			else:
				self.reg_pc = pc

		if self.interrupt != 0:
			if self.sim_mode_os == 1:
				self.os.handle_interrupt(self.interrupt)
				self.interrupt = 0
		
		self.cycle = self.cycle + 1

def load_binary_into_memory (fname, memory, paddr):
	if not os.path.isfile(fname):
		print("file "+fname+" does not exists")
		sys.exit()
	if (os.path.getsize(fname) % 2) == 1:
		print("file size must be even")
		sys.exit()
	bpos = 0
	i = paddr
	with open(fname, "rb") as f:
		while True:
			byte = f.read(1)
			if not byte:
				break
			byte = ord(byte)
			if bpos == 0:
				lower_byte = byte
			else:
				word = lower_byte | (byte << 8)
				memory.write(i, word)
				i = i + 1
			bpos = bpos ^ 1
	print("loaded " + str(i) + " words into memory")
	# bytes_read = open(fname, "rb").read()
	# for byte in bytes_read:
	# 	print(type(ord(byte)))
		#print(type(byte))

def fake_syscall_handler (cpu):
	if cpu.get_reg(0) == 0: # halt service
		cpu.cpu_alive = False
		cpu.dprint("halt service")