# Plan: [INFRA][P2] Containerd Cleanup

## Summary

- SSH to prod, investigate containerd usage (DO droplet agent dependency)
- Clean 51GB old snapshots if safe
- Reduce disk usage from 71% to <60%

## Implementation Steps

1. **SSH to prod** - `ssh root@139.59.201.65`

2. **Check containerd status** - Determine if in active use:
   ```bash
   systemctl status containerd
   systemctl is-enabled containerd
   ps aux | grep containerd
   ```

3. **Identify DO droplet agent dependency** - Check if agent uses containerd:
   ```bash
   dpkg -l | grep digitalocean
   systemctl status droplet-agent
   cat /etc/droplet-agent/config.yaml
   ```

4. **Inventory containerd snapshots**:
   ```bash
   du -sh /var/lib/containerd/
   du -sh /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/
   ls -la /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/
   ```

5. **If containerd NOT in use** (no running containers, agent doesn't depend on it):
   - Stop containerd: `systemctl stop containerd`
   - Disable containerd: `systemctl disable containerd`
   - Remove snapshots: `rm -rf /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/*`
   - Optionally remove containerd entirely: `apt remove containerd.io` (if not needed)

6. **If containerd IS in use** (DO agent depends on it):
   - Use containerd's built-in garbage collection:
     ```bash
     ctr -n k8s.io images ls
     ctr -n k8s.io snapshots ls
     ctr -n k8s.io snapshots rm <unused-snapshot-ids>
     ```
   - Or prune via crictl if available: `crictl rmi --prune`

7. **Verify disk usage after cleanup**:
   ```bash
   df -h /
   du -sh /var/lib/containerd/
   ```

## Tests

- Manual validation:
  - [ ] `df -h /` shows disk usage <60%
  - [ ] `systemctl status containerd` shows expected state (stopped/disabled OR running with reduced snapshots)
  - [ ] DO droplet agent still functional: `systemctl status droplet-agent`
  - [ ] No impact to Docker containers: `docker ps`

## Dependencies & Risks

- Dependencies:
  - SSH access to prod server
  - Root access for containerd operations

- Risks/edge cases:
  - DO droplet agent may require containerd - check before removal
  - If snapshots are in use, deletion could break running containers
  - May need to reinstall containerd later if Kubernetes needed
