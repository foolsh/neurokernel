#!/usr/bin/env python

"""
Create and run multiple empty LPUs to time data reception throughput.
"""

import argparse
import itertools
import time

import numpy as np
import pycuda.driver as drv

from neurokernel.base import setup_logger
from neurokernel.core import Manager, Module, PORT_DATA, PORT_CTRL, PORT_TIME
from neurokernel.pattern import Pattern
from neurokernel.plsel import Selector, SelectorMethods
from neurokernel.tools.comm import get_random_port

class MyModule(Module):
    """
    Empty module class.

    This module class doesn't do anything in its execution step apart from
    transmit/receive dummy data. All spike ports are assumed to
    produce/consume data at every step.
    """

    def __init__(self, sel,
                 sel_in, sel_out,
                 sel_gpot, sel_spike,
                 data_gpot=None, data_spike=None,
                 columns=['interface', 'io', 'type'],
                 port_data=PORT_DATA, port_ctrl=PORT_CTRL, port_time=PORT_TIME,
                 id=None, device=None, debug=False):
        if data_gpot is None:
            data_gpot = np.zeros(SelectorMethods.count_ports(sel_gpot), float)
        if data_spike is None:
            data_spike = np.zeros(SelectorMethods.count_ports(sel_spike), int)
        super(MyModule, self).__init__(sel, sel_in, sel_out,
                                       sel_gpot, sel_spike,
                                       data_gpot, data_spike,
                                       columns, port_data, port_ctrl, port_time,
                                       id, device, debug, True)

        self.pm['gpot'][self.interface.out_ports().gpot_ports(tuples=True)] = 1.0
        self.pm['spike'][self.interface.out_ports().spike_ports(tuples=True)] = 1

def gen_sels(n_lpu, n_spike, n_gpot):
    """
    Generate port selectors for LPUs in benchmark test.

    Parameters
    ----------
    n_lpu : int
        Number of LPUs. Must be at least 2.
    n_spike : int
        Total number of input and output spiking ports any 
        single LPU exposes to any other LPU. Each LPU will therefore
        have 2*n_spike*(n_lpu-1) total spiking ports.
    n_gpot : int
        Total number of input and output graded potential ports any 
        single LPU exposes to any other LPU. Each LPU will therefore
        have 2*n_gpot*(n_lpu-1) total graded potential ports.

    Returns
    -------
    results : dict of tuples
        The keys of the result are the module IDs; the values are tuples
        containing the respective selectors for input, output, graded potential, 
        and spiking ports.
    """

    assert n_lpu >= 2
    assert n_spike >= 0
    assert n_gpot >= 0

    results = {}

    for i in xrange(n_lpu):
        lpu_id = 'lpu%s' % i
        other_lpu_ids = '['+','.join(['lpu%s' % j for j in xrange(n_lpu) if j != i])+']'

        # Structure ports as 
        # /lpu_id/in_or_out/spike_or_gpot/[other_lpu_ids,..]/[0:n_spike]
        sel_in_gpot = Selector('/%s/in/gpot/%s/[0:%i]' % \
                    (lpu_id, other_lpu_ids, n_gpot))
        sel_in_spike = Selector('/%s/in/spike/%s/[0:%i]' % \
                    (lpu_id, other_lpu_ids, n_spike))
        sel_out_gpot = Selector('/%s/out/gpot/%s/[0:%i]' % \
                    (lpu_id, other_lpu_ids, n_gpot))
        sel_out_spike = Selector('/%s/out/spike/%s/[0:%i]' % \
                    (lpu_id, other_lpu_ids, n_spike))
        results[lpu_id] = (Selector.union(sel_in_gpot, sel_in_spike),
                           Selector.union(sel_out_gpot, sel_out_spike),
                           Selector.union(sel_in_gpot, sel_out_gpot),
                           Selector.union(sel_in_spike, sel_out_spike))

    return results

