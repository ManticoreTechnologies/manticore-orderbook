#!/usr/bin/env python3
"""
Runs all tests for the Manticore OrderBook.

This script discovers and runs all tests in the tests directory,
including unit tests, integration tests, and performance tests.
"""

import unittest
import argparse
import sys
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_runner')

def discover_and_run_tests(test_type=None, verbose=False, failfast=False):
    """
    Discover and run tests of the specified type.
    
    Args:
        test_type: The type of tests to run ('unit', 'integration', 'all')
        verbose: Whether to show verbose output
        failfast: Whether to stop on first failure
    
    Returns:
        The test result object
    """
    # Set verbosity level
    verbosity = 2 if verbose else 1
    
    # Create test loader
    loader = unittest.TestLoader()
    
    # Determine test directory
    if test_type == 'unit':
        start_dir = os.path.join(os.path.dirname(__file__), 'unit')
        logger.info("Running unit tests...")
    elif test_type == 'integration':
        start_dir = os.path.join(os.path.dirname(__file__), 'integration')
        logger.info("Running integration tests...")
    else:  # All tests
        start_dir = os.path.dirname(__file__)
        logger.info("Running all tests...")
    
    # Discover tests
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast)
    
    # Run tests and return the result
    return runner.run(suite)

def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run Manticore OrderBook tests')
    parser.add_argument('--type', choices=['unit', 'integration', 'all'], 
                        default='all', help='Type of tests to run')
    parser.add_argument('--verbose', action='store_true', help='Show verbose output')
    parser.add_argument('--failfast', action='store_true', help='Stop on first failure')
    
    args = parser.parse_args()
    
    logger.info("Starting test run at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    result = discover_and_run_tests(args.type, args.verbose, args.failfast)
    
    logger.info("Finished test run at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("Tests run: %d", result.testsRun)
    logger.info("Failures: %d", len(result.failures))
    logger.info("Errors: %d", len(result.errors))
    logger.info("Skipped: %d", len(result.skipped))
    
    # Return appropriate exit code (0 for success, 1 for failure)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main()) 