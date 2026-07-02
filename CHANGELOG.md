# Changelog

All notable changes to this collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this collection adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.2] - 2026-07-02

### Changed

- `traefik`: update default image tag from `v3.6.2` to `v3.7.6`
- `arcane`: pin image from `latest` to `v2.3.1`; pin Postgres from `17-alpine` to `17.10-alpine`
- `semaphore`: pin image from `latest` to `v2.18.14`; pin Postgres from `17-alpine` to `17.10-alpine`
- `dashy`: update image from `3.1.0` to `4.3.12` (major version — verify dashboard after deploy);
  add `dashy_version` variable; declare `dashy_version` and `dashy_image` in `argument_specs`
- `it_tools`: add `it_tools_version` variable; pin image from `latest` to `2024.10.22-7ca5933`;
  declare `it_tools_version` in `argument_specs`
- `grimmory`: pin image from `latest` to `v3.2.4`; pin MariaDB from `11` to `11.8.8`
- `n8n`: add `n8n_version` variable; pin image from `latest` to `2.28.5`; pin Postgres from `15`
  to `15.18`; declare `n8n_version` in `argument_specs`
- `librechat`: update API image to `v0.8.7`, Meilisearch to `v1.48.3` (index migration note
  added), RAG API to `v0.8.0`, pgvector to `0.8.4-pg17`

## [0.4.1] - 2026-07-01

### Fixed

- `uptime_kuma`: add `:z` SELinux relabeling to the data volume mount so the
  container's entrypoint can `chown` the directory on Fedora hosts with SELinux
  enforcing.
- `uptime_kuma`: pre-create data directory with owner UID 1000 (`node` user) so
  the container starts cleanly on first deploy without a manual `chcon`.

## [0.4.0] - 2026-07-01

### Added

- `uptime_kuma` role — deploys Uptime Kuma self-hosted monitoring dashboard as a rootful Podman
  Quadlet unit; mounts a persistent data volume; routes traffic via Traefik container labels on
  `proxy_network.network`.
  
## [0.3.1] - 2026-06-24

### Fixed

- `grimmory`: install `nfs-utils` before attempting the NFS mount (fixes
  "mount program didn't pass remote address" on hosts without nfs-utils).
- `grimmory`: embed `user` and `password` as JDBC URL query parameters in
  `DATABASE_URL` so Spring Boot picks up the application credentials rather
  than defaulting to `root`.

## [0.3.0] - 2026-06-24

### Added

- `grimmory` role — deploys Grimmory eBook library and MariaDB 11 as rootful Podman
  Quadlet units; mounts an NFS share for the books volume; routes traffic via Traefik
  container labels on `proxy_network.network`.

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
