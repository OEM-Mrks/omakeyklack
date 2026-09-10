# Maintainer: Markus Oeffling
pkgname=omakeyklack
pkgver=0.4.2
pkgrel=1
pkgdesc="Tray-App und Soundpack-Umschalter fuer wayvibes"
arch=('any')
url="https://github.com/OEM-Mrks/omakeyklack"
license=('MIT')
# wayvibes gehoert in depends und nicht in optdepends: ohne die Engine
# spielt omakeyklack keinen einzigen Ton, das Paket waere eine leere
# Oberflaeche. gstreamer liefert die Gst-Typelib, gst-plugins-base den
# playbin, gst-plugins-good die WAV-/MP3-/FLAC-Dekoder.
depends=('python' 'python-gobject' 'gtk3' 'libayatana-appindicator'
         'gstreamer' 'gst-plugins-base' 'gst-plugins-good'
         'wayvibes-git')
install="$pkgname.install"
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
  cd "$srcdir/$pkgname-$pkgver"
  install -d "$pkgdir/usr/lib/omakeyklack"
  cp -r src/omakeyklack "$pkgdir/usr/lib/omakeyklack/omakeyklack"

  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/omakeyklack" <<'LAUNCHER'
#!/usr/bin/env bash
exec env PYTHONPATH="/usr/lib/omakeyklack${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m omakeyklack "$@"
LAUNCHER
  chmod 755 "$pkgdir/usr/bin/omakeyklack"

  # Wird von "omakeyklack --check" aufgerufen.
  install -Dm755 bin/omakeyklack-doctor "$pkgdir/usr/bin/omakeyklack-doctor"

  install -Dm644 data/omakeyklack.desktop \
    "$pkgdir/usr/share/applications/omakeyklack.desktop"
  for icon in data/icons/hicolor/scalable/apps/*.svg; do
    install -Dm644 "$icon" \
      "$pkgdir/usr/share/icons/hicolor/scalable/apps/$(basename "$icon")"
  done
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
