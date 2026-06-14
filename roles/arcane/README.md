# danmwallace.podman.arcane

Deploys [Arcane](https://getarcaneapp.com/) — a container management UI — alongside
its PostgreSQL database as rootful Podman Quadlet units on Fedora Server. Both
services run under systemd (as `arcane.service` and `arcane-postgres.service`),
restart automatically on failure, and join a dedicated `arcane` Podman network.
The Arcane container also attaches to the `proxy_network` Podman network and
carries Traefik labels so that the reverse proxy can route HTTPS traffic to it
at the configured hostname.

Arcane connects to the host Podman socket via `/run/podman/podman.sock` (mounted
as `/var/run/docker.sock` inside the container), which allows it to manage
containers and images on the local host. Postgres data is persisted to a
subdirectory of `arcane_data_dir` on the host filesystem.

## Requirements

- Fedora Server with Podman and systemd-based Quadlet support (Podman >= 4.4).
- A Traefik reverse-proxy instance running in the `proxy_network` Podman network
  and configured with a `cloudflare` TLS cert resolver.
- Ansible >= 2.16.

## Role Variables

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `arcane_version` | str | no | `latest` | Arcane image tag (e.g. `latest`, `1.2.3`). |
| `arcane_hostname` | str | **yes** | `arcane.example.com` | Public hostname for Arcane (e.g. `arcane.example.com`). Used for `APP_URL` and the Traefik routing rule. |
| `arcane_data_dir` | str | no | `/opt/podman/arcane` | Host directory for Arcane persistent data. Postgres data is stored under a `postgres/` subdirectory. |
| `arcane_postgres_db` | str | no | `arcane` | Name of the Postgres database created for Arcane. |
| `arcane_postgres_user` | str | no | `arcane` | Postgres username Arcane connects with. |
| `arcane_postgres_password` | str | **yes** | `""` | Postgres password for `arcane_postgres_user`. **Supply from vault.** |
| `arcane_encryption_key` | str | **yes** | `""` | Encryption key used by Arcane for at-rest secret encryption. **Supply from vault.** |
| `arcane_jwt_secret` | str | **yes** | `""` | JWT signing secret for Arcane session tokens. **Supply from vault.** |

## Dependencies

None declared in `meta/main.yml`. The collection itself depends on
`containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, and
`community.general >= 8.0.0` (declared in `galaxy.yml`).

## Example Playbook

```yaml
- name: Deploy Arcane
  hosts: util_servers
  roles:
    - role: danmwallace.podman.arcane
      vars:
        arcane_hostname: arcane.example.com
        arcane_version: "1.2.3"
        arcane_data_dir: /opt/podman/arcane
        arcane_postgres_db: arcane
        arcane_postgres_user: arcane
        # Supply the following three from Ansible Vault:
        arcane_postgres_password: "{{ vault_arcane_postgres_password }}"
        arcane_encryption_key: "{{ vault_arcane_encryption_key }}"
        arcane_jwt_secret: "{{ vault_arcane_jwt_secret }}"
```

## What the Role Does

1. Creates the host data directories `arcane_data_dir` and
   `arcane_data_dir/postgres` (mode `0755`).
2. Writes the `arcane` Podman network Quadlet unit to
   `/etc/containers/systemd/arcane.network`.
3. Renders and deploys the `arcane-postgres` Quadlet container unit to
   `/etc/containers/systemd/arcane-postgres.container` from the
   `arcane-postgres.container.j2` template; notifies the
   `Restart arcane-postgres` handler if the file changes.
4. Renders and deploys the `arcane` Quadlet container unit to
   `/etc/containers/systemd/arcane.container` from the `arcane.container.j2`
   template; notifies the `Restart arcane` handler if the file changes.
5. Runs `systemctl daemon-reload` then enables and starts
   `arcane-postgres.service`.
6. Enables and starts `arcane.service`.

## Notes

- The Arcane container mounts `/run/podman/podman.sock` with `SecurityLabelDisable=true`
  to satisfy SELinux constraints on the socket without needing a custom policy.
- Both handler tasks suppress the `Could not find the requested service` systemd
  error that fires in Molecule (where `daemon-reload` is skipped via
  `molecule-notest` tags and the Quadlet unit is never registered). Any other
  failure is still surfaced.
- Arcane listens on port `3552` inside the container. The Traefik label
  `traefik.http.services.arcane.loadbalancer.server.port=3552` tells Traefik
  where to forward traffic.
- The `arcane-postgres` container is Postgres 17 Alpine and is only reachable
  within the `arcane` network; it is not exposed to `proxy_network` or to the host.

## License

MIT
