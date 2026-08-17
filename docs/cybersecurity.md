# Ethical Hacking Workspace

Phase 11 implements an authorized Ethical Hacking cockpit for labs, defensive validation, secure code review, findings, notes, evidence, and read-only repository review.

The backend keeps the stable `/api/v1/security` API for compatibility. The preferred frontend page is `/ethical-hacking`; `/cybersecurity` remains a compatibility route.

Safety boundaries:

- Scope must come from explicit user input and trusted `config/policy.yaml`, never from model or retrieved text.
- Static review is read-only and scans bounded repository text files.
- Sample inspection computes metadata and printable strings only; it does not execute samples.
- Findings and notes are persisted as user data and remain untrusted when later used as context.
- Broad Ethical Hacking knowledge is allowed, including reconnaissance, web testing, AD concepts, reverse engineering, malware analysis, forensics, and detection engineering. Execution is policy-controlled and auditable.

The initial static review engine is intentionally lightweight. It detects common patterns such as possible hardcoded secrets, `shell=True`, dynamic execution, unsafe pickle deserialization, and interpolated SQL. It is not a replacement for dedicated SAST tooling.

When a configured active scope exists in trusted application state, agents may use it as context and should not repeatedly ask authorization questions. Scope is never inferred from ordinary chat text, retrieved documents, model output, or tool output.
