from typing import Iterable, Union

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
    and returns the first client whose ``ping()`` succeeds.

    :param host: Controller IP or hostname
    :param ports: Ports to probe in order. Real controllers use 443 (RWS2) or 80 (RWS1); RobotStudio virtual
                  controllers serve RWS2 over https on 80 or a per-controller port
    :raises ConnectionError: No port answered as RWS1 or RWS2
    """
    ports = list(ports)
    for port in ports:
        for cls, scheme in ((RWS2, "https"), (RWS, "http")):
            client = cls(f"{scheme}://{host}:{port}", username=username, password=password)
            if client.ping(timeout=timeout):
                return client
    raise ConnectionError(f"No RWS1/RWS2 controller answered at {host} on ports {ports}")
