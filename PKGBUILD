# Maintainer: Markus Oeffling
pkgname=omakeyklack
pkgver=0.2.1
pkgrel=1
pkgdesc="Tray-App und Soundpack-Umschalter fuer wayvibes"
arch=('any')
url="https://github.com/OEM-Mrks/omakeyklack"
license=('MIT')
depends=('python' 'python-gobject' 'gtk3' 'libayatana-appindicator'
         'gst-plugins-base' 'gst-plugins-good')
optdepends=('wayvibes-git: Sound-Engine, ohne sie werden keine Toene abgespielt')
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

  install -Dm644 data/omakeyklack.desktop \
    "$pkgdir/usr/share/applications/omakeyklack.desktop"
  for icon in data/icons/hicolor/scalable/apps/*.svg; do
    install -Dm644 "$icon" \
      "$pkgdir/usr/share/icons/hicolor/scalable/apps/$(basename "$icon")"
  done
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
