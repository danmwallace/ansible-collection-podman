# Changelog

All notable changes to this collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this collection adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.1] - 2026-09-09

### Fixed

- `arcane`: the socket proxy could not reach the Podman socket — SELinux denies `container_t`
  `connectto` on the `container_runtime_t` socket, so every Arcane API call got a 503. The
  proxy unit now sets `SecurityLabelDisable=true`, the same setting the `traefik` unit
  already relies on; Arcane itself stays confined and the HAProxy allowlist is unchanged
- `librechat`: the RAG API unit received no embeddings configuration, so with any provider
  other than OpenAI-with-env-key it crash-looped on "Missing credentials". The unit now
  renders `EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`, `RAG_USE_FULL_CONTEXT`, the
  `RAG_AZURE_OPENAI_*` trio when the provider is `azure`, and `OPENAI_API_KEY` when it is
  `openai` — all from the existing `librechat_*` variables

## [0.6.0] - 2026-09-08

### Security

- `arcane`: replace the raw read-write Podman socket mount with a
  `tecnativa/docker-socket-proxy` sidecar (`arcane-socket-proxy`) on an internal
  `arcane-socket` Quadlet network. Arcane now reaches the API via
  `DOCKER_HOST=tcp://arcane-socket-proxy:2375`; the socket is mounted `ro,z` into the proxy
  only, with build/auth/secrets/swarm/exec endpoints denied (#28, supersedes #24)

### Added

- `arcane`: `arcane_socket_proxy_version` (default `v0.5.0`)
- `librechat`: `librechat_meilisearch_upgrade_db` (default `true`) renders
  `MEILI_UPGRADE_DB=true` so Meilisearch minor bumps upgrade the index in place
  (requires data written by v1.12 or newer)
- CI: `argument_specs drift check` job (`.github/scripts/check_argument_specs.py`) fails
  when a `meta/argument_specs.yml` default differs from `defaults/main.yml`
- `dashy`: declare `dashy_arcane_ai01_hostname`, `dashy_uptime_kuma_hostname`,
  `dashy_hermes_dash_ai01_hostname`, `dashy_hermes_dash_aimaster_hostname` in
  `argument_specs` (the template already required them)

### Changed

- `arcane`: `v2.3.1` → `v2.10.2`; Postgres `17.10-alpine` → `17.11-alpine`
- `dashy`: `4.3.12` → `4.6.0` (4.5+ requires unique section names; template verified)
- `grimmory`: `v3.2.4` → `v3.3.3`; MariaDB `11.8.8` → `11.8.9`
- `librechat`: Meilisearch `v1.48.3` → `v1.53.2`
- `n8n`: `2.28.5` → `2.38.4`; Postgres sidecar pinned `17-alpine` → `17.11-alpine`
- `semaphore`: `v2.18.14` → `v2.19.12`; Postgres `17.10-alpine` → `17.11-alpine`
- `traefik`: `v3.7.6` → `v3.7.13`
- `uptime_kuma`: `1.23.16` → `2.5.3` (**major**: one-way in-place SQLite migration on first
  start; back up the data dir first — see the role README)
- `argument_specs` defaults resynced with `defaults/main.yml` in `grimmory`, `librechat`,
  `traefik` (they still advertised `latest`, `v1.7.3`, `ankane/pgvector:latest`, `v3.6.2`)
- READMEs regenerated for `arcane`, `dashy`, `grimmory`, `librechat`, `n8n`, `semaphore`,
  `traefik`, `uptime_kuma`, with upgrade notes for Postgres majors, Meilisearch and
  Uptime Kuma 2.x

### Fixed

- `grimmory`: MariaDB health check used `mysqladmin`, which 11.x images no longer ship, so the
  container was permanently `unhealthy`; now `healthcheck.sh --connect --innodb_initialized`
- Molecule scenarios for `dashy`, `librechat`, `semaphore` supply the secrets the 0.5.0
  preflight asserts require; stale `:latest` assertions replaced with the pinned tags

## [0.5.0] - 2026-09-03

### Changed

- `uptime_kuma`: pin image from floating `:1` to `1.23.16` (#11)
- `n8n`: move Postgres sidecar from `15.18` to `17-alpine` (#18)
- `librechat`: pgvector `0.8.4-pg17` → `0.8.6-pg17` (#26); RAG API `v0.8.0` → `v0.9.0` (#25)
- `arcane`, `semaphore`: correct `argument_specs` image defaults from `latest` to the pinned
  tags (`v2.3.1`, `v2.18.14`) and mark secret options `no_log: true` (#16, #19)

### Added

- `arcane`, `n8n`, `semaphore`: preflight `assert` that required secrets are non-empty, so an
  unset vault variable fails fast instead of deploying with an empty credential (#20, #21, #23)
- `semaphore`: `semaphore_cookie_hash` and `semaphore_cookie_encryption` variables rendered as
  `SEMAPHORE_COOKIE_HASH` / `SEMAPHORE_COOKIE_ENCRYPTION` (#23)

### Security

- `grimmory`: MariaDB `HealthCmd` no longer embeds the root password on the command line (#27)
- `arcane`: document the raw Podman socket mount as a known risk pending a socket-proxy
  sidecar (#24; superseded by the 0.6.0 socket proxy)

## [0.4.4] - 2026-07-10

### Fixed

- `dashy`: add `statusCheckUrl` pointing to `/auth/password-login` for Hermes Dashboard (ai01)
  and Hermes Dashboard (ai-master) — hermes redirects unauthenticated root requests to an OAuth
  path that returns 500 with BasicAuth; the password-login endpoint returns 200

## [0.4.3] - 2026-07-02

### Fixed

- `grimmory`: mount books volume to `/books` (correct container path) instead of `/app/books`
- `grimmory`: use local persistent directory (`{{ grimmory_data_dir }}/books`) for book storage so uploads survive container restarts
- `grimmory`: set `owner/group` to `grimmory_app_uid` on `books`, `data`, and `bookdrop` directories so the container user can write to them

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
