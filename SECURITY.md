# Security Policy

## Reporting a Vulnerability

Please use **GitHub Private vulnerability reporting** (the "Report a vulnerability"
button under the Security tab) to report security issues privately. Do not open a
public issue for a suspected vulnerability.

## Scope

This repository is a **starter template and a small, dependency-light overlay
engine** (YAML in, merged dict out). The realistic threat surface is:

- `overlay_scoring.overlay.load_yaml` uses `yaml.safe_load` (no arbitrary object
  construction). Passing untrusted YAML is expected to fail safely; report it if
  it does not.
- The engine never executes code from definitions or overlays; it only reads
  fields and copies opaque payloads.

Out of scope (by design, not a vulnerability):

- A definition or overlay that is semantically wrong but structurally valid
  (e.g. a threshold that does not match your intent) — that is a content review
  concern, not a security issue.
- Resource use from extremely large definition files.
