#!/usr/bin/env python

from unittest import main, TestCase

from neurokernel.routing_table import RoutingTable

class test_routingtable(TestCase):
    def setUp(self):
        self.connections_orig = [('a', 'b'), ('b', 'c')]
        self.ids_orig = set([i[0] for i in self.connections_orig]+\
                            [i[1] for i in self.connections_orig])
        self.t = RoutingTable()
        for c in self.connections_orig:
            self.t[c[0], c[1]] = 1

    def test_ids(self):
        assert set(self.t.ids) == self.ids_orig

    def test_connections(self):
        assert set(self.t.connections) == set(self.connections_orig)

    def test_setitem(self):
        t = RoutingTable()
        t['a', 'b'] = 1
        assert t.data.has_node('a')
        assert t.data.has_node('b')
        assert t.data.has_edge('a', 'b')

    def test_getitem(self):
        t = RoutingTable()
        t.data.add_node('a')
        t.data.add_node('b')
        t.data.add_edge('a', 'b', {'data':1})
        assert t['a', 'b'] == 1

    def test_src_ids(self):
        for i in self.connections_orig:
            assert i[0] in self.t.src_ids(i[1])

    def test_dest_ids(self):
        for i in self.connections_orig:
            assert i[1] in self.t.dest_ids(i[0])

if __name__ == '__main__':
    main()
