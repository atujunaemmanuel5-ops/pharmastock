# Pharmacist verification queue

The software now exposes `/safety/rules` and `/safety/interactions` so a
pharmacist can review the exact rule and interaction rows used by the demo.

Before operational or clinical use, a pharmacist must:

1. Verify every `prescription_required` row in
   `data/raw/synthetic_data/rx_rules.csv` against current Uganda regulatory
   guidance and record `verified_by`, `verified_on`, and `source_ref`.
2. Review the DDInter-to-catalogue mappings produced by
   `src/safety/interactions.py`, especially the hand-reviewed demo severities.
3. Confirm that each interaction's severity, management wording, and source are
   appropriate for the local dispensing context.

The application intentionally enforces only prescription rules with a source
reference. It must not silently turn proposed rows into clinical rules.
