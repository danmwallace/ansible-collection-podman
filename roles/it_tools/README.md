# danmwallace.podman.it_tools

Deploys [IT-Tools](https://github.com/CorentinTh/it-tools) — a collection of developer and network utility functions — as a rootful Podman Quadlet on Fedora Server. The container runs from `docker.io/corentinth/it-tools:latest` and is managed by systemd via a Quadlet unit written to `/etc/containers/systemd/`.

The service is placed on the `proxy_network` Podman network and exposed through Traefik via container labels. Traefik terminates TLS using the `cloudflare` cert resolver and routes requests for `it_tools_hostname` to the container on port 80. No ports are published directly to the host.

## Requirements

- Fedora Server with Podman and systemd-container support (Quadlet).
- A running Traefik instance attached to the `proxy_network` Podman network.
- Ansible 2.16 or later.
- The `containers.podman` (>=1.11.0), `ansible.posix` (>=1.5.0), and `community.general` (>=8.0.0) collections must be present (declared as collection-level dependencies in `galaxy.yml`).

## Role Variables

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `it_tools_hostname` | str | yes | `it-tools.example.com` | Hostname for the IT-Tools web interface, used in the Traefik router rule. |
| `it_tools_data_dir` | str | no | `/opt/podman/it-tools` | Host directory created for IT-Tools data files. |

## Dependencies

None. Collection-level dependencies (`containers.podman`, `ansible.posix`, `community.general`) are declared in the collection's `galaxy.yml`.

## Example Playbook

```yaml
- name: Deploy IT-Tools
  hosts: util_servers
  roles:
    - role: danmwallace.podman.it_tools
      vars:
        it_tools_hostname: it-tools.home.example.com
```

## What the Role Does

1. Creates the data directory (`it_tools_data_dir`) on the host with mode `0755`.
2. Renders the Quadlet unit template to `/etc/containers/systemd/it-tools.container`, notifying the `Restart it-tools` handler if the file changes.
3. Reloads the systemd daemon and enables and starts `it-tools.service`.

When the handler fires, systemd reloads its daemon and restarts `it-tools.service`.

## Notes

- The Quadlet unit pulls `it-tools:latest` on every fresh container creation. Pin to a digest in the template if you need reproducible deploys.
- The handler suppresses the `Could not find the requested service` error in Molecule test environments, where the Quadlet unit is never loaded. Any other restart failure still surfaces normally.
- The `Enable and start it-tools.service` task and the handler are both tagged `molecule-notest` so Molecule skips the actual systemd calls during testing.

## License

MIT
