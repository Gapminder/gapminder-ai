from lib.config import read_config
from lib.gdrive.auth import (
    AuthorizedClients,
    authorize,
    authorized_service_account_credentials,
)


def get_service_account_authorized_clients() -> AuthorizedClients:
    config = read_config()

    b64_encoded_service_account_credentials = config["SERVICE_ACCOUNT_CREDENTIALS"]
    credentials = authorized_service_account_credentials(
        b64_encoded_service_account_credentials
    )
    authorized_clients = authorize(credentials)
    return authorized_clients
