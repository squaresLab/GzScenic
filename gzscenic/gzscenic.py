### Top-level functionality of the scenic package as a script:
### load a scenario and generate scenes in an infinite loop.

import logging
import sys
import time
import argparse
import random
import importlib.metadata
from shutil import copy

import scenic.syntax.translator as translator
import scenic.core.errors as errors
from scenic.core.simulators import SimulationCreationError

from .translate import scene_to_sdf


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
    mainOptions.add_argument('--verbose', help='verbose logging',
                             action='store_true')
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
    debugOpts = parser.add_argument_group('debugging options')
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
    debugOpts.add_argument('--gather-stats', type=int, metavar='N',
                           help='collect timing statistics over this many scenes')
    
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help=argparse.SUPPRESS)
    
    # Positional arguments
    parser.add_argument('scenicFile', help='a Scenic file to run', metavar='FILE')
    
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
    
    if args.gather_stats is None:   # Generate scenes interactively until killed
        import matplotlib.pyplot as plt
        successCount = 0
        while True:
            scene, _ = generateScene(scenario, args)
            if delay is None:
                scene.show(zoom=args.zoom)
            else:
                scene.show(zoom=args.zoom, block=False)
                plt.pause(delay)
                plt.clf()
            workspace, model_files = scene_to_sdf(scene)
            workspace.write('out/Workspace.world')
            for filename in model_files:
                copy(filename, 'out/models/')
    else:   # Gather statistics over the specified number of scenes
        its = []
        startTime = time.time()
        while len(its) < args.gather_stats:
            scene, iterations = generateScene(scenario, args)
            its.append(iterations)
        totalTime = time.time() - startTime
        count = len(its)
        logger.info(f'Sampled {len(its)} scenes in {totalTime:.2f} seconds.')
        logger.info(f'Average iterations/scene: {sum(its)/count}')
        logger.info(f'Average time/scene: {totalTime/count:.2f} seconds.')

