from __future__ import annotations

from dataclasses import dataclass


class SmokeBudgetExceeded(RuntimeError):
    """Prevent an opt-in smoke run from sending more CAL transport attempts."""


@dataclass(slots=True)
class SmokeAttemptBudget:
    """Hard per-process cap counted just before an outbound CAL transport call."""

    max_attempts: int
    attempts: int = 0

    def __post_init__(self) -> None:
        if type(self.max_attempts) is not int:
            raise TypeError("smoke max_attempts must be an integer")
        if not 1 <= self.max_attempts <= 25:
            raise ValueError("smoke max_attempts must be between 1 and 25")

    def before_attempt(self) -> None:
        if self.attempts >= self.max_attempts:
            raise SmokeBudgetExceeded(
                f"CAL live smoke transport budget exhausted after {self.max_attempts} attempts"
            )
        self.attempts += 1
