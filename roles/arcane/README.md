# danmwallace.podman.arcane

Deploys [Arcane](https://getarcaneapp.com/) — a container management UI — with a
PostgreSQL database and a socket-proxy sidecar as rootful Podman Quadlet units on
Fedora Server. The three services run under systemd as `arcane.service`,
`arcane-postgres.service`, and `arcane-socket-proxy.service`, restart automatically
on failure, and are wired together over two dedicated Podman networks: `arcane`
(Arcane ↔ Postgres) and `arcane-socket` (Arcane ↔ socket proxy, `Internal=true`, so
it has no route off the host). The Arcane container also joins `proxy_network` and
carries Traefik labels so the reverse proxy can route HTTPS traffic to port `3552`
at the configured hostname.

Arcane never touches the host Podman socket directly. Instead, a
[Tecnativa docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy)
container mounts `/run/podman/podman.sock` read-only and exposes a filtered
Docker-compatible API on `tcp://arcane-socket-proxy:2375`, which Arcane reaches via
`DOCKER_HOST`. The proxy allowlists only the endpoints Arcane needs to manage
containers, images, networks, and volumes; `BUILD`, `AUTH`, `SECRETS`, `SWARM`, and
`EXEC` are denied, so a compromise of the Arcane UI cannot exec into other
containers or reach the raw socket. Postgres data is persisted under
`arcane_data_dir/postgres` on the host.

## Requirements

- Ansible >= 2.16
- `containers.podman`, `ansible.posix`, and `community.general` collections on the
  controller (declared as collection dependencies in `galaxy.yml`)
- Fedora Server with Podman >= 4.4 (Quadlet support) and the rootful Podman socket
  available at `/run/podman/podman.sock` (`podman.socket` enabled)
- A Traefik instance attached to the `proxy_network` Podman network (Quadlet name
  `systemd-proxy_network`) with a `cloudflare` TLS cert resolver — see
  `danmwallace.podman.traefik`

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `arcane_hostname` | str | yes | — | Public hostname for Arcane (e.g. `arcane.example.com`). Used for `APP_URL` and the Traefik routing rule. |
| `arcane_postgres_password` | str | yes | — | Postgres password for `arcane_postgres_user`. **Supply from vault.** |
| `arcane_encryption_key` | str | yes | — | Encryption key used by Arcane for at-rest secret encryption. **Supply from vault.** |
| `arcane_jwt_secret` | str | yes | — | JWT signing secret for Arcane session tokens. **Supply from vault.** |
| `arcane_version` | str | no | `v2.10.2` | Arcane image tag (e.g. `v2.10.2`). |
| `arcane_socket_proxy_version` | str | no | `v0.5.0` | Image tag for the `ghcr.io/tecnativa/docker-socket-proxy` sidecar that mediates Arcane's access to the Podman socket. |
| `arcane_data_dir` | str | no | `/opt/podman/arcane` | Host directory for Arcane persistent data. Postgres data is stored under a `postgres/` subdirectory. |
| `arcane_postgres_db` | str | no | `arcane` | Name of the Postgres database created for Arcane. |
| `arcane_postgres_user` | str | no | `arcane` | Postgres username Arcane connects with. |

`arcane_hostname` has a placeholder default of `arcane.example.com` in
`defaults/main.yml` but is declared required in `argument_specs.yml`; always set it.
The three secret variables default to empty strings and the role asserts they are
non-empty before doing anything.

## Dependencies

None declared in `meta/main.yml`. In practice the target host needs Podman with the
rootful socket enabled and an existing `proxy_network` Quadlet network, both of
which `danmwallace.podman.traefik` provides.

## Example Playbook

```yaml
- hosts: util_servers
  become: true
  roles:
    - role: danmwallace.podman.arcane
      vars:
        arcane_hostname: arcane.example.com
        arcane_postgres_password: "{{ vault_arcane_postgres_password }}"
        arcane_encryption_key: "{{ vault_arcane_encryption_key }}"
        arcane_jwt_secret: "{{ vault_arcane_jwt_secret }}"
```

## What the Role Does

1. Asserts `arcane_postgres_password`, `arcane_encryption_key`, and
   `arcane_jwt_secret` are all non-empty (with `no_log`).
2. Ensures `arcane_data_dir` and `arcane_data_dir/postgres` exist (0755).
3. Writes the `arcane` Quadlet network unit to
   `/etc/containers/systemd/arcane.network`.
4. Writes the `arcane-socket` Quadlet network unit
   (`/etc/containers/systemd/arcane-socket.network`) with `Internal=true`.
5. Renders `arcane-postgres.container` (Postgres `17.11-alpine`, on the `arcane`
   network, data volume at `arcane_data_dir/postgres`).
6. Renders `arcane-socket-proxy.container` (`docker-socket-proxy`, on the
   `arcane-socket` network, socket mounted `:ro,z`, API allowlist as environment).
7. Renders `arcane.container` (on `arcane`, `arcane-socket`, and `proxy_network`;
   `Requires=`/`After=` the socket proxy; `DOCKER_HOST=tcp://arcane-socket-proxy:2375`;
   Traefik labels).
8. Runs `daemon-reload`, then enables and starts `arcane-postgres.service`.
9. Runs `daemon-reload`, then enables and starts `arcane-socket-proxy.service`.
10. Enables and starts `arcane.service`.

`Restart arcane-postgres`, `Restart arcane-socket-proxy`, and `Restart arcane`
handlers fire when their respective unit file changes, each doing a `daemon-reload`
so Quadlet regenerates the service before restarting it.

## Notes

- **Socket-proxy allowlist.** The proxy enables `CONTAINERS`, `IMAGES`, `NETWORKS`,
  `VOLUMES`, `SERVICES`, `TASKS`, `INFO`, `VERSION`, and `POST`; it disables `BUILD`,
  `AUTH`, `SECRETS`, and `SWARM`, and leaves `EXEC` at its default of `0`. As a
  result, Arcane's container **exec/console feature is not available** through this
  deployment — that is deliberate. To change the allowlist, edit
  `templates/arcane-socket-proxy.container.j2`.
- **SELinux.** The proxy unit sets `SecurityLabelDisable=true` (it runs as `spc_t`,
  like the `traefik` unit) because a confined `container_t` process is denied
  `connectto` on the `container_runtime_t` Podman socket. Arcane itself stays confined;
  only the small HAProxy proxy is unconfined, and its allowlist is the access control.
- `arcane.container` declares `Requires=arcane-socket-proxy.service`, so stopping
  the proxy stops Arcane too; starting Arcane pulls the proxy up first.
- The `arcane-socket` network is `Internal=true`: containers on it have no external
  connectivity, and only Arcane and the proxy are attached. The proxy is reachable
  from nowhere else.
- All three handlers suppress the `Could not find the requested service` systemd
  error that fires in Molecule (where `daemon-reload` is skipped via
  `molecule-notest` tags and the Quadlet units are never registered). Any other
  failure is still surfaced.
- The Traefik label `traefik.docker.network=systemd-proxy_network` uses the
  Quadlet-generated network name (Quadlet prefixes `.network` units with
  `systemd-`), which is what the Traefik provider sees via the Podman socket.
- `arcane-postgres` is only reachable on the `arcane` network; it is not attached
  to `proxy_network` and publishes no host ports.

## License

MIT
