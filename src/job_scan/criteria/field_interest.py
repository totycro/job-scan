"""Employer business-domain interest policy."""

PROMPT_VERSION = "field-interest-v1"
INSTRUCTIONS = """Assess interest in the evidenced employer's business domain. Keep recruiting
 agency and client fields separate from the employer's. A company name alone does not establish
 its field; never use model memory to fill missing company facts. Keep employer affinity
separate."""
