#! /usr/bin/env python

from lab.parser import Parser

parser = Parser()
parser.add_pattern("avg_dur_gao", "average duration of get_applicable_ops calls: (.+)", type=float, file="driver.log", required=False)
parser.add_pattern("num_gao", "number of get_applicable_ops calls: (.+)", type=int, file="driver.log", required=False)
parser.add_pattern("tot_dur_gao", "total duration of get_applicable_ops calls: (:+)", type=float, file="driver.log", required=False)
