"""Include the isolated simulation's behavioral tests in normal host CI."""
from tools.research.adaptive_tree import test_engine


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(test_engine)
