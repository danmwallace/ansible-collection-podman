# danmwallace.podman.semaphore

Deploys [Semaphore UI](https://semaphoreui.com/) — a web UI for running Ansible
playbooks — together with a PostgreSQL database, both as rootful Podman Quadlet
container units on Fedora Server. The application runs
`docker.io/semaphoreui/semaphore:{{ semaphore_version }}` (default `v2.19.12`) with
`semaphore server --no-config`, so it is configured entirely through `SEMAPHORE_*`
environment variables in the Quadlet unit; the sidecar runs
`docker.io/library/postgres:17.11-alpine` with a `pg_isready` health check. Units are
placed under `/etc/containers/systemd/` and managed by systemd, so both services
survive reboots.

The Semaphore container attaches to two networks: a private `semaphore` network shared
with its Postgres sidecar, and the host's `proxy_network` so Traefik can route
`https://{{ semaphore_hostname }}` to port 3000 using the `cloudflare` certificate
resolver on the `websecure` entrypoint. Data is bind-mounted from `semaphore_data_dir`
(default `/opt/podman/semaphore`): `data/` to `/var/lib/semaphore`, `config/` to
`/etc/semaphore`, and `postgres/` to `/var/lib/postgresql`.

## Requirements

- Ansible >= 2.16
- Fedora Server with Podman and the systemd Quadlet generator (`podman >= 4.4`)
- The `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, and
  `community.general >= 8.0.0` collections (declared as collection-level dependencies
  of `danmwallace.podman`)
- A Traefik reverse proxy attached to the `proxy_network` Podman network with a
  `websecure` entrypoint and a certificate resolver named `cloudflare` (typically from
  `danmwallace.podman.traefik`)

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `semaphore_version` | str | no | `v2.19.12` | Semaphore image tag for `docker.io/semaphoreui/semaphore`. |
| `semaphore_hostname` | str | yes | — | Hostname for the Semaphore web interface (e.g. `semaphore.example.com`). Used in the Traefik router rule. |
| `semaphore_data_dir` | str | no | `/opt/podman/semaphore` | Host base directory for Semaphore data, config, and Postgres volumes. |
| `semaphore_postgres_db` | str | no | `semaphore` | Name of the Postgres database for Semaphore. |
| `semaphore_postgres_user` | str | no | `semaphore` | Postgres username for Semaphore. |
| `semaphore_postgres_password` | str | yes | — | Postgres password for Semaphore. Must not be empty. **Supply from vault.** |
| `semaphore_admin` | str | no | `admin` | Semaphore admin username. |
| `semaphore_admin_password` | str | yes | — | Semaphore admin password. Must not be empty. **Supply from vault.** |
| `semaphore_admin_name` | str | no | `Admin` | Display name for the Semaphore admin user. |
| `semaphore_admin_email` | str | no | `admin@example.com` | Email address for the Semaphore admin user. |
| `semaphore_access_key_encryption` | str | yes | — | Encryption key for stored credentials (`SEMAPHORE_ACCESS_KEY_ENCRYPTION`). Must not be empty. **Supply from vault.** |
| `semaphore_cookie_hash` | str | yes | — | HMAC key for session cookies (`SEMAPHORE_COOKIE_HASH`). Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `semaphore_cookie_encryption` | str | yes | — | Encryption key for session cookies (`SEMAPHORE_COOKIE_ENCRYPTION`). Generate with `openssl rand -base64 32`. **Supply from vault.** |
| `semaphore_playbook_path` | str | no | `/tmp/semaphore/` | Value passed as `SEMAPHORE_PLAYBOOK_PATH`. See **Notes**. |
| `semaphore_ansible_host_key_checking` | str | no | `"False"` | Value for `ANSIBLE_HOST_KEY_CHECKING` in the Semaphore container environment. |

## Dependencies

None declared in `meta/main.yml`. The target host needs Podman with Quadlet support and
an existing `proxy_network` Quadlet network (created by `danmwallace.podman.traefik`).

## Example Playbook

```yaml
- hosts: util_servers
  become: true
  roles:
    - role: danmwallace.podman.semaphore
      vars:
        semaphore_hostname: semaphore.example.com
        semaphore_admin_email: ops@example.com
        semaphore_postgres_password: "{{ vault_semaphore_postgres_password }}"
        semaphore_admin_password: "{{ vault_semaphore_admin_password }}"
        semaphore_access_key_encryption: "{{ vault_semaphore_access_key_encryption }}"
        semaphore_cookie_hash: "{{ vault_semaphore_cookie_hash }}"
        semaphore_cookie_encryption: "{{ vault_semaphore_cookie_encryption }}"
```

## What the Role Does

1. Asserts that `semaphore_postgres_password`, `semaphore_admin_password`,
   `semaphore_access_key_encryption`, `semaphore_cookie_hash`, and
   `semaphore_cookie_encryption` are all non-empty (with `no_log`), failing early
   instead of rendering units with blank secrets.
2. Creates `{{ semaphore_data_dir }}` and its `data/`, `config/`, and `postgres/`
   subdirectories with mode `0755`.
3. Writes `/etc/containers/systemd/semaphore.network`, a minimal Quadlet network unit
   labelled `managed_by=ansible`.
4. Renders `/etc/containers/systemd/semaphore-postgres.container` from
   `semaphore-postgres.container.j2`: `postgres:17.11-alpine` on the `semaphore`
   network, credentials from the role variables, and a `pg_isready` health check
   (5s interval, 3s timeout, 5 retries, 15s start period). Notifies
   `Restart semaphore-postgres` on change.
5. Renders `/etc/containers/systemd/semaphore.container` from `semaphore.container.j2`:
   the application container, ordered after and requiring `semaphore-postgres.service`,
   attached to both networks, with all database, admin, and encryption settings injected
   as environment variables plus Traefik labels. Notifies `Restart semaphore` on change.
6. Enables and starts `semaphore-postgres.service` (with `daemon_reload: true` so the
   Quadlet generator picks up the new units).
7. Enables and starts `semaphore.service`.

The `Restart semaphore-postgres` and `Restart semaphore` handlers each restart their
service with a daemon-reload when the corresponding unit file changed.

## Notes

- The Postgres unit uses `Restart=always`; the Semaphore unit uses `Restart=on-failure`
  with `RestartSec=5s` and `StartLimitBurst=10`, so a crash loop is retried rather than
  restarted forever.
- The database connection is `PGSSLMODE=disable` over the private `semaphore` network;
  the sidecar is not reachable from `proxy_network`.
- `SEMAPHORE_PLAYBOOK_PATH` is not a configuration key Semaphore reads (its temporary
  path option is `tmp_path` / `SEMAPHORE_TMP_PATH`, default `/tmp/semaphore`). The
  variable is passed through unchanged for compatibility; leaving it at the default has
  no effect on where Semaphore stores working copies.
- The role does not migrate data across PostgreSQL major versions. The sidecar is pinned
  to a `17.x-alpine` tag; patch bumps within the major are safe, but moving the image to
  a new major on an existing `postgres/` directory will fail to start until the operator
  dumps and restores (or `pg_upgrade`s) the cluster.
- The Traefik network label is `systemd-proxy_network`, the name systemd assigns to a
  Quadlet-managed network called `proxy_network`. The role does not open any host
  firewall ports; TLS terminates at Traefik.
- The systemd enable/start tasks and both handlers carry `tags: [molecule-notest]` so
  Molecule can lint and template without a working Quadlet generator. The handlers also
  suppress the "Could not find the requested service" error systemd raises in Molecule
  when the unit has never been loaded.

## License

MIT
