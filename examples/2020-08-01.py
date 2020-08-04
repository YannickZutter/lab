#! /usr/bin/env python

import os
import os.path
import platform

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport
from lab import cached_revision
from lab.environments import BaselSlurmEnvironment, LocalEnvironment


ATTRIBUTES = ["coverage", "error", "expansions", "total_time", "expansions_until_last_jump", "search_time",  "cost", "run_dir"]

NODE = platform.node()
if NODE.endswith(".scicore.unibas.ch") or NODE.endswith(".cluster.bc2.ch"):
    # Create bigger suites with suites.py from the downward-benchmarks repo.
    SUITE = ["freecell", "gripper", "zenotravel"]
    ENV = BaselSlurmEnvironment(email="yannick.zutter@stud.unibas.ch")
    REPO = os.path.expanduser("~/fast-downward")
else:
    SUITE = ["depot:p01.pddl", "gripper:prob01.pddl", "depot:p02.pddl", "gripper:prob02.pddl", "gripper:prob02.pddl",
             "zenotravel:p01.pddl", "zenotravel:p02.pddl", "freecell:p01.pddl", "freecell:p02.pddl", "freecell:p03.pddl"]
    ENV = LocalEnvironment(processes=2)
    REPO = os.path.expanduser("~/CLionProjects/fast-downward")
# Use path to your Fast Downward repository.
BENCHMARKS_DIR = os.path.expanduser("~/benchmarks")
# If REVISION_CACHE is None, the default ./data/revision-cache is used.
REVISION_CACHE = os.environ.get("DOWNWARD_REVISION_CACHE")
VCS = cached_revision.get_version_control_system(REPO)
REV = "78cf72605672b5debed7bd09f31271984ff20e7b"

exp = FastDownwardExperiment(environment=ENV, revision_cache=REVISION_CACHE)

# Add built-in parsers to the experiment.
exp.add_parser(exp.EXITCODE_PARSER)
exp.add_parser(exp.TRANSLATOR_PARSER)
exp.add_parser(exp.SINGLE_SEARCH_PARSER)
exp.add_parser(exp.PLANNER_PARSER)
exp.add_parser("ff/ff-parser.py")
exp.add_parser("sg-parser.py")

exp.add_suite(BENCHMARKS_DIR, SUITE)
exp.add_algorithm("default", REPO, REV, ["--search", "astar(blind(), sg = default)"])
exp.add_algorithm("naive", REPO, REV, ["--search", "astar(blind(), sg = naive)"])
exp.add_algorithm("marked", REPO, REV, ["--search", "astar(blind(), sg = marked)"])
exp.add_algorithm("timestamps", REPO, REV, ["--search", "astar(blind(), sg = timestamps)"])

# Add step that writes experiment files to disk.
exp.add_step("build", exp.build)

# Add step that executes all runs.
exp.add_step("start", exp.start_runs)

# Add step that collects properties from run directories and
# writes them to *-eval/properties.
exp.add_fetcher(name="fetch")

# Add report step (AbsoluteReport is the standard report).
exp.add_report(AbsoluteReport(attributes=ATTRIBUTES), outfile="report.html")

# Add scatter plot report step.
exp.add_report(
    ScatterPlotReport(attributes=["expansions"], filter_algorithm=["blind", "lmcut"]),
    outfile="scatterplot.png",
)

# Parse the commandline and show or run experiment steps.
exp.run_steps()
