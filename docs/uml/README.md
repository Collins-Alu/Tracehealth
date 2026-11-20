# UML diagrams (as built)

These diagrams describe the system as implemented, following the SRS
Appendix B flows. They are written in Mermaid, which GitHub and VS Code
(with the "Markdown Preview Mermaid Support" extension) render directly.

| File | Diagram | SRS |
|---|---|---|
| [class-diagram.md](class-diagram.md) | Entities and relationships | B.1 / B.2 |
| [b3-submit-report.md](b3-submit-report.md) | Submitting a report, online or offline | B.3 |
| [b4-verify-report.md](b4-verify-report.md) | Verification and its consequences | B.4 |
| [b5-health-linkage.md](b5-health-linkage.md) | Clinic import and linkage | B.5 |
| [b6-payout.md](b6-payout.md) | Incentive payout | B.6 |
| [states.md](states.md) | Report and payout state machines | |

To export a PNG/SVG for the report: `npx -p @mermaid-js/mermaid-cli mmdc -i class-diagram.md -o class-diagram.svg`.
