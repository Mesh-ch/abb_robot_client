from typing import Iterable, Union

import requests

from .rws import RWS
from .rws2 import RWS2


def connect(
    host: str,
    ports: Iterable[int] = (443, 80),
    username: str = "Default User",
    password: str = "robotics",
    timeout: float = 1.0,
) -> Union[RWS, RWS2]:
    """
    Detect the controller's RWS version and return a matching client.

    For each port in order, tries RWS 2.0 (https, OmniCore / RobotWare 7) then RWS 1.0 (http, IRC5 / RobotWare 6)
    and returns the first client whose root endpoint answers HTTP 200.

    :param host: Controller IP or hostname
    :param ports: Ports to probe in order. Real controllers use 443 (RWS2) or 80 (RWS1); RobotStudio virtual
                  controllers serve RWS2 over https on 80 or a per-controller port
    :raises ConnectionError: No port answered, or the controller rejected the username/password
    """
    ports = list(ports)
    rejected = []
    for port in ports:
        for cls, scheme in ((RWS2, "https"), (RWS, "http")):
            client = cls(f"{scheme}://{host}:{port}", username=username, password=password)
            # Same request as client.ping(), but keeps the status so a 401 is reported as bad credentials
            headers = {"accept": "application/hal+json;v=2.0"} if cls is RWS2 else None
            try:
                res = client._session.get(
                    f"{client.base_url}/", auth=client.auth, headers=headers, timeout=timeout, verify=False
                )
                res.close()
            except requests.RequestException:
                continue
            if res.status_code == 200:
                return client
            if res.status_code == 401:
                rejected.append(f"{cls.__name__} at {client.base_url}")
    if rejected:
        raise ConnectionError(f"Controller rejected username '{username}' / password ({', '.join(rejected)})")
    raise ConnectionError(f"No RWS1/RWS2 controller answered at {host} on ports {ports}")
