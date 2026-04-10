import os
from pathlib import Path

from dotenv import load_dotenv
from qiskit_ibm_runtime import QiskitRuntimeService

dotenv_file = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=dotenv_file)

instance = os.getenv("IBM_CLOUD_INSTANCE")
token = os.getenv("IBM_CLOUD_TOKEN")

if not instance or not token:
    raise ValueError(
        "Missing IBM credentials. Add IBM_CLOUD_INSTANCE and IBM_CLOUD_TOKEN to your .env file."
    )

# Save an IBM Quantum account and set it as your default account.
QiskitRuntimeService.save_account(
    channel="ibm_cloud",
    instance=instance,
    token=token,
    set_as_default=True,
    overwrite=True,
)


service = QiskitRuntimeService()
backend = service.backend("ibm_rensselaer")


# To see the list of saved accounts:
service.saved_accounts()