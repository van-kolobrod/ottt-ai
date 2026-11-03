"""OTTT discovery v0.1: standalone black-box scientific-discovery baseline.

Run: python experiments/discovery.py
No third-party dependencies. Researcher is given a callable measurement
interface, never the hidden law. Hypothesis space is deliberately limited
to y=a*x**p with integer p from -4 to 4.
"""
import math
import random
import unittest


class World:
    def __init__(self, coefficient=100.0, exponent=-2.0, noise=0.0, seed=17):
        self._coefficient = coefficient
        self._exponent = exponent
        self._noise = noise
        self._rng = random.Random(seed)

    def measure(self, distance):
        if not 0.5 <= distance <= 20:
            raise ValueError("distance must be in [0.5,20]")
        y = self._coefficient * distance ** self._exponent
        return y * (1 + self._rng.gauss(0, self._noise))


class Researcher:
    def __init__(self, measure):
        self.measure = measure
        self.observations = []

    def observe(self, x):
        y = self.measure(x)
        if y <= 0:
            raise ValueError("positive measurements required")
        self.observations.append((x, y))
        return y

    def hypotheses(self):
        if len(self.observations) < 2:
            raise ValueError("at least two observations required")
        results = []
        for p in range(-4, 5):
            log_a = sum(math.log(y) - p * math.log(x)
                        for x, y in self.observations) / len(self.observations)
            a = math.exp(log_a)
            error = sum((math.log(y) - log_a - p * math.log(x)) ** 2
                        for x, y in self.observations) / len(self.observations)
            results.append((error, a, p))
        return sorted(results)

    def choose_experiment(self):
        best, alternative = self.hypotheses()[:2]
        candidates = [0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 20]
        used = {x for x, _ in self.observations}
        available = [x for x in candidates if x not in used]
        if not available:
            raise ValueError("candidate pool exhausted")
        def disagreement(x):
            _, a1, p1 = best
            _, a2, p2 = alternative
            return abs(math.log((a1 * x ** p1) / (a2 * x ** p2)))
        return max(available, key=disagreement)

    def discover(self, rounds=4):
        for x in (1.0, 2.0):
            self.observe(x)
        for _ in range(rounds):
            self.observe(self.choose_experiment())
        error, coefficient, exponent = self.hypotheses()[0]
        return {"coefficient": coefficient, "exponent": exponent,
                "log_mse": error, "observations": self.observations}


def demo():
    world = World()
    researcher = Researcher(world.measure)
    result = researcher.discover()
    print("Discovered: y = {:.6g} * x^{}".format(
        result["coefficient"], result["exponent"]))
    for x, y in result["observations"]:
        print("  x={:5g}  measured={:.8g}".format(x, y))
    holdout = [1.25, 5, 9]
    errors = [abs(result["coefficient"] * x ** result["exponent"]
                  / world.measure(x) - 1) for x in holdout]
    print("Holdout mean relative error:", sum(errors) / len(errors))


class Tests(unittest.TestCase):
    def test_inverse_square(self):
        result = Researcher(World(100, -2).measure).discover()
        self.assertEqual(result["exponent"], -2)
        self.assertAlmostEqual(result["coefficient"], 100)

    def test_unseen_power(self):
        result = Researcher(World(7, 3).measure).discover()
        self.assertEqual(result["exponent"], 3)
        self.assertAlmostEqual(result["coefficient"], 7)


if __name__ == "__main__":
    demo()
    unittest.main(argv=["discovery"], exit=False)
