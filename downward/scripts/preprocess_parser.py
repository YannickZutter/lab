#! /usr/bin/env python
"""
Regular expressions and functions for parsing preprocessing results.
"""

from __future__ import division

import logging
import re
import os
import sys

# The lab directory is added automatically in the Experiment constructor
from lab.parser import Parser


def check(props):
    if props.get('translate_error') == 1:
        msg = 'Translator error without preprocessor error'
        assert props.get('preprocess_error') == 1, msg

    if props.get('cost') is not None:
        assert props.get('search_time') is not None


# Preprocessing functions -----------------------------------------------------


def parse_translator_timestamps(content, props):
    """Parse all translator output of the following forms:

        Computing fact groups: [0.000s CPU, 0.004s wall-clock]
        Writing output... [0.000s CPU, 0.001s wall-clock]
    """
    pattern = re.compile(r'^(.+)(\.\.\.|:) \[(.+)s CPU, .+s wall-clock\]$')
    for line in content.splitlines():
        if line.startswith('Done!'):
            break
        match = pattern.match(line)
        if match:
            section = match.group(1).lower().replace(' ', '_')
            props['translator_time_' + section] = float(match.group(3))


def _get_var_descriptions(content):
    """Returns a list of (var_name, domain_size, axiom_layer) tuples."""
    regex = re.compile(r'begin_variables\n\d+\n(.+)end_variables', re.M | re.S)
    match = regex.search(content)
    if not match:
        return []
    # var_descriptions looks like ['var0 7 -1', 'var1 4 -1', 'var2 4 -1']
    var_descriptions = [var.split() for var in match.group(1).splitlines()]
    return [(name, int(size), int(layer))
            for name, size, layer in var_descriptions]


def _get_derived_vars(content):
    """Count those variables that have an axiom_layer >= 0."""
    var_descriptions = _get_var_descriptions(content)
    if not var_descriptions:
        logging.error('Number of derived vars could not be found')
        return None
    return len([name for name, size, layer in var_descriptions if layer >= 0])


def translator_derived_vars(content, props):
    if 'translator_derived_variables' not in props:
        props['translator_derived_variables'] = _get_derived_vars(content)


def preprocessor_derived_vars(content, props):
    if 'preprocessor_derived_variables' not in props:
        props['preprocessor_derived_variables'] = _get_derived_vars(content)


def _get_facts(content):
    var_descriptions = _get_var_descriptions(content)
    if not var_descriptions:
        logging.error('Number of facts could not be found')
        return None
    return sum(size for name, size, layer in var_descriptions)


def translator_facts(content, props):
    if not 'translator_facts' in props:
        props['translator_facts'] = _get_facts(content)


def preprocessor_facts(content, props):
    if not 'preprocessor_facts' in props:
        props['preprocessor_facts'] = _get_facts(content)


def translator_mutex_groups(content, props):
    if 'translator_mutex_groups' in props:
        return
    # Number of mutex groups (second line in the "all.groups" file).
    # The file normally starts with "begin_groups\n7\ngroup", but if no groups
    # are found, it has the form "begin_groups\n0\nend_groups".
    match = re.search(r'begin_groups\n(\d+)$', content, re.M | re.S)
    if match:
        props['translator_mutex_groups'] = int(match.group(1))


def translator_mutex_groups_total_size(content, props):
    """
    Total mutex group sizes after translating
    (sum over all numbers that follow a "group" line in the "all.groups" file)
    """
    if 'translator_total_mutex_groups_size' in props:
        return
    groups = re.findall(r'group\n(\d+)', content, re.M | re.S)
    props['translator_total_mutex_groups_size'] = sum(map(int, groups))

# -----------------------------------------------------------------------------


class PreprocessParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_preprocess_parsing()
        self.add_preprocess_functions()
        # Only try to parse all.groups file if it exists.
        if os.path.exists('all.groups'):
            self.add_mutex_groups_functions()

    def add_preprocess_parsing(self):
        """Add some preprocess specific parsing"""

        # TODO: Set required to True
        #parser.add_pattern('translate_error', r'translate_error = (\d)',
        #                 file='preprocess-properties', type=int, required=False)
        #parser.add_pattern('preprocess_error', r'preprocess_error = (\d)',
        #                 file='preprocess-properties', type=int, required=False)

        # Parse the preprocessor output. We need to parse the translator values
        # from the preprocessor output for older revisions. In newer revisions the
        # values are overwritten by values from the translator output.
        # The preprocessor log looks like:
        # 19 variables of 19 necessary
        # 2384 of 2384 operators necessary.
        # 0 of 0 axiom rules necessary.
        self.add_multipattern([(1, 'preprocessor_variables', int),
                              (2, 'translator_variables', int)],
                              r'(\d+) variables of (\d+) necessary')
        self.add_multipattern([(1, 'preprocessor_operators', int),
                               (2, 'translator_operators', int)],
                               r'(\d+) of (\d+) operators necessary')
        self.add_multipattern([(1, 'preprocessor_axioms', int),
                               (2, 'translator_axioms', int)],
                               r'(\d+) of (\d+) axiom rules necessary')

        # Parse the numbers from the following lines of translator output:
        #    170 relevant atoms
        #    141 auxiliary atoms
        #    311 final queue length
        #    364 total queue pushes
        #    13 uncovered facts
        #    0 implied effects removed
        #    0 effect conditions simplified
        #    0 implied preconditions added
        #    0 operators removed
        #    38 propositions removed
        for value in ['relevant atoms', 'auxiliary atoms', 'final queue length',
                'total queue pushes', 'uncovered facts', 'implied effects removed',
                'effect conditions simplified', 'implied preconditions added',
                'operators removed', 'propositions removed']:
            attribute = 'translator_' + value.lower().replace(' ', '_')
            # Those lines are not required, because they were not always printed
            self.add_pattern(attribute, r'(.+) %s' % value, type=int,
                             required=False)

        # Parse the numbers from the following lines of translator output:
        #   Translator variables: 7
        #   Translator derived variables: 0
        #   Translator facts: 24
        #   Translator mutex groups: 7
        #   Translator total mutex groups size: 28
        #   Translator operators: 34
        #   Translator task size: 217
        for value in ['variables', 'derived variables', 'facts', 'mutex groups',
                      'total mutex groups size', 'operators', 'task size']:
            attribute = 'translator_' + value.lower().replace(' ', '_')
            # Those lines are not required, because they were not always printed
            self.add_pattern(attribute, r'Translator %s: (.+)' % value, type=int,
                             required=False)

        # Parse the numbers from the following lines of preprocessor output:
        #   Preprocessor facts: 24
        #   Preprocessor derived variables: 0
        #   Preprocessor task size: 217
        for value in ['facts', 'derived variables', 'task size']:
            attribute = 'preprocessor_' + value.lower().replace(' ', '_')
            # Those lines are not required, because they were not always printed
            self.add_pattern(attribute, r'Preprocessor %s: (.+)' % value, type=int,
                             required=False)

    def add_preprocess_functions(self):
        self.add_function(parse_translator_timestamps)

        # Those functions will only parse the output files if we haven't found the
        # values in the log.
        self.add_function(translator_facts, file='output.sas')
        self.add_function(preprocessor_facts, file='output')
        self.add_function(translator_derived_vars, file='output.sas')
        self.add_function(preprocessor_derived_vars, file='output')

    def add_mutex_groups_functions(self):
        # Those functions will only parse the output files if we haven't found the
        # values in the log.
        self.add_function(translator_mutex_groups, file='all.groups')
        self.add_function(translator_mutex_groups_total_size, file='all.groups')


if __name__ == '__main__':
    parser = PreprocessParser()
    parser.parse()