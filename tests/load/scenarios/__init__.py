"""Load test scenario configurations."""

from tests.load.scenarios.normal import NormalLoadTest
from tests.load.scenarios.peak import PeakLoadTest
from tests.load.scenarios.sustained import SustainedLoadTest

__all__ = ["NormalLoadTest", "PeakLoadTest", "SustainedLoadTest"]
