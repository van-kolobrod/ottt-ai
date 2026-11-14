"""OTTT experiment: cross-domain transfer of a discovered relationship.

Run: python experiments/discovery_transfer.py
No dependencies. A researcher sees observations, not source equations.
Test: learn a relation in hydraulic domain; transfer its *shape* to an
electrical domain with renamed variables and a different coefficient.
"""
from dataclasses import dataclass
import math
import unittest


@dataclass(frozen=True)
class Observation:
    left: float
    right: float
    flow: float


class BlackBox:
    def __init__(self, coefficient, law):
        self._coefficient = coefficient
        self._law = law

    def measure(self, left, right):
        difference = left - right
        if self._law == "linear":
            flow = self._coefficient * difference
        elif self._law == "square":
            flow = self._coefficient * difference * abs(difference)
        else:
            raise ValueError("Unknown private world")
        return Observation(left, right, flow)


# These are structural candidate hypotheses, not hard-coded world equations.
# The researcher does not know which candidate governs which world.
CANDIDATES = {
    "difference": lambda a, b: a - b,
    "sum": lambda a, b: a + b,
    "absolute_difference": lambda a, b: abs(a - b),
    "signed_square_difference": lambda a, b: (a - b) * abs(a - b),
    "product": lambda a, b: a * b,
    "left": lambda a, b: a,
}


def fit(name, observations):
    feature = CANDIDATES[name]
    xs = [feature(o.left, o.right) for o in observations]
    ys = [o.flow for o in observations]
    denominator = sum(x*x for x in xs)
    if denominator < 1e-12:
        return math.inf, 0.0
    coefficient = sum(x*y for x, y in zip(xs, ys)) / denominator
    mse = sum((coefficient*x-y)**2 for x, y in zip(xs, ys))/len(xs)
    return mse, coefficient


class Researcher:
    def __init__(self):
        self.learned = None

    def discover(self, observations):
        ranked = sorted((fit(name, observations)[0], name)
                        for name in CANDIDATES)
        mse, name = ranked[0]
        self.learned = name
        return name, mse

    def transfer(self, observations):
        if self.learned is None:
            raise ValueError("Discover a source relation first")
        # Only the structure is transferred; target coefficient is fitted anew.
        mse, coefficient = fit(self.learned, observations)
        return self.learned, coefficient, mse

    def predict(self, name, coefficient, left, right):
        return coefficient * CANDIDATES[name](left, right)


def sample(world, pairs):
    return [world.measure(a, b) for a, b in pairs]


SOURCE_PAIRS = [(10, 2), (3, 7), (8, 8), (2, 1), (12, 5)]
TARGET_CALIBRATION = [(4, 1), (1, 5)]
TARGET_HOLDOUT = [(9, 3), (2, 8), (5, 5), (7, 2)]


def experiment(target_law="linear"):
    hydraulics = BlackBox(2.5, "linear")
    electricity = BlackBox(0.4, target_law)
    agent = Researcher()
    discovered, source_mse = agent.discover(sample(hydraulics, SOURCE_PAIRS))
    transferred, coefficient, calibration_mse = agent.transfer(
        sample(electricity, TARGET_CALIBRATION))
    errors = [abs(agent.predict(transferred, coefficient, a, b) -
                  electricity.measure(a, b).flow)
              for a, b in TARGET_HOLDOUT]
    return {"source_relation": discovered, "source_mse": source_mse,
            "target_relation": transferred, "target_coefficient": coefficient,
            "target_calibration_mse": calibration_mse,
            "target_holdout_max_error": max(errors)}


class Tests(unittest.TestCase):
    def test_transfer_to_new_domain(self):
        result = experiment()
        self.assertEqual(result["source_relation"], "difference")
        self.assertAlmostEqual(result["target_coefficient"], 0.4)
        self.assertLess(result["target_holdout_max_error"], 1e-10)

    def test_negative_control(self):
        # A different physical law must *not* be proclaimed transferable.
        result = experiment("square")
        self.assertGreater(result["target_holdout_max_error"], 1.0)

    def test_missing_source(self):
        with self.assertRaises(ValueError):
            Researcher().transfer([])


if __name__ == "__main__":
    print("Matching domains:", experiment())
    print("Different-law control:", experiment("square"))
    unittest.main(argv=["discovery_transfer"], exit=False)
