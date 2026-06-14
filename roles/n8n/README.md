# danmwallace.podman.n8n

Deploys [n8n](https://n8n.io/) workflow automation and its PostgreSQL 15 database
as rootful Podman Quadlet systemd units on Fedora Server. Both containers run on a
dedicated `n8n` Podman network; the n8n container is also attached to a shared
`proxy_network` so Traefik can pick it up via container labels and terminate TLS
through a Cloudflare cert resolver.

Data directories are created on the host under a configurable base path and
bind-mounted into the containers with the `:z` SELinux relabelling flag. The n8n
container runs as UID/GID 1000; its data and local-files directories are
pre-created with matching ownership. The role registers a handler that restarts
both services (Postgres first, then n8n) whenever either Quadlet unit file changes.

## Requirements

- Fedora Server with Podman and systemd-based Quadlet support (`podman >= 4.4`).
- A Traefik reverse proxy listening on the `proxy_network` Podman network with a
  Cloudflare cert resolver named `cloudflare` and an `websecure` entrypoint.
- Ansible `>= 2.16`.

## Role Variables

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `n8n_hostname` | str | yes | — | Hostname for the n8n web interface (e.g. `n8n.example.com`). Used to set `N8N_HOST`, `WEBHOOK_URL`, and the Traefik router rule. |
| `n8n_encryption_key` | str | yes | — | Encryption key used by n8n to encrypt credentials at rest. Must remain stable; changing it invalidates all stored credentials. **Supply from vault.** |
| `n8n_postgres_password` | str | yes | — | Password for the Postgres n8n user. **Supply from vault.** |
| `n8n_data_dir` | str | no | `/opt/podman/n8n` | Host base directory for n8n data, Postgres data, and local files. |
| `n8n_postgres_user` | str | no | `n8n` | Postgres username for the n8n database. |
| `n8n_postgres_db` | str | no | `n8n` | Postgres database name for n8n. |

## Dependencies

None declared in `meta/main.yml`. The collection itself depends on
`containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, and
`community.general >= 8.0.0`, which must be present in the execution environment.

## Example Playbook

```yaml
- name: Deploy n8n
  hosts: util_servers
  roles:
    - role: danmwallace.podman.n8n
      vars:
        n8n_hostname: n8n.example.com
        n8n_encryption_key: "{{ vault_n8n_encryption_key }}"
        n8n_postgres_password: "{{ vault_n8n_postgres_password }}"
```

## What the Role Does

1. Creates the base data directory (`n8n_data_dir`) owned by root, mode `0755`.
2. Creates `{{ n8n_data_dir }}/data` and `{{ n8n_data_dir }}/local-files` with
   owner/group `1000:1000` so the n8n container process can write to them without
   privilege escalation.
3. Creates `{{ n8n_data_dir }}/postgres` owned by root, mode `0755`, for the
   Postgres data volume.
4. Writes `/etc/containers/systemd/n8n.network` — a minimal Quadlet network unit
   that defines the `n8n` Podman network with an `ansible` managed-by label.
5. Renders `/etc/containers/systemd/n8n-postgres.container` from the
   `n8n-postgres.container.j2` template, running `postgres:15` on the `n8n`
   network with the configured credentials and a bind-mount for persistent data.
   Notifies the **Restart n8n** handler on change.
6. Renders `/etc/containers/systemd/n8n.container` from the `n8n.container.j2`
   template, running `n8nio/n8n:latest` on both the `n8n` and `proxy_network`
   networks. Sets `N8N_HOST`, `N8N_PROTOCOL`, `N8N_ENCRYPTION_KEY`, database
   connection variables, and Traefik routing labels. Notifies the **Restart n8n**
   handler on change.
7. Enables and starts `n8n-postgres.service` (with `daemon_reload: true`).
8. Enables and starts `n8n.service`.

On handler trigger: restarts `n8n-postgres.service` (daemon-reload), then
`n8n.service` (daemon-reload).

## Notes

- Both Quadlet unit files are placed under `/etc/containers/systemd/` (rootful
  Quadlet path). The n8n container is attached to `proxy_network` using the
  `systemd-proxy_network` network name as the Traefik Docker network label — this
  is the name systemd assigns to Quadlet-managed networks.
- The `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true` environment variable causes n8n
  to enforce strict permissions on its settings file; the pre-created data
  directory with correct ownership satisfies this requirement.
- Systemd enable/start tasks and both handler tasks carry `tags: [molecule-notest]`
  so Molecule scenarios can lint and template without a running Podman daemon. The
  handler also suppresses the "Could not find the requested service" error that
  systemd raises in Molecule when the Quadlet unit has never been loaded.

## License

MIT