def emulate(n_lpu, n_spike, n_gpot, steps):
    """
    Benchmark inter-LPU communication throughput.

    Each LPU is configured to use a different local GPU.

    Parameters
    ----------
    n_lpu : int
        Number of LPUs. Must be at least 2 and no greater than the number of
        local GPUs.
    n_spike : int
        Total number of input and output spiking ports any 
        single LPU exposes to any other LPU. Each LPU will therefore
        have 2*n_spike*(n_lpu-1) total spiking ports.
    n_gpot : int
        Total number of input and output graded potential ports any 
        single LPU exposes to any other LPU. Each LPU will therefore
        have 2*n_gpot*(n_lpu-1) total graded potential ports.
    steps : int
        Number of steps to execute.

    Returns
    -------
    throughput : float
        Received data throughput in bytes/seconds.
    exec_time : float
        Execution time in seconds.
    """

    # Time everything starting with manager initialization:
    start = time.time()

    # Check whether a sufficient number of GPUs are available:
    drv.init()
    if n_lpu > drv.Device.count():
        raise RuntimeError('insufficient number of available GPUs.')

    man = Manager(get_random_port(), get_random_port(), get_random_port())
    man.add_brok()

    # Set up modules:
    sel_dict = gen_sels(n_lpu, n_spike, n_gpot)
    for i in xrange(n_lpu):
        lpu_i = 'lpu%s' % i
        sel_in, sel_out, sel_gpot, sel_spike = sel_dict[lpu_i]
        sel = Selector.union(sel_in, sel_out, sel_gpot, sel_spike)
        m = MyModule(sel, sel_in, sel_out,
                     sel_gpot, sel_spike,
                     port_data=man.port_data, port_ctrl=man.port_ctrl,
                     port_time=man.port_time,
                     id=lpu_i, device=i, debug=args.debug)
        man.add_mod(m)

    # Set up connections between module pairs:
    for i, j in itertools.combinations(xrange(n_lpu), 2):
        lpu_i = 'lpu%s' % i
        lpu_j = 'lpu%s' % j
        sel_in_i, sel_out_i, sel_gpot_i, sel_spike_i = sel_dict[lpu_i]            
        sel_in_j, sel_out_j, sel_gpot_j, sel_spike_j = sel_dict[lpu_j]            

        # The order of these two selectors is important; the individual 'from'
        # and 'to' ports must line up properly for Pattern.from_concat to
        # produce the right pattern:
        sel_from = sel_out_i+sel_out_j
        sel_to = sel_in_j+sel_in_i
        man.log_info('before from_concat')
        pat = Pattern.from_concat(sel_from, sel_to,
                                  from_sel=sel_from, to_sel=sel_to, data=1)

        man.log_info('before setting attribs')
        pat.interface[sel_in_i, 'interface', 'io'] = [0, 'out']
        pat.interface[sel_out_i, 'interface', 'io'] = [0, 'in']
        pat.interface[sel_gpot_i, 'interface', 'type'] = [0, 'gpot']
        pat.interface[sel_spike_i, 'interface', 'type'] = [0, 'spike']
        pat.interface[sel_in_j, 'interface', 'io'] = [1, 'out']
        pat.interface[sel_out_j, 'interface', 'io'] = [1, 'in']
        pat.interface[sel_gpot_j, 'interface', 'type'] = [1, 'gpot']
        pat.interface[sel_spike_j, 'interface', 'type'] = [1, 'spike']
        man.log_info('before connecting modules')
        man.connect(man.modules[lpu_i], man.modules[lpu_j], pat, 0, 1)

    man.start(steps=steps)
    man.stop()
    return man.get_throughput(), (time.time()-start)

if __name__ == '__main__':
    num_lpus = 2
    num_gpot = 100
    num_spike = 100
    max_steps = 100

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False,
                        dest='debug', action='store_true',
                        help='Enable debug mode.')
    parser.add_argument('-l', '--log', default='none', type=str,
                        help='Log output to screen [file, screen, both, or none; default:none]')
    parser.add_argument('-u', '--num_lpus', default=num_lpus, type=int,
                        help='Number of LPUs [default: %s]' % num_lpus)
    parser.add_argument('-s', '--num_spike', default=num_spike, type=int,
                        help='Number of spiking ports [default: %s]' % num_spike)
    parser.add_argument('-g', '--num_gpot', default=num_gpot, type=int,
                        help='Number of graded potential ports [default: %s]' % num_gpot)
    parser.add_argument('-m', '--max_steps', default=max_steps, type=int,
                        help='Maximum number of steps [default: %s]' % max_steps)
    args = parser.parse_args()

    file_name = None
    screen = False
    if args.log.lower() in ['file', 'both']:
        file_name = 'neurokernel.log'
    if args.log.lower() in ['screen', 'both']:
        screen = True
    logger = setup_logger(file_name=file_name, screen=screen, multiline=True)

    print emulate(args.num_lpus, args.num_spike, args.num_gpot, args.max_steps)
