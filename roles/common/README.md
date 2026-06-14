# danmwallace.podman.common

Configures the baseline system state for a Fedora Server host that will run
Podman-based homelab services. The role installs Podman, Buildah, Skopeo, and
supporting Python bindings; ensures firewalld is running; sets the
`container_manage_cgroup` SELinux boolean; creates system users with `wheel`
membership and a passwordless-sudo sudoers entry for the `ansible` service
account; and creates the `/etc/containers/systemd` Quadlet directory with
`podman.socket` enabled. It is scoped to Fedora Server only — Atomic variants
(IoT, CoreOS, Silverblue, Kinoite) are not supported.

On KVM guests the role additionally installs and starts `qemu-guest-agent`,
conditional on the virtio channel (`/dev/virtio-ports/org.qemu.guest_agent.0`)
being present. Cockpit with the `cockpit-podman` plugin is installed and
socket-activated when `common_cockpit_enabled: true`.

## Requirements

- Ansible >= 2.16
- Collections: `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`,
  `community.general >= 8.0.0`
- Target host: Fedora Server (not an Atomic variant); SELinux enabled or
  permissive (the SELinux task skips when SELinux is disabled)

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `common_timezone` | str | no | `America/New_York` | Timezone to set on the host, passed to `community.general.timezone`. |
| `common_cockpit_enabled` | bool | no | `false` | Install and enable Cockpit and cockpit-podman. |
| `common_users` | list of dict | no | `[{name: ansible, groups: [wheel]}, {name: dwallace, groups: [wheel]}]` | Users to create. Each entry requires `name` (str) and `groups` (list of str). |

## Dependencies

None declared in `meta/main.yml`. The collection-level `galaxy.yml` requires
`containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, and
`community.general >= 8.0.0` — install them before running this role.

## Example Playbook

```yaml
- hosts: podman_hosts
  become: true
  roles:
    - role: danmwallace.podman.common
      vars:
        common_timezone: America/New_York
        common_cockpit_enabled: true
        common_users:
          - name: ansible
            groups:
              - wheel
          - name: dwallace
            groups:
              - wheel
```

## What the Role Does

1. **Validate arguments** — checks caller-supplied vars against `argument_specs.yml` and fails fast on type errors.
2. **Set hostname** — applies `inventory_hostname` via `systemd` strategy using `ansible.builtin.hostname`.
3. **Install packages** — installs `podman`, `buildah`, `skopeo`, `python3-podman`, and `container-selinux` via dnf (Fedora only); installs `qemu-guest-agent` on KVM guests.
4. **Configure firewalld** — installs `firewalld` and ensures the service is enabled and started.
5. **Set SELinux boolean** — enables `container_manage_cgroup` persistently (skipped when SELinux is disabled).
6. **Create users** — ensures each entry in `common_users` exists with the correct supplementary groups and `/bin/bash` shell; writes `/etc/sudoers.d/ansible` granting the `ansible` account passwordless sudo (validated with `visudo`).
7. **Enable qemu-guest-agent** (KVM guests only) — enables the unit, checks for the virtio-ports channel, and starts the agent only if the channel device exists.
8. **Cockpit** (when `common_cockpit_enabled: true`) — installs `cockpit` and `cockpit-podman`, then enables and starts `cockpit.socket`.
9. **Quadlet directory** — creates `/etc/containers/systemd` (mode `0755`, owned `root:root`) and enables and starts `podman.socket`.

## Notes

- The `common_users` task appends groups rather than replacing them (`append: true`), so existing group memberships on the host are preserved.
- SSH public keys are **not** deployed by this role; use a separate authorized-key task if needed.
- `qemu-guest-agent` is only started if `/dev/virtio-ports/org.qemu.guest_agent.0` exists, preventing failures on hosts where the virtio channel is not yet attached.
- All package and service tasks are guarded by `ansible_facts['distribution'] == 'Fedora'`; the role will skip silently on other distributions rather than fail.

## License

MIT
