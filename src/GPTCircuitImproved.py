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

        #"vertical" edges

        even_circuit = QuantumCircuit(num_qubits)
        odd_circuit = QuantumCircuit(num_qubits)

        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                
                if (i + j) % 2 == 0:
                    qcparody = even_circuit
                else:                    
                    qcparody = odd_circuit

                # map |00> -> |11>
                qcparody.x([idx(i, j), idx(i, j + 1)])

                # apply phase on |11> using ZZ interaction
                qcparody.cx(idx(i, j), idx(i, j + 1))
                qcparody.rz(2 * gamma_l, idx(i, j + 1))
                qcparody.cx(idx(i, j), idx(i, j + 1))

                # map back
                qcparody.x([idx(i, j), idx(i, j + 1)])
        
        qc.compose(even_circuit, inplace=True)
        qc.barrier()
        qc.compose(odd_circuit, inplace=True)
        qc.barrier()

        # "horizontal" edges
        even_circuit = QuantumCircuit(num_qubits)
        odd_circuit = QuantumCircuit(num_qubits)
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                
                if (i + j) % 2 == 0:
                    qcparody = even_circuit
                else:                    
                    qcparody = odd_circuit

                # map |00> -> |11>
                qcparody.x([idx(i, j), idx(i + 1, j)])

                # apply phase on |11> using ZZ interaction
                qcparody.cx(idx(i, j), idx(i + 1, j))
                qcparody.rz(2 * gamma_l, idx(i + 1, j))
                qcparody.cx(idx(i, j), idx(i + 1, j))

                # map back
                qcparody.x([idx(i, j), idx(i + 1, j)])
        
        qc.compose(even_circuit, inplace=True)
        qc.barrier()
        qc.compose(odd_circuit, inplace=True)
        qc.barrier()

        # -----------------------------------------------------
        # MIXER UNITARY (XY model)
        # U = exp(-i beta (XX + YY))
        #
        # Implemented via:
        #   exp(-i beta XX) = RXX(2β)
        #   exp(-i beta YY) = RYY(2β)
        # -----------------------------------------------------

        # vertical edges
        even_circuit = QuantumCircuit(num_qubits)
        odd_circuit = QuantumCircuit(num_qubits)

        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                
                if (i + j) % 2 == 0:
                    qcparody = even_circuit
                else:                    
                    qcparody = odd_circuit

                qcparody.append(RXXGate(2 * beta_l), [idx(i, j), idx(i, j + 1)])
                qcparody.append(RYYGate(2 * beta_l), [idx(i, j), idx(i, j + 1)])
        
        qc.compose(even_circuit, inplace=True)
        qc.barrier()
        qc.compose(odd_circuit, inplace=True)
        qc.barrier()

        # "horizontal" edges
        even_circuit = QuantumCircuit(num_qubits)
        odd_circuit = QuantumCircuit(num_qubits)
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                
                if (i + j) % 2 == 0:
                    qcparody = even_circuit
                else:                    
                    qcparody = odd_circuit

                qcparody.append(RXXGate(2 * beta_l), [idx(i, j), idx(i + 1, j)])
                qcparody.append(RYYGate(2 * beta_l), [idx(i, j), idx(i + 1, j)])

        qc.compose(even_circuit, inplace=True)
        qc.barrier()
        qc.compose(odd_circuit, inplace=True)
        qc.barrier()

    return qc