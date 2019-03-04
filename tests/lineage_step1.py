#!/usr/bin/env python3
"""Example command for lineage test
"""
import sys
import argparse
import os
from os.path import abspath, expanduser, join, exists
import random
import datetime

from dataworkspaces.lineage import make_lineage, CmdLineParameter,\
    add_lineage_parameters_to_arg_parser, get_lineage_parameter_values,\
    ResourceRef

PARAMS = [
    CmdLineParameter(name='size', default=50, type=int,
                     help="the size")
]

BASE_DIR=abspath(expanduser(".")) # run from within workspace

def main(argv=sys.argv[1:]):
    print("Running step1")
    parser = argparse.ArgumentParser("Lineage step 1")
    parser.add_argument('--fail', action='store_true', default=False,
                        help="If specified, fail the step")
    add_lineage_parameters_to_arg_parser(parser, PARAMS)
    parser.add_argument('test_case', metavar='TEST_CASE')
    args = parser.parse_args(argv)
    with make_lineage(get_lineage_parameter_values(PARAMS,args),
                      [ResourceRef('source-data')]) as lineage:
          lineage.add_output_path(join(BASE_DIR, 'intermediate-data/s1'))
          if args.fail:
              raise Exception("Failing this step")
          else:
              immediate_dir = join(BASE_DIR, 'intermediate-data/s1')
              if not exists(immediate_dir):
                  os.mkdir(immediate_dir)
              with open(join(BASE_DIR, 'intermediate-data/s1/out.csv'), 'w') as f:
                  f.write('name,time,value\n')
                  f.write('r1,%s,%s\n' % (datetime.datetime.now().isoformat(),
                                          random.random()))
              with open(join(BASE_DIR, 'intermediate-data/s1/test_case.txt'), 'w') as f:
                  f.write(args.test_case)
    print("finished lineage step 1")
    return 0

if __name__=='__main__':
    sys.exit(main())
