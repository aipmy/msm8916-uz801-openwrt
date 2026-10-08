#!/usr/bin/env bash
set -e

# 1. Lock default target to msm89xx
sed -i 's/default TARGET_mediatek/default TARGET_msm89xx/' scripts/target-metadata.pl 2>/dev/null || true

# 1.1 Always synchronize .config with diffconfig_jz0145_complete if present
if [ -f /repo/configs/diffconfig_jz0145_complete ]; then
    cp -f /repo/configs/diffconfig_jz0145_complete /home/builder/openwrt/.config
    ./scripts/config/conf --defconfig=/home/builder/openwrt/.config Config.in >/dev/null 2>&1 || true
fi

# 2. Prevent include/toplevel.mk from resetting .config via tmp/.config
python3 -c "
with open('include/toplevel.mk', 'r') as f:
    lines = f.readlines()
new_lines = []
skip = False
for line in lines:
    if '@(' in line and 'cp .config tmp/.config' in ''.join(lines):
        # check if this is the start of the subshell
        pass
    if 'cp .config tmp/.config' in line:
        skip = True
        # remove previous line if it was @(
        if new_lines and '@(' in new_lines[-1]:
            new_lines.pop()
        new_lines.append('\t@true\n')
        continue
    if skip:
        if line.strip() == ')':
            skip = False
        continue
    new_lines.append(line)
with open('include/toplevel.mk', 'w') as f:
    f.writelines(new_lines)
" 2>/dev/null || true

# 3. Copy outputs back to host repo_output after build
copy_output() {
    if [ -d /home/builder/openwrt/bin/targets/msm89xx/msm8916 ]; then
        echo "Copying firmware artifacts to host /repo_output..."
        mkdir -p /repo_output
        cp -a /home/builder/openwrt/bin/targets/msm89xx/msm8916/* /repo_output/ || true
    fi
}
trap copy_output EXIT

exec "$@"
