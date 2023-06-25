import curses
import sys
import pycfg
from pyarch import *
from pyos import *

def main ():
	while cpu.cpu_alive:
		cpu.run_cycle()
		memory.run_cycle()
		timer.run_cycle()
		terminal.run_cycle()

	terminal.end()

	if cpu.sim_mode_os == 0:
		terminal.dprint(cpu.regs)
		terminal.dprint(memory.data)
	
	terminal.dprint("pysim halted")

if len(sys.argv) == 1:
	sim_mode_os = 1
else:
	sim_mode_os = 0

terminal = terminal_t()

if sim_mode_os == 1:
	memsize = pycfg.MEMORY_SIZE_WITH_OS
else:
	memsize = pycfg.MEMORY_SIZE_WITHOUT_OS

memory = memory_t(terminal, memsize)
cpu = cpu_t(terminal, memory)
timer = timer_t(cpu)

terminal.set_cpu(cpu)

cpu.sim_mode_os = sim_mode_os

if cpu.sim_mode_os == 1:
	os = os_t(cpu, memory, terminal)
	cpu.set_os(os)
	terminal.set_os(os)
else:
	load_binary_into_memory(sys.argv[1], memory, 0)
	cpu.set_pc(1)

main()
