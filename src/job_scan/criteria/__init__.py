"""Static code-owned dimension definitions in presentation order."""

from dataclasses import dataclass

from job_scan.criteria import company_affinity, field_interest, role_fit, technology_fit


@dataclass(frozen=True)
class DimensionDefinition:
    id: str
    label: str
    instructions: str
    prompt_version: str


DIMENSIONS = tuple(
    DimensionDefinition(name, label, policy.INSTRUCTIONS, policy.PROMPT_VERSION)
    for name, label, policy in (
        ("role_fit", "Role fit", role_fit),
        ("technology_fit", "Technology fit", technology_fit),
        ("field_interest", "Field interest", field_interest),
        ("company_affinity", "Company affinity", company_affinity),
    )
)
