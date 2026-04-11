from qiskit import QuantumCircuit, circuit

def LayerOptimizedCircuit(gamma: list[float], 
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

    # (i, j) -> i * grid_size[1] + j

    # ==============================================
    # 26 layers per itteration (of gamma, beta)
    # ==============================================

    for gamma_i, beta_i in zip(gamma, beta):

        # "vertical" edges
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                # one layer
                qc.rz(0-gamma_i, idx)
                qc.rz(0-gamma_i, idx + 1)

                # 3 layers
                qc.cx(idx, idx + 1)
                qc.rz(gamma_i, idx + 1)
                qc.cx(idx, idx + 1)
        
        qc.barrier()

        # "horizontal" edges
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                # one layer
                qc.rz(0-gamma_i, idx)
                qc.rz(0-gamma_i, idx + grid_size[1])

                # 3 layers
                qc.cx(idx, idx + grid_size[1])
                qc.rz(gamma_i, idx + grid_size[1])
                qc.cx(idx, idx + grid_size[1])
        
        qc.barrier()

        # mixer layer

        qc.h(range(num_qubits)) # H turns X into Z and Y into X, so we can implement the mixer with CNOTs and Rz rotations.

        # "vertical" edges
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                qc.cx(idx, idx + 1)
                qc.rz(2*beta_i, idx + 1)
                qc.cx(idx, idx + 1)
        
        qc.barrier()

        # "horizontal" edges
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                qc.cx(idx, idx + grid_size[1])
                qc.rz(2*beta_i, idx + grid_size[1])
                qc.cx(idx, idx + grid_size[1])
        
        qc.barrier()

        qc.h(range(num_qubits))
        qc.s(range(num_qubits)) # S turns X into Y and Y into X,
        qc.h(range(num_qubits))

        # "vertical" edges
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                qc.cx(idx, idx + 1)
                qc.rz(2*beta_i, idx + 1)
                qc.cx(idx, idx + 1)
        
        qc.barrier()

        # "horizontal" edges
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                qc.cx(idx, idx + grid_size[1])
                qc.rz(2*beta_i, idx + grid_size[1])
                qc.cx(idx, idx + grid_size[1])
        
        qc.barrier()
        qc.sdg(range(num_qubits)) # undo the S gate
        qc.h(range(num_qubits)) # undo the H gate


    qc.measure_all()
    return qc




    
