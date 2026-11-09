"""Role-specific policy, independent of other fit dimensions."""

PROMPT_VERSION = "role-fit-v1"
INSTRUCTIONS = """Assess responsibilities, seniority, hands-on versus management work and career
 direction against the user's desired role. Use only the identified target role's supplied HTML.
 Distinguish required duties from optional ones. Silence about management is not proof of no
 management duties. Preserve unknown conditions required for fit."""
