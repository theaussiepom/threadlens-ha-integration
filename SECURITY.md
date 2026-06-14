# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

This integration is **pre-1.0** and under active development.

## Reporting a vulnerability

Please report security issues privately rather than opening a public GitHub issue.

1. Open a [GitHub Security Advisory](https://github.com/theaussiepom/threadlens-ha-integration/security/advisories/new), or
2. Contact the maintainer via GitHub (`@theaussiepom`).

Include:

- A clear description of the issue
- Steps to reproduce
- Impact assessment
- Suggested fix if you have one

## Scope notes

- ThreadLens Core v1 has **no API authentication**. This integration inherits that model and is intended for trusted LAN use only.
- Do not expose ThreadLens or Home Assistant to the public internet without appropriate reverse-proxy authentication.
- This integration does not mutate Thread, Matter, or OTBR state and does not commission devices.
- Reports from ThreadLens Core redact secrets but may still include operational metadata.

## What we consider in scope

- Credential leakage in diagnostics or logs
- Unsafe panel JS behaviour (XSS, external network calls)
- Authentication bypass in Home Assistant websocket handlers
- Information disclosure via misconfigured diagnostics

## Out of scope

- ThreadLens Core collector behaviour (report to [threadlens](https://github.com/theaussiepom/threadlens))
- Home Assistant platform vulnerabilities
- Network exposure of unauthenticated ThreadLens on an untrusted network
