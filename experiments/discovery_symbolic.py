"""OTTT v0.2: bounded symbolic discovery without third-party dependencies.

Researcher gets only a measurement function, not the world's law.
Grammar: x, 1, addition, multiplication, division, composed to depth 3.
Fits y = a*f(x)+b and selects experiments by hypothesis disagreement.
"""
import math
import unittest
from dataclasses import dataclass


class World:
    def __init__(self, law):
        self._law = law

    def measure(self, x):
        if not 0.5 <= x <= 20:
            raise ValueError("x out of range")
        return self._law(x)


@dataclass(frozen=True)
class Expression:
    name: str
    fn: object
    complexity: int


def grammar():
    x = Expression("x", lambda t: t, 1)
    one = Expression("1", lambda t: 1.0, 1)
    nodes = [x, one]
    for _ in range(3):
        additions = []
        pool = sorted(nodes, key=lambda e: (e.complexity, len(e.name)))[:50]
        for a in pool:
            for b in (x, one):
                additions.extend([
                    Expression(f"({a.name}+{b.name})", lambda t, a=a, b=b: a.fn(t)+b.fn(t), a.complexity+b.complexity+1),
                    Expression(f"({a.name}*{b.name})", lambda t, a=a, b=b: a.fn(t)*b.fn(t), a.complexity+b.complexity+1),
                    Expression(f"({a.name}/{b.name})", lambda t, a=a, b=b: a.fn(t)/b.fn(t), a.complexity+b.complexity+1),
                    Expression(f"({b.name}/{a.name})", lambda t, a=a, b=b: b.fn(t)/a.fn(t), a.complexity+b.complexity+1),
                ])
        seen = {}
        for e in nodes + additions:
            try:
                sig = tuple(round(e.fn(t), 9) for t in (0.73, 1.31, 2.71, 5.13))
                if not all(math.isfinite(z) and abs(z) < 1e9 for z in sig):
                    continue
            except (ZeroDivisionError, OverflowError, ValueError):
                continue
            if sig not in seen or e.complexity < seen[sig].complexity:
                seen[sig] = e
        nodes = sorted(seen.values(), key=lambda e: (e.complexity, len(e.name)))[:250]
    return nodes


class Researcher:
    def __init__(self, measure):
        self.measure = measure
        self.data = []
        self.features = grammar()

    def observe(self, x):
        self.data.append((x, float(self.measure(x))))

    def hypotheses(self):
        ys = [y for _, y in self.data]
        mean_y = sum(ys)/len(ys)
        scale = max(1.0, max(abs(y) for y in ys))
        candidates = []
        for e in self.features:
            try:
                fs = [e.fn(x) for x, _ in self.data]
                if not all(math.isfinite(z) for z in fs):
                    continue
                mf = sum(fs)/len(fs)
                var = sum((z-mf)**2 for z in fs)
                if var < 1e-15:
                    continue
                a = sum((z-mf)*(y-mean_y) for z, y in zip(fs, ys))/var
                b = mean_y-a*mf
                mse = sum((a*z+b-y)**2 for z, y in zip(fs, ys))/len(ys)/scale**2
                candidates.append((mse + 1e-12*e.complexity, mse, e, a, b))
            except (OverflowError, ZeroDivisionError, ValueError):
                continue
        return sorted(candidates, key=lambda v: v[0])

    def choose_experiment(self):
        top = self.hypotheses()[:12]
        used = {x for x, _ in self.data}
        choices = [x for x in (0.5, 0.7, 0.9, 1.3, 1.7, 2, 2.7, 3.5, 5, 7, 9, 13, 17, 20) if x not in used]

        def spread(x):
            try:
                values = [a*e.fn(x)+b for _, _, e, a, b in top]
                if not all(math.isfinite(z) for z in values):
                    return -1
                return max(values)-min(values)
            except (ZeroDivisionError, OverflowError):
                return -1
        return max(choices, key=spread)

    def discover(self):
        for x in (1.0, 2.0, 4.0, 8.0):
            self.observe(x)
        for _ in range(4):
            self.observe(self.choose_experiment())
        _, mse, expr, a, b = self.hypotheses()[0]
        return expr, a, b, mse


LAWS = [
    ("inverse square", lambda x: 100/x**2),
    ("quadratic plus constant", lambda x: 3*x*x+7),
    ("rational", lambda x: 12/(x+1)),
]


def demo():
    for label, law in LAWS:
        r = Researcher(World(law).measure)
        expr, a, b, mse = r.discover()
        holdout = [1.25, 3.25, 11.5]
        error = max(abs(a*expr.fn(x)+b-law(x)) for x in holdout)
        print(f"{label}: y={a:.6g}*{expr.name}+({b:.6g}); train MSE={mse:.3g}; holdout max error={error:.3g}")


class Tests(unittest.TestCase):
    def test_laws(self):
        for label, law in LAWS:
            with self.subTest(label=label):
                r = Researcher(World(law).measure)
                e, a, b, _ = r.discover()
                self.assertLess(max(abs(a*e.fn(x)+b-law(x)) for x in (1.25, 3.25, 11.5)), 1e-6)


if __name__ == "__main__":
    demo()
    unittest.main(argv=["discovery_symbolic"], exit=False)
