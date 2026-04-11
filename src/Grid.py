from qiskit import QuantumCircuit, QAOAAnsatz, PauliOp

class Grid:

    def __init__(self, length: int, width: int, bushes: list[tuple[int, int]], budget: int):
        self.length = length
        self.width = width
        self.bushes = bushes
        self.budget = budget
        self.idx = dict()
        for i, bush in enumerate(bushes):
            self.idx[bush] = i # Map 2D grid coordinate -> 1D index
        self.edges = self.BuildEdges()
        pass

    def BuildEdges(self) -> list[tuple[int, int]]:
        edges = []
        for n, i in enumerate(self.bushes):
            for j in self.bushes[n+1:]:
                if (i[0] == j[0] and abs(i[1] - j[1]) == 1) or (i[1] == j[1] and abs(i[0] - j[0]) == 1):
                    edges.append((self.idx[i], self.idx[j]))
        return edges

    def BuildQAOALayer(self, gamma: float, beta: float) -> QuantumCircuit:
        """Build a single QAOA layer for the grid problem."""
        num_qubits = len(self.bushes)
        qc = QuantumCircuit(num_qubits)

        # Apply cost unitary for each edge
        for (i, j) in self.edges:
            qc.rzz(-2 * gamma, i, j)

        qc.barrier()
        
        # Apply mixer unitary for each qubit
        for i in range(0, num_qubits, 2):
            qc.rxx(-beta, i, (i + 1) % num_qubits) # Apply RXX between pairs of qubits (0-1, 2-3, ...)
            qc.ryy(-beta, i, (i + 1) % num_qubits) # Apply RYY between pairs of qubits (0-1, 2-3, ...)
        
        for i in range(1, num_qubits, 2):
            qc.rxx(-beta, i, (i + 1) % num_qubits) # Apply RXX between pairs of qubits (1-2, 3-4, ...)
            qc.ryy(-beta, i, (i + 1) % num_qubits) # Apply RYY between pairs of qubits (1-2, 3-4, ...)
        
        return qc
    
    def BuildQuantumCircuit(self, gammas: list[float], betas: list[float]) -> QuantumCircuit:
        """Build the full QAOA circuit for the grid problem."""
        num_qubits = len(self.bushes)
        qc = QuantumCircuit(num_qubits)

        # Initialize in uniform superposition
        qc.x(range(self.budget))

        qc.barrier()

        # Add QAOA layers
        for gamma, beta in zip(gammas, betas):
            qc.compose(self.BuildQAOALayer(gamma, beta), inplace=True)
            qc.barrier()

        return qc
    
