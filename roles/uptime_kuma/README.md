# danmwallace.podman.uptime_kuma

Deploys [Uptime Kuma](https://github.com/louislam/uptime-kuma) — a self-hosted uptime monitoring dashboard — as a rootful Podman Quadlet on Fedora Server. The container runs `docker.io/louislam/uptime-kuma:2.5.3` by default and is managed by systemd via a Quadlet unit written to `/etc/containers/systemd/uptime-kuma.container`.

The service joins the `proxy_network` Podman network and is exposed through Traefik via container labels. Traefik terminates TLS using the `cloudflare` cert resolver and routes requests for `uptime_kuma_hostname` to the container on port 3001. No ports are published directly to the host. Persistent data (the SQLite database `kuma.db`, `db-config.json`, and uploads) lives in `uptime_kuma_data_dir` on the host, mounted at `/app/data` inside the container.

## Requirements

- Fedora Server with Podman and systemd-container support (Quadlet).
- A running Traefik instance attached to the `proxy_network` Podman network, with the `cloudflare` cert resolver configured.
- Ansible >= 2.16.
- The `containers.podman` (>=1.11.0), `ansible.posix` (>=1.5.0), and `community.general` (>=8.0.0) collections, declared as collection-level dependencies in `galaxy.yml`.

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `uptime_kuma_hostname` | str | yes | `uptime-kuma.example.com` | Hostname for the Uptime Kuma web interface, used in the Traefik router rule. |
| `uptime_kuma_data_dir` | str | no | `/opt/podman/uptime-kuma` | Host directory mounted at `/app/data` for persistent storage. |
| `uptime_kuma_image` | str | no | `docker.io/louislam/uptime-kuma:2.5.3` | Container image. Pin to a digest or specific tag for reproducible deploys. |

`uptime_kuma_hostname` has a placeholder default so the role renders in isolation; always override it.

## Dependencies

None declared in `meta/main.yml`. In practice the target host needs the `proxy_network` Podman network (created by `danmwallace.podman.traefik`).

## Example Playbook

```yaml
- name: Deploy Uptime Kuma
  hosts: util_servers
  become: true
  roles:
    - role: danmwallace.podman.uptime_kuma
      vars:
        uptime_kuma_hostname: uptime.home.example.com
```

## What the Role Does

1. Creates the data directory (`uptime_kuma_data_dir`) on the host with mode `0755`, owned by UID/GID `1000` (override with `uptime_kuma_data_owner`).
2. Renders the Quadlet unit template to `/etc/containers/systemd/uptime-kuma.container` (mode `0644`), notifying the `Restart uptime-kuma` handler if the file changes.
3. Reloads the systemd daemon and enables and starts `uptime-kuma.service`.

The `Restart uptime-kuma` handler runs `systemctl restart uptime-kuma.service` with `daemon_reload: true` when the unit changes.

## Upgrading from 1.x to 2.x

Uptime Kuma 2.0 is a major release that rewrites the on-disk database. The role's default image moved from `1.23.16` straight to `2.5.3`; the upstream [migration guide](https://github.com/louislam/uptime-kuma/wiki/Migration-From-v1-To-v2) applies to that jump. What to expect:

- **Back up the data directory first.** Stop the service, then archive `uptime_kuma_data_dir` before re-running the role with the new image:

  ```bash
  sudo systemctl stop uptime-kuma.service
  sudo tar -C /opt/podman -czf /root/uptime-kuma-pre-v2-$(date +%F).tgz uptime-kuma
  ```

  Backing up the data directory is the only supported backup method; the 1.x JSON backup/restore feature was removed in 2.0.
- **Migration is one-way.** 2.x rewrites the heartbeat history into new aggregate tables and records the schema state in the database. A 1.x image cannot read the result, so the only rollback is to restore the backup and pin `uptime_kuma_image` back to `docker.io/louislam/uptime-kuma:1.23.16`.
- **Existing SQLite data is migrated in place.** On first start, 2.x finds `kuma.db` in `/app/data`, writes a `db-config.json` (`type: sqlite`) beside it, and then runs the aggregate-table migration. No new environment variable, volume, or port is required; the role's unit is unchanged apart from the image tag. Do not use the `-rootless` image variants for the upgrade — upstream warns they fail to start against 1.x data.
- **First start takes a while and must not be interrupted.** While the migration runs, port 3001 serves a plain progress page instead of the dashboard, and the container log prints `[DON'T STOP] Migrating monitor ...` lines. Upstream quotes ~7 minutes for 20 monitors with 90 days of history, and hours for larger installs. Watch it with `journalctl -fu uptime-kuma.service` or `podman logs -f uptime-kuma`. If the container is stopped mid-migration it will refuse to start again (`Aggregate table migration is already in progress`) — restore from backup and retry.
- **Minimum source version.** Upstream does not state a minimum 1.x release; 2.x first applies any outstanding 1.x schema patches and then the 2.x migrations, so any 1.x database is expected to migrate. The role was on 1.23.16, the final 1.x release, which is the path upstream tested.
- **Behaviour changes after the upgrade** that may affect existing setups: badge endpoints (`/api/badge/:id/uptime/:duration`) accept only `24`, `24h`, `30d`, `1y`-style durations; SMTP notification subject/body templating switched to LiquidJS (variables are case-sensitive); the DNS-cache option for HTTP monitors was removed; newly created monitors default to 0 retries instead of 1.

## Notes

- The handler suppresses the `Could not find the requested service` error in Molecule test environments, where the Quadlet unit is never loaded. Any other restart failure still surfaces normally.
- The `Enable and start uptime-kuma.service` task and the handler are both tagged `molecule-notest` so Molecule skips the actual systemd calls during testing.

## License

MIT
