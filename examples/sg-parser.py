#! /usr/bin/env python

from lab.parser import Parser
import re

def limit(content, props):
    props["sg_iteration_limit_reached"] = re.findall("reached maximum number of successor generation iterations! Aborting now...", content, re.M)



parser = Parser()
parser.add_pattern("avg_dur_gao", r"average duration of get_applicable_ops calls: (.+)\n", type=float)
parser.add_pattern("num_gao", r"number of get_applicable_ops calls: (.+)\n", type=int)
parser.add_pattern("tot_dur_gao", r"total duration of get_applicable_ops calls: (.+)\n", type=float)
parser.add_pattern("sg_intitialization_time", r"time to initialize successor generator: (.+)s\n", type=float)
parser.add_function(limit)


parser.parse()
