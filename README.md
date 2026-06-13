# danmwallace.podman

Ansible collection for Fedora Server homelab hosts running rootful Podman with systemd Quadlets.

## Roles

| Role | Description |
|------|-------------|
| `common` | Base Fedora Server configuration: packages, firewalld, SELinux, users, Podman socket, Quadlet directory |

## Requirements

- Ansible >= 2.16
- Fedora Server (Atomic variants not supported)
- Collections: `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, `community.general >= 8.0.0`

## Usage

```yaml
- hosts: fedora_vms
  roles:
    - role: danmwallace.podman.common
      vars:
        podman_common_timezone: "America/New_York"
```

## License

MIT
