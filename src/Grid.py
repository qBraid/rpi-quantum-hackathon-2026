from qiskit import QuantumCircuit
import matplotlib.pyplot as plt
import random

class Grid:

    def __init__(self, length: int, width: int, bushes: list[tuple[int, int]], budget: int):
        self.length = length
        self.width = width
        self.bushes = bushes
        self.budget = budget
        self.toyons = set()
        self.idx = dict()
        for i, bush in enumerate(bushes):
            self.idx[bush] = i # Map 2D grid coordinate -> 1D index
        self.edges = self.BuildEdges()
        self.degree_sequence = self.GetDegreeSequence()
        pass

    @classmethod
    def random(cls, length: int, width: int, num_bushes: int, budget: int):
        bushes = set()
        while len(bushes) < num_bushes:
            bush = (random.randint(0, length - 1), random.randint(0, width - 1))
            bushes.add(bush)
        return cls(length, width, list(bushes), budget)
    
    def implement_solution(self, solution: list[int]):
        """Given a binary solution vector, mark the corresponding bushes as occupied by toyons."""
        for i, val in enumerate(solution):
            if val == 1:
                bush = self.bushes[i]
                self.toyons.add(bush)
        pass
    
    def plot(self, show = True):
        fig, ax = plt.subplots()
        for bush in self.bushes:
            ax.fill_between([bush[1] - 0.5, bush[1] + 0.5], bush[0] - 0.5, bush[0] + 0.5, color='red' if bush in self.toyons else 'green', alpha=0.5) # Note: (x, y) = (col, row)
        ax.set_xlim(-0.5, self.width - 0.5)
        ax.set_ylim(-0.5, self.length - 0.5)
        ax.set_aspect('equal')
        plt.axis('off')
        plt.gca().invert_yaxis() # Invert y-axis to match grid coordinates
        if show:
            plt.show()
        pass

    def BuildEdges(self) -> list[tuple[int, int]]:
        edges = []
        for n, i in enumerate(self.bushes):
            for j in self.bushes[n+1:]:
                if (i[0] == j[0] and abs(i[1] - j[1]) == 1) or (i[1] == j[1] and abs(i[0] - j[0]) == 1):
                    edges.append((self.idx[i], self.idx[j]))
        return edges
    
    def GetDegreeSequence(self) -> list[int]:
        degree_sequence = [0] * len(self.bushes)
        for (i, j) in self.edges:
            degree_sequence[i] += 1
            degree_sequence[j] += 1
        return degree_sequence

    def BuildQAOALayer(self, gamma: float, beta: float) -> QuantumCircuit:
        """Build a single QAOA layer for the grid problem."""
        num_qubits = len(self.bushes)
        qc = QuantumCircuit(num_qubits)

        # rz gates
        for i in range(num_qubits):
            degree = self.degree_sequence[i]
            if degree > 0:
                qc.rz(-gamma * degree, i) # Apply RZ with angle proportional to degree of vertex
        
        qc.barrier()

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
    
