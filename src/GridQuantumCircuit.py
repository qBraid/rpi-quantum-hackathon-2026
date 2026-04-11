from qiskit import QuantumCircuit

def GridQuantumCircuit(gamma: list[float], 
                          beta: list[float], 
                          max_active: int = 10, 
                          grid_size: tuple[int, int]= (10, 10)
                          ) -> QuantumCircuit:
    """Constructs a quantum circuit for the Layer Optimized Quantum Approximate Optimization Algorithm (LO-QAOA) based on the provided parameters.

    Args:
        gamma (list[float]): A list of angles for the problem unitary layers.
        beta (list[float]): A list of angles for the mixer unitary layers.
        max_active (int, optional): The maximum number of active qubits in the circuit. Defaults to 10.
        grid_size (tuple[int, int], optional): The dimensions of the grid for the qubits. Defaults to (10, 10).

    """

    num_qubits = grid_size[0] * grid_size[1]
    qc = QuantumCircuit(num_qubits)
    qc.x(range(max_active)) # start in the state |1>^max_active |0>^(num_qubits - max_active)

    # (i, j) -> i * grid_size[1] + j

    # ==============================================
    # 26 layers per itteration (of gamma, beta)
    # ==============================================

    for gamma_i, beta_i in zip(gamma, beta):

        # "vertical" edges

        # each of these uses four layers (total of 8)
        vertical_odd = QuantumCircuit(num_qubits)
        vertical_even = QuantumCircuit(num_qubits)

        vertical_odd.rz(0-gamma_i, range(num_qubits))
        vertical_even.rz(0-gamma_i, range(num_qubits))

        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                # 3 layers
                if j % 2 == 0:
                    vertical_odd.cx(idx, idx + 1)
                    vertical_odd.rz(gamma_i, idx + 1)
                    vertical_odd.cx(idx, idx + 1)
                else:
                    vertical_even.cx(idx, idx + 1)
                    vertical_even.rz(gamma_i, idx + 1)
                    vertical_even.cx(idx, idx + 1)
    
        qc.compose(vertical_odd, inplace=True)
        qc.barrier()
        qc.compose(vertical_even, inplace=True)
        qc.barrier()

        # "horizontal" edges

        # each of these uses four layers (total of 8)
        horizontal_odd = QuantumCircuit(num_qubits)
        horizontal_even = QuantumCircuit(num_qubits)
        horizontal_odd.rz(0-gamma_i, range(num_qubits))
        horizontal_even.rz(0-gamma_i, range(num_qubits))
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                # 3 layers
                if i % 2 == 0:
                    horizontal_odd.cx(idx, idx + grid_size[1])
                    horizontal_odd.rz(gamma_i, idx + grid_size[1])
                    horizontal_odd.cx(idx, idx + grid_size[1])
                else:
                    horizontal_even.cx(idx, idx + grid_size[1])
                    horizontal_even.rz(gamma_i, idx + grid_size[1])
                    horizontal_even.cx(idx, idx + grid_size[1])

        qc.compose(horizontal_odd, inplace=True)
        qc.barrier()
        qc.compose(horizontal_even, inplace=True)
        qc.barrier()

        # mixer layer

        # one layer
        qc.h(range(num_qubits)) # H turns X into Z and Y into X, so we can implement the mixer with CNOTs and Rz rotations.

        # "vertical" edges

        # each of these uses three layers (total of 6)
        vertical_odd = QuantumCircuit(num_qubits)
        vertical_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                # 3 layers
                if j % 2 == 0:
                    vertical_odd.cx(idx, idx + 1)
                    vertical_odd.rz(2*beta_i, idx + 1)
                    vertical_odd.cx(idx, idx + 1)
                else:
                    vertical_even.cx(idx, idx + 1)
                    vertical_even.rz(2*beta_i, idx + 1)
                    vertical_even.cx(idx, idx + 1)
        
        qc.compose(vertical_odd, inplace=True)
        qc.barrier()
        qc.compose(vertical_even, inplace=True)
        qc.barrier()

        # "horizontal" edges

        # each of these uses three layers (total of 6)
        horizontal_odd = QuantumCircuit(num_qubits)
        horizontal_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                # 3 layers
                if i % 2 == 0:
                    horizontal_odd.cx(idx, idx + grid_size[1])
                    horizontal_odd.rz(2*beta_i, idx + grid_size[1])
                    horizontal_odd.cx(idx, idx + grid_size[1])
                else:
                    horizontal_even.cx(idx, idx + grid_size[1])
                    horizontal_even.rz(2*beta_i, idx + grid_size[1])
                    horizontal_even.cx(idx, idx + grid_size[1])
        
        qc.compose(horizontal_odd, inplace=True)
        qc.barrier()
        qc.compose(horizontal_even, inplace=True)
        qc.barrier()

        # 3 layers
        qc.h(range(num_qubits)) # H turns X into Z and Y into X, so we can implement the mixer with CNOTs and Rz rotations.
        qc.s(range(num_qubits)) # S turns X into Y and Y into X, so we can implement the mixer with CNOTs and Rz rotations.
        qc.h(range(num_qubits))

        # "vertical" edges

        # each of these uses three layers (total of 6)
        vertical_odd = QuantumCircuit(num_qubits)
        vertical_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                # 3 layers
                if j % 2 == 0:
                    vertical_odd.cx(idx, idx + 1)
                    vertical_odd.rz(2*beta_i, idx + 1)
                    vertical_odd.cx(idx, idx + 1)
                else:
                    vertical_even.cx(idx, idx + 1)
                    vertical_even.rz(2*beta_i, idx + 1)
                    vertical_even.cx(idx, idx + 1)
        
        qc.compose(vertical_odd, inplace=True)
        qc.barrier()
        qc.compose(vertical_even, inplace=True)
        qc.barrier()

        # "horizontal" edges

        # each of these uses three layers (total of 6)
        horizontal_odd = QuantumCircuit(num_qubits)
        horizontal_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                # 3 layers
                if i % 2 == 0:
                    horizontal_odd.cx(idx, idx + grid_size[1])
                    horizontal_odd.rz(2*beta_i, idx + grid_size[1])
                    horizontal_odd.cx(idx, idx + grid_size[1])
                else:
                    horizontal_even.cx(idx, idx + grid_size[1])
                    horizontal_even.rz(2*beta_i, idx + grid_size[1])
                    horizontal_even.cx(idx, idx + grid_size[1])
        
        qc.compose(horizontal_odd, inplace=True)
        qc.barrier()
        qc.compose(horizontal_even, inplace=True)
        qc.barrier()

        qc.h(range(num_qubits)) # H turns X into Z and Y into X, so we can implement the mixer with CNOTs and Rz rotations.
        qc.sdg(range(num_qubits)) # S turns X into Y and Y into X,

    return qc
        
