### Top-level functionality of the scenic package as a script:
### load a scenario and generate scenes in an infinite loop.

import logging
import sys
import time
import argparse
import random
import importlib.metadata
from shutil import copy
import importlib
import os
import yaml

import scenic.syntax.translator as translator
import scenic.core.errors as errors
from scenic.core.simulators import SimulationCreationError

from .translate import scene_to_sdf
from .model_generator import generate_model


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def setup_logging(verbose: bool = False) -> None:
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG if verbose else logging.INFO)
    logging.getLogger('gzscenic').addHandler(log_to_stdout)


def setup_arg_parser():

    parser = argparse.ArgumentParser(prog='gzscenic', add_help=False,
                                     description='Sample from a Scenic scenario.')
    
    mainOptions = parser.add_argument_group('main options')
    mainOptions.add_argument('-s', '--seed', help='random seed', type=int)
    mainOptions.add_argument('--load', help='load a scenic file', type=str, default='')
    mainOptions.add_argument('--verbose', help='verbose logging',
                             action='store_true')
    mainOptions.add_argument('--noplt', action='store_true',
                            help='do not create plots for scenes')
    mainOptions.add_argument('-n', '--scenes-num', type=int,
                            help='maximum number of scenes to generate. unlimited by default')
    mainOptions.add_argument('-p', '--param', help='override a global parameter',
                             nargs=2, default=[], action='append', metavar=('PARAM', 'VALUE'))
    mainOptions.add_argument('-m', '--model', help='specify a Scenic world model', default=None)
    mainOptions.add_argument('--scenario', default=None,
                             help='name of scenario to run (if file contains multiple)')
    
    # Interactive rendering options
    intOptions = parser.add_argument_group('static scene diagramming options')
    intOptions.add_argument('-d', '--delay', type=float,
                            help='loop automatically with this delay (in seconds) '
                                 'instead of waiting for the user to close the diagram')
    intOptions.add_argument('-z', '--zoom', help='zoom expansion factor (default 1)',
                            type=float, default=1)
    
    # Debugging options
    debugOpts = parser.add_argument_group('Scenic debugging options')
    debugOpts.add_argument('--show-params', help='show values of global parameters',
                           action='store_true')
    debugOpts.add_argument('-b', '--full-backtrace', help='show full internal backtraces',
                           action='store_true')
    debugOpts.add_argument('--pdb', action='store_true',
                           help='enter interactive debugger on errors (implies "-b")')
    ver = importlib.metadata.version('scenic')
    debugOpts.add_argument('--version', action='version', version=f'Scenic {ver}',
                           help='print Scenic version information and exit')
    debugOpts.add_argument('--dump-initial-python', help='dump initial translated Python',
                           action='store_true')
    debugOpts.add_argument('--dump-ast', help='dump final AST', action='store_true')
    debugOpts.add_argument('--dump-python', help='dump Python equivalent of final AST',
                           action='store_true')
    debugOpts.add_argument('--no-pruning', help='disable pruning', action='store_true')
    
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help=argparse.SUPPRESS)
    
    # Positional arguments
    parser.add_argument('scenicFile', help='a Scenic file to run', metavar='ScenicFILE')
    parser.add_argument('input', help='path to input yaml file', type=str, metavar='inputFILE')
    parser.add_argument('outputPath', help='Path to the output directory')
    
    # Parse arguments and set up configuration
    return parser.parse_args()


def generateScene(scenario, args):
    startTime = time.time()
    verbosity = 3 if args.verbose else 1
    scene, iterations = errors.callBeginningScenicTrace(
        lambda: scenario.generate(verbosity=verbosity)
    )
    totalTime = time.time() - startTime
    logger.debug(f'  Generated scene in {iterations} iterations, {totalTime:.4g} seconds.')
    if args.show_params:
        for param, value in scene.params.items():
            logger.debug(f'    Parameter "{param}": {value}')
    return scene, iterations


def main():
    args = setup_arg_parser()
    setup_logging(args.verbose)

    delay = args.delay
    errors.showInternalBacktrace = args.full_backtrace
    if args.pdb:
        errors.postMortemDebugging = True
        errors.showInternalBacktrace = True
    translator.dumpTranslatedPython = args.dump_initial_python
    translator.dumpFinalAST = args.dump_ast
    translator.dumpASTPython = args.dump_python
    translator.verbosity = 3 if args.verbose else 1
    translator.usePruning = not args.no_pruning
    if args.seed is not None:
        logger.info(f'Using random seed = {args.seed}')
        random.seed(args.seed)

    if not args.load:
        spec = importlib.util.spec_from_file_location('model', 'gzscenic/base.scenic', loader=translator.ScenicLoader(os.path.abspath('gzscenic/base.scenic'), 'base.scenic'))
        module = importlib.util.module_from_spec(spec)
        sys.modules['gzscenic.model'] = module
        spec.loader.exec_module(module)

        with open(args.input, 'r') as f:
            input_objects = yaml.load(f)
        for obj in input_objects:
            print(generate_model(obj, os.path.dirname(args.input)))
    else:
        if args.load.rpartition('.')[-1] not in ['sc', 'scenic']:
            raise Exception('The file to be loaded needs to be .sc or .scenic')
        spec = importlib.util.spec_from_file_location('model', args.load, loader=translator.ScenicLoader(os.path.abspath(args.load), os.path.basename(args.load)))
        module = importlib.util.module_from_spec(spec)
        sys.modules['gzscenic.model'] = module
        spec.loader.exec_module(module)

    # Load scenario from file
    logger.info('Beginning scenario construction...')
    startTime = time.time()
    scenario = errors.callBeginningScenicTrace(
        lambda: translator.scenarioFromFile(args.scenicFile,
                                            params=dict(args.param),
                                            model=args.model,
                                            scenario=args.scenario)
    )
    totalTime = time.time() - startTime
    logger.info(f'Scenario constructed in {totalTime:.2f} seconds.')
    
    if args.noplt:
        import matplotlib.pyplot as plt
    success_count = 0
    while not args.scenes_num or success_count <= args.scenes_num:
        scene, _ = generateScene(scenario, args)
        if not args.noplt:
            if delay is None:
                scene.show(zoom=args.zoom)
            else:
                scene.show(zoom=args.zoom, block=False)
                plt.pause(delay)
                plt.clf()

        scene_to_sdf(scene, args.outputPath)

