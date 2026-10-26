# Arch Linux (x86_64) with what a desktop install adds before the guide starts:
# sudo for the wheel group and an X server (Xvfb stands in for the desktop's
# display). Git, Python, curl, less, Obsidian and Docker are left to the guide.
# DisableSandbox: pacman's download sandbox can't start under amd64 emulation
# on Apple Silicon; a real x86_64 machine doesn't need this.
FROM archlinux:latest
RUN printf '\n[options]\nDisableSandbox\n' >> /etc/pacman.conf \
 && pacman -Syu --noconfirm \
 && pacman -S --noconfirm --needed sudo xorg-server-xvfb \
 && rm -rf /var/cache/pacman/pkg/*
RUN useradd -m -s /bin/bash -G wheel learner \
 && echo 'learner:learner-pass' | chpasswd \
 && printf '%%wheel ALL=(ALL:ALL) ALL\n' > /etc/sudoers.d/10-wheel && chmod 440 /etc/sudoers.d/10-wheel
CMD ["/usr/bin/sleep", "infinity"]
