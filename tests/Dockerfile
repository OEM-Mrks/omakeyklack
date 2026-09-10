# Ein moeglichst nacktes Arch - so nah an "frisch installiert", wie es ohne
# echte Neuinstallation geht.
#
# Bewusst NICHT enthalten: python-gobject, gtk3, gstreamer,
# libayatana-appindicator, ein AUR-Helfer, Soundpacks, die Gruppe input.
# Genau das muss install.sh selbst beschaffen koennen - und genau daran ist
# die Einrichtung auf einer frischen Omarchy-Maschine gescheitert.
#
# Gebaut und benutzt wird das Bild von tests/fresh-install.sh.
FROM archlinux:base-devel

# curl und tar fuer boot.sh, git fuer den Klon-Weg, sudo weil makepkg und
# pacman es brauchen.
RUN pacman -Sy --noconfirm --needed git sudo curl tar && \
    pacman -Scc --noconfirm

# makepkg weigert sich als root - also ein normaler Benutzer, wie auf einer
# echten Maschine auch. Ohne Passwort, damit der Lauf nicht haengt.
RUN useradd -m -G wheel pruefer && \
    echo 'pruefer ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/pruefer && \
    groupadd -f input

USER pruefer
WORKDIR /home/pruefer
