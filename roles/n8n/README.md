# danmwallace.podman.n8n

Deploys [n8n](https://n8n.io/) workflow automation and its PostgreSQL database as
rootful Podman Quadlet systemd units on Fedora Server. The n8n container runs
`docker.io/n8nio/n8n:{{ n8n_version }}` (default `2.38.4`) and the sidecar runs
`docker.io/library/postgres:17.11-alpine`. Both containers share a dedicated `n8n`
Podman network; the n8n container is also attached to the shared `proxy_network`
so Traefik can discover it via container labels and terminate TLS with the
`cloudflare` certificate resolver on the `websecure` entrypoint.

Data lives on the host under `n8n_data_dir` (default `/opt/podman/n8n`) and is
bind-mounted with the `:z` SELinux relabelling flag: `data/` to `/home/node/.n8n`,
`local-files/` to `/files`, and `postgres/` to `/var/lib/postgresql/data`. The n8n
container runs as UID/GID 1000, so its two writable directories are pre-created with
matching ownership. n8n is configured entirely through environment variables in the
Quadlet unit (`N8N_HOST`, `N8N_PROTOCOL=https`, `WEBHOOK_URL`, `N8N_RUNNERS_ENABLED=true`,
`DB_TYPE=postgresdb`, `DB_POSTGRESDB_*`) and listens on port 5678 inside the container.

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
| `n8n_hostname` | str | yes | — | Hostname for the n8n web interface (e.g. `n8n.example.com`). Sets `N8N_HOST`, `WEBHOOK_URL`, and the Traefik router rule. |
| `n8n_encryption_key` | str | yes | — | Encryption key n8n uses to encrypt credentials at rest. Must stay stable; changing it invalidates all stored credentials. **Supply from vault.** |
| `n8n_postgres_password` | str | yes | — | Password for the Postgres n8n user. **Supply from vault.** |
| `n8n_data_dir` | str | no | `/opt/podman/n8n` | Host base directory for n8n data, Postgres data, and local files. |
| `n8n_postgres_user` | str | no | `n8n` | Postgres username for the n8n database. |
| `n8n_postgres_db` | str | no | `n8n` | Postgres database name created by the sidecar (`POSTGRES_DB`). See **Notes** before changing it. |
| `n8n_version` | str | no | `"2.38.4"` | Image tag for `docker.io/n8nio/n8n`. |

## Dependencies

None declared in `meta/main.yml`. The target host needs Podman with Quadlet support and
an existing `proxy_network` Quadlet network (created by `danmwallace.podman.traefik`).

## Example Playbook

```yaml
- hosts: ai_servers
  become: true
  roles:
    - role: danmwallace.podman.n8n
      vars:
        n8n_hostname: n8n.example.com
        n8n_encryption_key: "{{ vault_n8n_encryption_key }}"
        n8n_postgres_password: "{{ vault_n8n_postgres_password }}"
```

## What the Role Does

1. Asserts `n8n_encryption_key` and `n8n_postgres_password` are non-empty (with
   `no_log`), failing early instead of rendering units with blank secrets.
2. Creates `{{ n8n_data_dir }}` owned by root, mode `0755`.
3. Creates `{{ n8n_data_dir }}/data` and `{{ n8n_data_dir }}/local-files` with
   owner/group `1000:1000`, mode `0755`, so the n8n process can write to them.
4. Creates `{{ n8n_data_dir }}/postgres` owned by root, mode `0755`, for the Postgres
   data volume.
5. Writes `/etc/containers/systemd/n8n.network`, a minimal Quadlet network unit
   labelled `managed_by=ansible`.
6. Renders `/etc/containers/systemd/n8n-postgres.container` from
   `n8n-postgres.container.j2`: `postgres:17.11-alpine` on the `n8n` network, with
   `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` from the role variables.
   Notifies `Restart n8n` on change.
7. Renders `/etc/containers/systemd/n8n.container` from `n8n.container.j2`:
   `n8nio/n8n:{{ n8n_version }}` on both the `n8n` and `proxy_network` networks, with
   the n8n environment and Traefik labels. Notifies `Restart n8n` on change.
8. Enables and starts `n8n-postgres.service` (with `daemon_reload: true` so the Quadlet
   generator picks up the new units).
9. Enables and starts `n8n.service`.

Both templates notify the same `Restart n8n` listener, which restarts
`n8n-postgres.service` first and then `n8n.service`, each with a daemon-reload.

## Upgrading the Postgres major version

The role does **not** migrate data across PostgreSQL major versions. The sidecar image
is pinned to a specific `17.x-alpine` tag, and Postgres refuses to start on a data
directory initialised by a different major — if `{{ n8n_data_dir }}/postgres/PG_VERSION`
says `15` and the unit runs a `17.x` image, `n8n-postgres.service` will fail on every
start and n8n will never come up.

Before changing the image major (in the template or by upgrading to a collection release
that does), the operator must migrate the data directory out of band:

1. Stop `n8n.service` and, with the **old** image still running, take a logical dump
   (`pg_dumpall -U {{ n8n_postgres_user }}` inside `n8n-postgres`), or plan a
   `pg_upgrade` run with both binaries available.
2. Move the old `{{ n8n_data_dir }}/postgres` aside (keep it until the restore is
   verified).
3. Apply the role so the new-major unit initialises a fresh cluster, then restore the
   dump into it and start `n8n.service`.

Patch bumps within a major (for example `17.10-alpine` to `17.11-alpine`) need no
migration.

## Notes

- **Postgres data directory** is created `0700` and its ownership is left to `initdb`
  (uid 999); the postgres entrypoint runs `chmod 0700` on every start, so any other mode
  would show as a change on every run.
- `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true` makes n8n require strict permissions on
  its settings file; the pre-created `data/` directory with `1000:1000` ownership
  satisfies this.
- `n8n_postgres_db` only sets `POSTGRES_DB` on the sidecar. The n8n container does not
  set `DB_POSTGRESDB_DATABASE`, so n8n connects to its built-in default database name
  (`n8n`). Changing `n8n_postgres_db` to anything else will create a database n8n never
  uses.
- `GENERIC_TIMEZONE` is fixed at `UTC` and `N8N_RUNNERS_ENABLED=true` runs the task
  runner in internal (child process) mode; neither is variable-driven.
- The Traefik network label is `systemd-proxy_network`, the name systemd assigns to a
  Quadlet-managed network called `proxy_network`.
- Both Quadlet units use `Restart=always`, so systemd recovers crashed containers
  without Ansible intervention.
- The systemd enable/start tasks and both handler tasks carry `tags: [molecule-notest]`
  so Molecule can lint and template without a working Quadlet generator. The handlers
  also suppress the "Could not find the requested service" error systemd raises in
  Molecule when the unit has never been loaded.

## License

MIT
