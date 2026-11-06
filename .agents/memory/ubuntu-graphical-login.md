# Ubuntu graphical login investigation

Historical observation, 2026-11-01: the Ubuntu VM intermittently displayed a black
screen before or after login. GNOME processes remained alive. Cursor movement
during Xorg login reproduced the problem; one successful login did not establish
a lasting repair. Disabling animations and changing the virtual graphics controller
did not reliably eliminate it. A repaint helper was tested and later removed.

The final applied configuration enabled Wayland in `/etc/gdm3/custom.conf` and set
`MUTTER_DEBUG_DISABLE_HW_CURSORS=1` in `/etc/environment`. The original VMSVGA
controller was restored. Both greeter and user session were verified as Wayland,
with software cursors, across two subsequent reboots, including a pointer-motion
test; the user then confirmed the desktop worked.

This was a graphical-session correction, not a change to gateway networking,
Zeek or the collector. Do not rewrite netplan or rerun gateway setup merely because
the desktop is black. Inspect current session/display logs first. Do not undo the
Wayland/cursor configuration during an unrelated sensor setup.

Evidence: the 2026-11-01 investigation's GNOME journal/session checks and user
confirmation. This note records that tested configuration, not a universal fix
for every black screen or a claim about the VM's current state.
