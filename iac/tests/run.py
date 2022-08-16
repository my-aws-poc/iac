import os
import unittest


def all_case():
    case_dir = os.getcwd()
    discover = unittest.defaultTestLoader.discover(case_dir, pattern="test_*.py")
    print(case_dir)
    return discover


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(all_case())
