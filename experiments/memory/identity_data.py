"""Synthetic 5B worlds. Control identity is a sidecar, never a sensor feature."""
from dataclasses import dataclass
import random


VERSION = "identity_worlds_5b_v1"
SCENARIOS = ("movement", "resize", "reshape", "disappearance", "identical", "crossing", "replacement")


@dataclass(frozen=True)
class PublicFrame:
    signal: str
    occurred_at: str


@dataclass(frozen=True)
class LabeledSequence:
    seed: int
    scenario: str
    frames: tuple
    controls: tuple
    ambiguous_transitions: tuple


def generate(seed):
    rng = random.Random(seed)
    sequences = []
    for scenario in SCENARIOS:
        offset, row = rng.randint(1, 3), rng.randint(1, 2)
        first = f"control-{rng.getrandbits(96):024x}"
        second = f"control-{rng.getrandbits(96):024x}"
        step = rng.randint(1, 4)

        def pixels(x, shape=((0, 0),)):
            return [(x+dx, row+dy) for dx, dy in shape]

        ambiguous = ()
        if scenario == "movement":
            worlds = [{first: pixels(offset+i*step)} for i in range(3)]
        elif scenario == "resize":
            width = rng.choice((3, 4))
            worlds = [{first: pixels(offset)},
                      {first: pixels(offset+1, tuple((x, 0) for x in range(width)))},
                      {first: pixels(offset+2, tuple((x, 0) for x in range(width)))}]
        elif scenario == "reshape":
            horizontal = tuple((x, 0) for x in range(4))
            vertical = tuple((0, y) for y in range(4))
            worlds = [{first: pixels(offset, horizontal)},
                      {first: pixels(offset+1, vertical)}, {first: pixels(offset+2, vertical)}]
        elif scenario == "disappearance":
            worlds = [{first: pixels(offset)}, {}, {first: pixels(offset+2)}]
        elif scenario == "identical":
            worlds = [{first: pixels(offset+i), second: pixels(offset+12+i)} for i in range(3)]
        elif scenario == "crossing":
            worlds = [{first: pixels(offset), second: pixels(offset+2)},
                      {first: pixels(offset+2), second: pixels(offset)}]
            # Both exchange and staying still produce exactly the same visible frames.
            ambiguous = (1,)
        else:
            # Observationally similar to growth, but the old object was replaced.
            worlds = [{first: pixels(offset)},
                      {second: pixels(offset+1, tuple((x, 0) for x in range(4)))}]
        frames = []
        for index, world in enumerate(worlds):
            field = [["."]*24 for _ in range(7)]
            for cells in world.values():
                for x, y in cells:
                    if field[y][x] != ".":
                        raise ValueError("Synthetic objects overlap")
                    field[y][x] = "#"
            frames.append(PublicFrame("\n".join("".join(line) for line in field),
                                      f"2026-11-04T00:00:0{index}Z"))
        sequences.append(LabeledSequence(seed, scenario, tuple(frames), tuple(worlds), ambiguous))
    return sequences


def dataset_splits(training=(11, 23, 37), validation=(101, 103), test=(211, 223, 227)):
    all_seeds = list(training)+list(validation)+list(test)
    if len(set(all_seeds)) != len(all_seeds):
        raise ValueError("Training, validation and test seeds must not overlap")
    return {name: [sequence for seed in seeds for sequence in generate(seed)]
            for name, seeds in (("training", training), ("validation", validation), ("test", test))}
