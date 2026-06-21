# Changelog

All notable changes to this collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this collection adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-21

### Added

- `dashy` role — deploys Dashy homelab dashboard as a Podman Quadlet unit with a
  fully rendered `dashy-config.yml` template; supports configurable sections,
  status checks, and `statusCheckUrl` overrides per item.
- `librechat`: `librechat_hermes_personal_model` and `librechat_hermes_infra_model`
  variables for the model name reported to LibreChat (defaults to `hermes-agent`).
- `librechat`: Hermes custom endpoint support with `librechat_hermes_personal_enabled`
  and `librechat_hermes_infra_enabled` toggles, URLs, and API key variables.

### Changed

- `traefik`: file provider switched from a single `dynamic_conf.yml` to a
  `conf.d/` directory (`watch: true`), allowing other roles to drop their own
  route files without touching the traefik role.

## [0.1.0] - 2026-06-14

### Added

- Initial release of `danmwallace.podman`.
- `common` role — Fedora base configuration for Podman hosts (packages, firewalld, SELinux,
  users, qemu-guest-agent, cockpit, Quadlet directory).
- `traefik` role — Traefik reverse proxy deployed as a Podman Quadlet unit.
- `arcane` role — Arcane service deployed as Podman Quadlet units.
- `it_tools` role — it-tools deployed as a Podman Quadlet unit.
- `librechat` role — LibreChat and its dependency stack (Meilisearch, vectordb, RAG API)
  as Podman Quadlet units.
- `n8n` role — n8n and its Postgres database as Podman Quadlet units.
- `semaphore` role — Semaphore UI and its Postgres database as Podman Quadlet units.
- Molecule scenarios for every role (`default` Ubuntu smoke-test + `fedora` primary for `common`).
