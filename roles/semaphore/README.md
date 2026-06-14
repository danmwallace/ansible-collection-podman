# danmwallace.podman.semaphore

Deploys [Semaphore](https://semaphoreui.com/) — a web UI for running Ansible playbooks — together
with a PostgreSQL 17 database, both running as rootful Podman Quadlet container units on Fedora
Server. Quadlet units are placed under `/etc/containers/systemd/` and are managed by systemd,
so both services survive reboots and are restarted automatically on failure.

The Semaphore container attaches to two networks: a private `semaphore.network` that it shares with
its Postgres sidecar, and the host's `proxy_network` Traefik network so that the UI is reachable
via HTTPS. Traefik routing labels are written directly into the Quadlet unit; the role expects a
running Traefik reverse proxy (with a Cloudflare certificate resolver) to already be present on
the host.

## Requirements

- Fedora Server with Podman and the systemd Quadlet generator available (`podman >= 4.4`).
- A Traefik reverse proxy attached to a network named `proxy_network` on the host.
- Ansible >= 2.16.
- The `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, and
  `community.general >= 8.0.0` collections (declared as collection-level dependencies in
  `danmwallace.podman`).

## Role Variables

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `semaphore_version` | str | no | `latest` | Semaphore image tag (`semaphoreui/semaphore:<tag>`). |
| `semaphore_hostname` | str | **yes** | — | Hostname for the Semaphore web interface (e.g. `semaphore.example.com`). Used in the Traefik routing rule. |
| `semaphore_data_dir` | str | no | `/opt/podman/semaphore` | Host base directory for Semaphore data, config, and Postgres volumes. |
| `semaphore_postgres_db` | str | no | `semaphore` | Name of the Postgres database for Semaphore. |
| `semaphore_postgres_user` | str | no | `semaphore` | Postgres username for Semaphore. |
| `semaphore_postgres_password` | str | **yes** | — | Postgres password. Must not be empty. **Supply from vault.** |
| `semaphore_admin` | str | no | `admin` | Semaphore admin username. |
| `semaphore_admin_password` | str | **yes** | — | Semaphore admin password. Must not be empty. **Supply from vault.** |
| `semaphore_admin_name` | str | no | `Admin` | Display name for the Semaphore admin user. |
| `semaphore_admin_email` | str | no | `admin@example.com` | Email address for the Semaphore admin user. |
| `semaphore_access_key_encryption` | str | **yes** | — | Encryption key for Semaphore stored credentials (`SEMAPHORE_ACCESS_KEY_ENCRYPTION`). Must not be empty. **Supply from vault.** |
| `semaphore_playbook_path` | str | no | `/tmp/semaphore/` | Path inside the container where Semaphore writes temporary playbook files. |
| `semaphore_ansible_host_key_checking` | str | no | `"False"` | Value for `ANSIBLE_HOST_KEY_CHECKING` in the Semaphore container environment. |

## Dependencies

No role-level dependencies. The collection-level dependency on `containers.podman >= 1.11.0`,
`ansible.posix >= 1.5.0`, and `community.general >= 8.0.0` must be satisfied by the consuming
control repo's `requirements.yml`.

## Example Playbook

```yaml
- name: Deploy Semaphore
  hosts: util_servers
  become: true
  vars:
    semaphore_hostname: semaphore.example.com
    semaphore_version: "2.10.22"
    semaphore_postgres_password: "{{ vault_semaphore_postgres_password }}"
    semaphore_admin_password: "{{ vault_semaphore_admin_password }}"
    semaphore_access_key_encryption: "{{ vault_semaphore_access_key_encryption }}"
    semaphore_admin_email: ops@example.com
  roles:
    - danmwallace.podman.semaphore
```

## What the Role Does

1. Creates the host directories `semaphore_data_dir`, `semaphore_data_dir/data`,
   `semaphore_data_dir/config`, and `semaphore_data_dir/postgres` with mode `0755`.
2. Writes the Quadlet network unit `/etc/containers/systemd/semaphore.network` (a private
   bridge network shared by both containers).
3. Templates `/etc/containers/systemd/semaphore-postgres.container` from
   `semaphore-postgres.container.j2` — a Postgres 17 Alpine container with a bind-mounted
   data volume and credentials injected as environment variables. Notifies the
   `Restart semaphore-postgres` handler on change.
4. Templates `/etc/containers/systemd/semaphore.container` from `semaphore.container.j2` —
   the Semaphore application container, attached to both `semaphore.network` and
   `proxy_network`, with all connection and admin credentials injected as environment
   variables and Traefik labels for HTTPS routing. Notifies the `Restart semaphore` handler
   on change.
5. Enables and starts `semaphore-postgres.service` via systemd (with `daemon_reload: true`
   so the Quadlet generator picks up the new unit file).
6. Enables and starts `semaphore.service` via systemd.

Handler restarts (`Restart semaphore-postgres`, `Restart semaphore`) fire after all tasks
complete if the corresponding Quadlet unit file changed. Both handlers suppress the
"Could not find the requested service" error that occurs in Molecule, where the daemon-reload
step is skipped.

## Notes

- Both Quadlet units have `Restart=always` in their `[Service]` section, so systemd
  automatically recovers crashed containers without Ansible intervention.
- The Semaphore container binds to port `3000` internally; Traefik is responsible for TLS
  termination using the `cloudflare` cert resolver. The role does not open any host firewall
  ports.
- Tasks that interact with systemd are tagged `molecule-notest` so Molecule scenarios can
  exercise template rendering without requiring a full systemd environment.
- Pin `semaphore_version` to a specific tag in production. The `latest` default is
  convenient for initial setup but will pull a new image on every Podman pull, making
  deployments non-deterministic.

## License

MIT
