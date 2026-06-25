# danmwallace.podman.grimmory

Deploys [Grimmory](https://github.com/grimmory-tools/grimmory), a self-hosted eBook library, and a [MariaDB 11](https://mariadb.org/) database as a pair of rootful Podman Quadlet units on Fedora. An NFS share is mounted on the host and bind-mounted into the Grimmory container as the books volume (`/app/books`). Traefik handles TLS termination via the Cloudflare cert resolver; the Grimmory container joins both the role-private `grimmory` network and the shared `proxy_network` Quadlet network used by Traefik.

Host data directories (app data, bookdrop, and the MariaDB data volume) are created under `grimmory_data_dir` (default `/opt/podman/grimmory`). The MariaDB container is confined to the private `grimmory` network only and is not reachable from `proxy_network`.

## Requirements

- Ansible >= 2.16
- Collections: `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`
- Target host: Fedora with Podman installed and the `proxy_network` Quadlet network already up (the `danmwallace.podman.traefik` role creates it)
- NFS client packages installed on the target host and the NFS server reachable at deploy time
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
| `grimmory_image_tag` | str | no | `latest` | Grimmory image tag. Pin to a release tag in production. |
| `grimmory_db_image` | str | no | `docker.io/library/mariadb` | MariaDB container image. |
| `grimmory_db_image_tag` | str | no | `11` | MariaDB image tag. |
| `grimmory_data_dir` | str | no | `/opt/podman/grimmory` | Host base directory for Grimmory data, bookdrop, and MariaDB volumes. |
| `grimmory_nfs_mountpoint` | str | no | `/mnt/nfs/books` | Host path where the NFS books share is mounted. |
| `grimmory_app_uid` | int | no | `1000` | UID the Grimmory container process runs as (`APP_USER_ID`). |
| `grimmory_app_gid` | int | no | `1000` | GID the Grimmory container process runs as (`APP_GROUP_ID`). |
| `grimmory_timezone` | str | no | `America/New_York` | Timezone passed to the container as the `TZ` env var. |
| `grimmory_db_name` | str | no | `grimmory` | MariaDB database name. |
| `grimmory_db_user` | str | no | `grimmory` | MariaDB application user. |
| `grimmory_traefik_network` | str | no | `systemd-proxy_network` | Podman network shared with Traefik (used in `traefik.docker.network` label). |

## Dependencies

None declared in `meta/main.yml`. In practice the target host needs:

- The `proxy_network` Podman network (created by `danmwallace.podman.traefik`)
- NFS client tooling and a reachable NFS server before the mount task runs

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

1. Creates the base data directories — `grimmory_data_dir`, `data/`, `bookdrop/`, and `db/` — with mode `0755`.
2. Creates the NFS mount point at `grimmory_nfs_mountpoint` (default `/mnt/nfs/books`) with mode `0755`.
3. Mounts the NFS books share (`grimmory_nfs_server:grimmory_nfs_path`) at `grimmory_nfs_mountpoint` using `fstype: nfs4` and `opts: defaults,_netdev,nofail`.
4. Deploys the `grimmory.network` Quadlet network unit to `/etc/containers/systemd/grimmory.network`.
5. Renders `grimmory-db.container.j2` to `/etc/containers/systemd/grimmory-db.container`. Changes here trigger the `Restart grimmory-db` handler.
6. Enables and starts `grimmory-db.service` via systemd with `daemon_reload: true`.
7. Renders `grimmory.container.j2` to `/etc/containers/systemd/grimmory.container`. Changes here triggers the `Restart grimmory` handler.
8. Enables and starts `grimmory.service` via systemd with `daemon_reload: true`.

The `Restart grimmory-db` handler calls `systemctl restart grimmory-db.service` with `daemon_reload: true` when the database Quadlet unit changes. The `Restart grimmory` handler does the same for `grimmory.service`.

## Notes

**NFS `nofail` behaviour:** The NFS mount uses `opts: defaults,_netdev,nofail`. This means a missing or unreachable NFS server will not hang boot, but Grimmory itself will fail to start — the `grimmory.service` unit declares `Requires=remote-fs.target`, so if the NFS mount is absent the books volume bind-mount into the container will be empty or missing.

**`DATABASE_URL` format:** The Grimmory container receives `DATABASE_URL=jdbc:mariadb://grimmory-db:3306/{{ grimmory_db_name }}`. This is a JDBC connection string, not a plain `mysql://` URL. If Grimmory fails to connect to the database on the first deploy, verify this format against the upstream `docker-compose.yml` — the expected scheme may have changed between releases.

## License

MIT
