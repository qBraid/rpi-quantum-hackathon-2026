from qiskit import QuantumCircuit
from qiskit.circuit.library import RXXGate, RYYGate


def GridQuantumCircuit(
    gamma: list[float],
    beta: list[float],
    max_active: int = 10,
    grid_size: tuple[int, int] = (10, 10)
) -> QuantumCircuit:
    """
    QAOA-style circuit for:
      - minimizing number of adjacent (0,0) pairs
      - subject to exactly k active (1-valued) nodes

    Model:
      Cost Hamiltonian: sum_{(i,j)} |00><00|  (penalize inactive adjacency)
      Mixer: XY Hamiltonian (XX + YY) to preserve Hamming weight
    """

    num_qubits = grid_size[0] * grid_size[1]
    qc = QuantumCircuit(num_qubits)

    # =========================================================
    # 1. INITIAL STATE: exactly k active qubits (|1>)
    # =========================================================
    # This seeds the algorithm in the correct Hamming-weight sector.
    qc.x(range(max_active))

    def idx(i, j):
        """Map 2D grid coordinate -> 1D index."""
        return i * grid_size[1] + j

    edges = []

    # Build grid edges (right + down neighbors only to avoid duplicates)
    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            if j + 1 < grid_size[1]:
                edges.append((idx(i, j), idx(i, j + 1)))
            if i + 1 < grid_size[0]:
                edges.append((idx(i, j), idx(i + 1, j)))

    # =========================================================
    # 2. QAOA LAYERS
    # =========================================================
    for gamma_l, beta_l in zip(gamma, beta):

        # -----------------------------------------------------
        # COST UNITARY
        # Implements phase on |00> states per edge:
        #
        # |00> = X|11>
        # so we:
        #   X -> apply ZZ phase on |11> -> X back
        # -----------------------------------------------------
        for (i, j) in edges:

            # map |00> -> |11>
            qc.x([i, j])

            # apply phase on |11> using ZZ interaction
            qc.cx(i, j)
            qc.rz(2 * gamma_l, j)
            qc.cx(i, j)

            # map back
            qc.x([i, j])

        qc.barrier()

        # -----------------------------------------------------
        # MIXER UNITARY (XY model)
        # U = exp(-i beta (XX + YY))
        #
        # Implemented via:
        #   exp(-i beta XX) = RXX(2β)
        #   exp(-i beta YY) = RYY(2β)
        # -----------------------------------------------------
        for (i, j) in edges:
            qc.append(RXXGate(2 * beta_l), [i, j])
            qc.append(RYYGate(2 * beta_l), [i, j])

        qc.barrier()

    return qc