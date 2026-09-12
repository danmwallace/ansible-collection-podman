# danmwallace.podman.grimmory

Deploys [Grimmory](https://github.com/grimmory-tools/grimmory), a self-hosted eBook library, and a [MariaDB](https://mariadb.org/) database as a pair of rootful Podman Quadlet units on Fedora. Grimmory runs `ghcr.io/grimmory-tools/grimmory:{{ grimmory_image_tag }}` (default `v3.3.3`) and MariaDB runs `docker.io/library/mariadb:{{ grimmory_db_image_tag }}` (default `11.8.9`). An NFS share is mounted on the host at `grimmory_nfs_mountpoint`; the container's library volume is the local `{{ grimmory_data_dir }}/books` directory, mounted at `/books`. Traefik terminates TLS via the Cloudflare cert resolver and routes `grimmory_hostname` to the container on port 6060 (Grimmory's default `SERVER_PORT`).

The Grimmory container joins both the role-private `grimmory` Quadlet network and the shared `proxy_network` used by Traefik. The MariaDB container is confined to the private `grimmory` network only and is not reachable from `proxy_network`. Host data directories (app data, books, bookdrop, and the MariaDB data volume) are created under `grimmory_data_dir` (default `/opt/podman/grimmory`).

## Requirements

- Ansible >= 2.16
- Collections: `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0` (declared in the collection's `galaxy.yml`)
- Target host: Fedora with Podman installed and the `proxy_network` Quadlet network already up (the `danmwallace.podman.traefik` role creates it)
- The NFS server reachable at deploy time (the role installs `nfs-utils` itself)
- A Cloudflare TLS cert resolver configured in Traefik (for HTTPS)

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `grimmory_hostname` | str | yes | — | Hostname for the Grimmory web interface (e.g. `books.wallace.boston`). |
| `grimmory_db_password` | str | yes | — | MariaDB password for the grimmory application user. **Supply from vault.** |
| `grimmory_db_root_password` | str | yes | — | MariaDB root password. **Supply from vault.** |
| `grimmory_nfs_server` | str | yes | — | NFS server hostname or IP (e.g. `10.10.99.3`). |
| `grimmory_nfs_path` | str | yes | — | Exported path on the NFS server (e.g. `/mnt/ssd-mirror/books`). |
| `grimmory_image` | str | no | `ghcr.io/grimmory-tools/grimmory` | Grimmory container image. |
| `grimmory_image_tag` | str | no | `v3.3.3` | Grimmory image tag. Pin to a release tag in production. |
| `grimmory_db_image` | str | no | `docker.io/library/mariadb` | MariaDB container image. |
| `grimmory_db_image_tag` | str | no | `11.8.9` | MariaDB image tag. |
| `grimmory_data_dir` | str | no | `/opt/podman/grimmory` | Host base directory for Grimmory data, books, bookdrop, and MariaDB volumes. |
| `grimmory_nfs_mountpoint` | str | no | `/mnt/nfs/books` | Host path where the NFS books share is mounted. |
| `grimmory_app_uid` | int | no | `1000` | UID the Grimmory container process runs as (`APP_USER_ID`). |
| `grimmory_app_gid` | int | no | `1000` | GID the Grimmory container process runs as (`APP_GROUP_ID`). |
| `grimmory_timezone` | str | no | `America/New_York` | Timezone passed to the container as the `TZ` env var. |
| `grimmory_db_name` | str | no | `grimmory` | MariaDB database name. |
| `grimmory_db_user` | str | no | `grimmory` | MariaDB application user. |
| `grimmory_db_uid` | int | no | `999` | Host UID that owns the MariaDB data directory (`db/`). Must match the `mysql` user inside the image; the entrypoint chowns the directory to it on every start. |
| `grimmory_traefik_network` | str | no | `systemd-proxy_network` | Podman network shared with Traefik (used in the `traefik.docker.network` label). |

## Dependencies

None declared in `meta/main.yml`. In practice the target host needs:

- The `proxy_network` Podman network (created by `danmwallace.podman.traefik`)
- A reachable NFS server before the mount task runs

## Example Playbook

```yaml
- hosts: util
  become: true
  roles:
    - role: danmwallace.podman.grimmory
      vars:
        grimmory_hostname: books.wallace.boston
        grimmory_nfs_server: 10.10.99.3
        grimmory_nfs_path: /mnt/ssd-mirror/books
        grimmory_db_password: "{{ vault_grimmory_db_password }}"
        grimmory_db_root_password: "{{ vault_grimmory_db_root_password }}"
```

## What the Role Does

1. Creates the data directories — `grimmory_data_dir`, `data/`, `books/`, `bookdrop/`, and `db/` — with mode `0755`. `data/`, `books/`, and `bookdrop/` are owned by `grimmory_app_uid`; the rest by root.
2. Ensures `nfs-utils` is installed.
3. Creates the NFS mount point at `grimmory_nfs_mountpoint` (default `/mnt/nfs/books`) with mode `0755`.
4. Mounts the NFS books share (`grimmory_nfs_server:grimmory_nfs_path`) at `grimmory_nfs_mountpoint` using `fstype: nfs4` and `opts: defaults,_netdev,nofail`.
5. Deploys the `grimmory.network` Quadlet network unit to `/etc/containers/systemd/grimmory.network`.
6. Renders `grimmory-db.container.j2` to `/etc/containers/systemd/grimmory-db.container`. Changes trigger the `Restart grimmory-db` handler.
7. Enables and starts `grimmory-db.service` via systemd with `daemon_reload: true`.
8. Renders `grimmory.container.j2` to `/etc/containers/systemd/grimmory.container`. Changes trigger the `Restart grimmory` handler.
9. Enables and starts `grimmory.service` via systemd with `daemon_reload: true`.

The `Restart grimmory-db` handler runs `systemctl restart grimmory-db.service` with `daemon_reload: true` when the database Quadlet unit changes; `Restart grimmory` does the same for `grimmory.service`.

## Notes

- **Data directory ownership.** `db/` is owned by `grimmory_db_uid` (999) and the app
  directories by `grimmory_app_uid`; managing them any other way makes the play report a
  change on every run because the containers reset ownership at start.
- **Container env names.** The unit passes `DATABASE_USERNAME`, `DATABASE_PASSWORD`,
  `USER_ID` and `GROUP_ID`, the names upstream reads (earlier releases used `DB_USER`,
  `DB_PASSWORD`, `APP_USER_ID`, `APP_GROUP_ID`, which Grimmory ignores).
**Listen port.** Grimmory 3.3.0 renamed the listen-port env var from `BOOKLORE_PORT` to `SERVER_PORT` (the old name still works as a fallback). The default is unchanged at `6060`, which is what the Traefik `loadbalancer.server.port` label assumes, so the role sets neither variable. If you ever set `SERVER_PORT` in the unit, change the label to match.

**MariaDB health check.** The `grimmory-db` unit uses the official image's `healthcheck.sh --connect --innodb_initialized` probe. MariaDB 11.x images no longer ship the `mysql*` compatibility symlinks, so a `mysqladmin ping` health command reports `not found` and leaves the container permanently unhealthy. `--connect` authenticates as the unprivileged `healthcheck@localhost` user the image creates when it initialises the data directory, so no password appears on the command line. A data directory initialised by a pre-2023 image (before that user existed) would need the user created by hand.

**NFS `nofail` behaviour.** The NFS mount uses `opts: defaults,_netdev,nofail`, so an unreachable NFS server will not hang boot. The `grimmory.service` unit declares `Requires=remote-fs.target` so it waits for the mount, but the container's `/books` volume is the local `{{ grimmory_data_dir }}/books` directory, not the NFS mountpoint — copy or sync from `grimmory_nfs_mountpoint` into it.

**Environment variables consumed upstream.** At v3.3.3 Grimmory's `application.yaml` reads `DATABASE_URL`, `DATABASE_USERNAME`, and `DATABASE_PASSWORD`, and the image entrypoint reads `USER_ID` / `GROUP_ID`. The role's `DB_USER`, `DB_PASSWORD`, `APP_USER_ID`, and `APP_GROUP_ID` env vars are therefore not read by the container; the database credentials take effect through the `?user=…&password=…` query string on the JDBC `DATABASE_URL`, and the process runs as upstream's default UID/GID `1000`, which matches the role defaults. Changing `grimmory_app_uid`/`grimmory_app_gid` alters directory ownership on the host but not the UID inside the container. This is unchanged between v3.2.4 and v3.3.3.

## License

MIT
