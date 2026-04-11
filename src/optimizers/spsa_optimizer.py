from dataclasses import dataclass
from typing import Any

import numpy as np

from .base import ObjectiveFn, Optimizer, OptimizerResult


@dataclass(frozen=True)
class SpsaOptimizer(Optimizer):
    maxiter: int
    learning_rate: float
    perturbation: float
    alpha: float
    gamma: float
    seed: int

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        parser.add_argument(
            "--spsa-maxiter",
            type=int,
            default=20,
            help="Maximum SPSA objective-evaluation budget.",
        )
        parser.add_argument(
            "--spsa-learning-rate",
            type=float,
            default=0.2,
            help="Base SPSA learning rate (a).",
        )
        parser.add_argument(
            "--spsa-perturbation",
            type=float,
            default=0.1,
            help="Base SPSA perturbation scale (c).",
        )
        parser.add_argument(
            "--spsa-alpha",
            type=float,
            default=0.602,
            help="SPSA learning-rate decay exponent.",
        )
        parser.add_argument(
            "--spsa-gamma",
            type=float,
            default=0.101,
            help="SPSA perturbation decay exponent.",
        )

    @classmethod
    def from_namespace(cls, args) -> "SpsaOptimizer":
        seed = getattr(args, "wildfire_seed", None)
        if seed is None:
            seed = getattr(args, "seed", 42)
        return cls(
            maxiter=int(args.spsa_maxiter),
            learning_rate=float(args.spsa_learning_rate),
            perturbation=float(args.spsa_perturbation),
            alpha=float(args.spsa_alpha),
            gamma=float(args.spsa_gamma),
            seed=int(seed),
        )

    @property
    def label(self) -> str:
        return "spsa"

    @property
    def options(self) -> dict[str, Any]:
        return {
            "maxiter": self.maxiter,
            "learning_rate": self.learning_rate,
            "perturbation": self.perturbation,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "seed": self.seed,
        }

    def planned_evaluations(self, *, num_parameters: int) -> int | None:
        _ = num_parameters
        return max(1, self.maxiter)

    def optimize(self, objective: ObjectiveFn, initial_params: np.ndarray) -> OptimizerResult:
        x = np.asarray(initial_params, dtype=float).copy()
        rng = np.random.default_rng(self.seed)
        budget = max(1, self.maxiter)

        best_x = x.copy()
        best_fun = float("inf")
        history: list[float] = []
        nfev = 0
        nit = 0

        while nfev + 2 <= budget:
            k = nit
            ak = self.learning_rate / ((k + 1) ** self.alpha)
            ck = self.perturbation / ((k + 1) ** self.gamma)
            delta = rng.choice(np.array([-1.0, 1.0], dtype=float), size=x.shape)

            x_plus = x + ck * delta
            x_minus = x - ck * delta

            y_plus = float(objective(x_plus))
            y_minus = float(objective(x_minus))
            history.extend([y_plus, y_minus])
            nfev += 2

            ghat = (y_plus - y_minus) / (2.0 * ck) * (1.0 / delta)
            x = x - ak * ghat

            y_center = 0.5 * (y_plus + y_minus)
            if y_center < best_fun:
                best_fun = y_center
                best_x = x.copy()
            nit += 1

        if nfev < budget:
            # Use any leftover single evaluation without exceeding the hard budget.
            y_current = float(objective(x))
            history.append(y_current)
            nfev += 1
            if y_current < best_fun:
                best_fun = y_current
                best_x = x.copy()

        raw_result = {
            "method": "SPSA",
            "nit": nit,
            "nfev": nfev,
            "history": history,
            "options": self.options,
        }
        return OptimizerResult(
            x=np.asarray(best_x, dtype=float),
            fun=float(best_fun),
            raw_result=raw_result,
        )


