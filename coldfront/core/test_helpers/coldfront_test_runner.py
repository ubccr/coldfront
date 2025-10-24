# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
from argparse import ArgumentTypeError
from enum import IntEnum

import factory
import factory.random
from django.test.runner import DiscoverRunner


class StressLevel(IntEnum):
    LOW = 8
    MEDIUM = 128
    HIGH = 1024
    EXTREME = 4096
    SEVERE = 32768

    default = LOW

    @classmethod
    def get_names(cls) -> list[str]:
        return [ele.name for ele in cls]

    @classmethod
    def from_string(cls, value: str):
        if value.upper() in cls.get_names():
            return cls[value.upper()]
        raise ValueError("Cannot convert value to StressLevel")


class ColdFrontRunner(DiscoverRunner):
    def __init__(self, stress_level=StressLevel.default, fake_seed=0, **kwargs):
        self.stress_level: StressLevel = stress_level
        self.fake_seed: float = fake_seed
        global STRESS_LEVEL
        global FAKE_SEED
        STRESS_LEVEL = self.stress_level
        FAKE_SEED = self.fake_seed
        super().__init__(**kwargs)

    def setup_test_environment(self, **kwargs):
        print(f"Using the seed {self.fake_seed} for test(s).")
        factory.random.reseed_random(self.fake_seed)
        if self.parallel > 1:
            print("NOTICE: Running test(s) in parallel may produce non-deterministic results.")
        super().setup_test_environment(**kwargs)

    @staticmethod
    def get_stress_level_from_arg(value: str):
        try:
            return StressLevel.from_string(value)
        except ValueError:
            raise ArgumentTypeError(
                f"Invalid value '{value}' cannot be converted to StressLevel. Use one of: {', '.join(StressLevel.get_names())}."
            )

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--stress-level",
            dest="stress_level",
            type=cls.get_stress_level_from_arg,
            default=StressLevel.default,
            help="Stress level to run the tests at. Higher levels take longer to run.",
        )
        parser.add_argument(
            "--fake-seed",
            dest="fake_seed",
            type=float,
            default=random.random(),
            help="Seed for the fake data generator.",
        )
        super().add_arguments(parser)


STRESS_LEVEL: StressLevel = StressLevel.default
FAKE_SEED: float = 0
