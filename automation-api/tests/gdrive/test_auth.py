from lib.config import read_config
from lib.gdrive.auth import authorize, authorized_service_account_credentials


def test_auth() -> None:
    config = read_config()

    b64_encoded_service_account_credentials = config["SERVICE_ACCOUNT_CREDENTIALS"]

    # Don't test further if credentials are not set
    if len(b64_encoded_service_account_credentials) == 0:
        return

    assert len(b64_encoded_service_account_credentials) > 1

    credentials = authorized_service_account_credentials(b64_encoded_service_account_credentials)

    authorize(credentials)

    assert "Empty assert to ensure pytest passes as long as the above code succeeds."
