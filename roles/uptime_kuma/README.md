# danmwallace.podman.uptime_kuma

Deploys [Uptime Kuma](https://github.com/louislam/uptime-kuma) — a self-hosted uptime monitoring dashboard — as a rootful Podman Quadlet on Fedora Server. The container runs from `docker.io/louislam/uptime-kuma:1` and is managed by systemd via a Quadlet unit written to `/etc/containers/systemd/`.

The service is placed on the `proxy_network` Podman network and exposed through Traefik via container labels. Traefik terminates TLS using the `cloudflare` cert resolver and routes requests for `uptime_kuma_hostname` to the container on port 3001. No ports are published directly to the host. Persistent data is stored in `uptime_kuma_data_dir` on the host, mounted at `/app/data` inside the container.

## Requirements

- Fedora Server with Podman and systemd-container support (Quadlet).
- A running Traefik instance attached to the `proxy_network` Podman network.
- Ansible 2.16 or later.
- The `containers.podman` (>=1.11.0), `ansible.posix` (>=1.5.0), and `community.general` (>=8.0.0) collections must be present (declared as collection-level dependencies in `galaxy.yml`).

## Role Variables

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `uptime_kuma_hostname` | str | yes | `uptime-kuma.example.com` | Hostname for the Uptime Kuma web interface, used in the Traefik router rule. |
| `uptime_kuma_data_dir` | str | no | `/opt/podman/uptime-kuma` | Host directory mounted at `/app/data` for persistent storage. |
| `uptime_kuma_image` | str | no | `docker.io/louislam/uptime-kuma:1` | Container image. Pin to a digest or specific tag for reproducible deploys. |

## Dependencies

None. Collection-level dependencies (`containers.podman`, `ansible.posix`, `community.general`) are declared in the collection's `galaxy.yml`.

## Example Playbook

```yaml
- name: Deploy Uptime Kuma
  hosts: util_servers
  roles:
    - role: danmwallace.podman.uptime_kuma
      vars:
        uptime_kuma_hostname: uptime.home.example.com
```

## What the Role Does

1. Creates the data directory (`uptime_kuma_data_dir`) on the host with mode `0755`.
2. Renders the Quadlet unit template to `/etc/containers/systemd/uptime-kuma.container`, notifying the `Restart uptime-kuma` handler if the file changes.
3. Reloads the systemd daemon and enables and starts `uptime-kuma.service`.

When the handler fires, systemd reloads its daemon and restarts `uptime-kuma.service`.

## Notes

- The `:1` image tag tracks the latest stable 1.x release. Pin to a specific patch version or digest if you need reproducible deploys.
- The handler suppresses the `Could not find the requested service` error in Molecule test environments, where the Quadlet unit is never loaded. Any other restart failure still surfaces normally.
- The `Enable and start uptime-kuma.service` task and the handler are both tagged `molecule-notest` so Molecule skips the actual systemd calls during testing.

## License

MIT
