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
| `arcane_hostname` | str | yes | — | Public hostname for Arcane (e.g. `arcane.example.com`). Used for `ARCANE_APP_URL` and the Traefik routing rule. |
| `arcane_postgres_password` | str | yes | — | Postgres password for `arcane_postgres_user`. **Supply from vault.** |
| `arcane_encryption_key` | str | yes | — | Encryption key (`ARCANE_ENCRYPTION_KEY`) used by Arcane for at-rest secret encryption. At least 32 characters, or a `hex:`/`base64:` encoded 32-byte key. **Supply from vault**, and keep the value 2.x used. |
| `arcane_jwt_secret` | str | no | `""` | **Deprecated, ignored.** Arcane 3.x signs sessions with its own key. Still accepted so existing inventories pass. |
| `arcane_version` | str | no | `v3.1.1` | Image tag for `ghcr.io/getarcaneapp/manager`. Must be `v3.0.0` or newer. |
| `arcane_socket_proxy_version` | str | no | `3.4@sha256:027f9fa5ee70be5836eeaa10ce889d7a83f34a8db16a7f412818b92997e0beab` | What follows `ghcr.io/tecnativa/docker-socket-proxy:` for the sidecar that mediates Arcane's access to the Podman socket: a tag or `tag@sha256:<digest>`. Upstream stopped versioned tags at `v0.5.0` and rebuilds `3.4` (HAProxy 3.4) weekly, so the default pins `3.4` to its multi-arch index digest. |
| `arcane_data_dir` | str | no | `/opt/podman/arcane` | Host directory for Arcane persistent data. Postgres data is stored under a `postgres/` subdirectory. |
| `arcane_postgres_db` | str | no | `arcane` | Name of the Postgres database created for Arcane. |
| `arcane_postgres_user` | str | no | `arcane` | Postgres username Arcane connects with. |

`arcane_hostname` has a placeholder default of `arcane.example.com` in
`defaults/main.yml` but is declared required in `argument_specs.yml`; always set it.
`arcane_postgres_password` and `arcane_encryption_key` default to empty strings; the
role asserts the password is non-empty and the key is long enough for 3.x before doing
anything.

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
```

## Upgrading from Arcane 2.x

The role renders a 3.x-only Quadlet unit: the image is `ghcr.io/getarcaneapp/manager`
(3.x removed the GHCR `arcane` alias) and every Arcane variable carries the `ARCANE_`
prefix. 3.x refuses to start if an unprefixed 2.x name is set, or if the database was
not first migrated by 2.17.x. Upstream guide:
<https://getarcane.app/docs/get-started/migrate-v3>.

1. **Run v2.17.3 once.** With collection 0.6.x (the 2.x template), set
   `arcane_version: v2.17.3`, deploy, and wait until Arcane is up. Older databases stop
   3.x with `upgrade to Arcane v2.17.1 first`.
2. **Resolve job runs marked "Needs attention".** 3.x removes "Resolve after review".
3. **Back up.** 3.x replaces its SQL migrations with one-way Goose migrations, so a
   restore is the only way back to 2.x. This role mounts no `/app/data` volume, so
   nothing there survives a restart anyway; the database dump plus the old unit file is
   the backup:

   ```sh
   sudo podman exec arcane-postgres pg_dump -U arcane arcane > arcane-$(date +%F).sql
   sudo cp /etc/containers/systemd/arcane.container arcane.container.2x
   ```

4. **Check `arcane_encryption_key`.** Keep the value 2.x used (it decrypts stored
   credentials). If it is shorter than 32 characters, 3.x refuses to start and the role
   fails first with an assert. Changing the key means Arcane can no longer decrypt what
   2.x stored with the old one, so plan to re-enter stored registry, Git and OIDC
   credentials, and do not upgrade until you have decided.
5. **Deploy this role version.** `arcane_jwt_secret` can stay in the inventory; the role
   ignores it. The `Restart arcane` handler restarts the unit; if
   `sudo journalctl -u arcane` shows `rename X to ARCANE_X`, a 2.x variable is still set.
6. **Afterwards:** set up notification providers again under System → Notifications
   (they are now global to the Manager), review custom roles (permissions were renamed;
   the built-in Deployer role loses `containers:update`), and update any scripts that call
   `/api/environments` (now `/api/agents`) or use six-field cron schedules (now
   five-field, converted automatically).

## What the Role Does

1. Asserts `arcane_version` is `v3.0.0` or newer, then (with `no_log`) that
   `arcane_postgres_password` is non-empty and `arcane_encryption_key` is at least 32
   characters or a `hex:`/`base64:` key.
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

- **Postgres data directory** is created `0700` and its ownership is left to `initdb`
  (uid 999); the postgres entrypoint runs `chmod 0700` on every start, so any other mode
  would show as a change on every run.
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
