from dataclasses import dataclass
from typing import Any, Callable, cast

import numpy as np
from scipy.optimize import minimize

from .base import ObjectiveFn, Optimizer, OptimizerResult


@dataclass(frozen=True)
class ScipyOptimizer(Optimizer):
    method: str
    maxiter: int
    adaptive: bool

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        parser.add_argument(
            "--optimizer",
            choices=("cobyla", "nelder-mead", "powell"),
            default="nelder-mead",
            help="Optimizer used to tune ansatz parameters.",
        )
        parser.add_argument(
            "--optimizer-maxiter",
            type=int,
            default=20,
            help="Maximum optimizer iterations/evaluations budget.",
        )
        parser.add_argument(
            "--optimizer-adaptive",
            action="store_true",
            help="Enable adaptive Nelder-Mead behavior when applicable.",
        )

    @classmethod
    def from_namespace(cls, args) -> "ScipyOptimizer":
        return cls(
            method=str(args.optimizer),
            maxiter=int(args.optimizer_maxiter),
            adaptive=bool(args.optimizer_adaptive),
        )

    @property
    def label(self) -> str:
        return f"scipy:{self.method}"

    @property
    def options(self) -> dict[str, Any]:
        budget = self.maxiter
        if self.method == "nelder-mead":
            return {"maxiter": budget, "maxfev": budget, "adaptive": self.adaptive}
        if self.method == "powell":
            return {"maxiter": budget, "maxfev": budget}
        return {"maxiter": budget}

    def planned_evaluations(self, *, num_parameters: int) -> int | None:
        _ = num_parameters
        return max(1, self.maxiter)

    def optimize(self, objective: ObjectiveFn, initial_params: np.ndarray) -> OptimizerResult:
        method_map = {
            "cobyla": "COBYLA",
            "nelder-mead": "Nelder-Mead",
            "powell": "Powell",
        }
        scipy_method = method_map[self.method]
        budget = max(1, self.maxiter)

        options: dict[str, Any]
        if scipy_method == "Nelder-Mead":
            options = {"maxiter": budget, "maxfev": budget, "adaptive": self.adaptive}
        elif scipy_method == "Powell":
            options = {"maxiter": budget, "maxfev": budget}
        else:
            options = {"maxiter": budget}

        minimize_fn: Callable[..., Any] = cast(Any, minimize)
        result = minimize_fn(
            fun=cast(Any, objective),
            x0=cast(Any, np.asarray(initial_params, dtype=float)),
            method=scipy_method,
            options=options,
        )
        x = np.asarray(result.x, dtype=float)
        fun = float(result.fun)
        return OptimizerResult(x=x, fun=fun, raw_result=result)

