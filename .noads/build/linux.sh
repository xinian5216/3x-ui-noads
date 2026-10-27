#!/usr/bin/env bash
set -euo pipefail
case "${NOADS_PLATFORM:-}" in amd64|arm64|armv7|armv6|386|armv5|s390x) ;; *) exit 1;; esac
CURL_RETRY="--retry 5 --retry-all-errors --retry-delay 3"
fetch() { wget -q --tries=5 --waitretry=10 --retry-on-http-error=429,500,502,503 "$@"; }
export CGO_ENABLED=1
export GOOS=linux
export GOARCH=${NOADS_PLATFORM}
# Use Bootlin prebuilt cross-toolchains (musl 1.2.5 in stable series)
case "${NOADS_PLATFORM}" in
  amd64) BOOTLIN_ARCH="x86-64" ;;
  arm64) BOOTLIN_ARCH="aarch64" ;;
  armv7) BOOTLIN_ARCH="armv7-eabihf"; export GOARCH=arm GOARM=7 ;;
  armv6) BOOTLIN_ARCH="armv6-eabihf"; export GOARCH=arm GOARM=6 ;;
  armv5) BOOTLIN_ARCH="armv5-eabi"; export GOARCH=arm GOARM=5 ;;
  386) BOOTLIN_ARCH="x86-i686" ;;
  s390x) BOOTLIN_ARCH="s390x-z13" ;;
esac
echo "Resolving Bootlin musl toolchain for arch=$BOOTLIN_ARCH (platform=${NOADS_PLATFORM})"
TARBALL_BASE="https://toolchains.bootlin.com/downloads/releases/toolchains/$BOOTLIN_ARCH/tarballs/"
TARBALL_URL=$(curl -fsSL $CURL_RETRY "$TARBALL_BASE" | grep -oE "${BOOTLIN_ARCH}--musl--stable-[^\"]+\\.tar\\.xz" | sort -r | head -n1)
[ -z "$TARBALL_URL" ] && { echo "Failed to locate Bootlin musl toolchain for arch=$BOOTLIN_ARCH" >&2; exit 1; }
echo "Downloading: $TARBALL_URL"
cd /tmp
curl -fL -sS $CURL_RETRY -o "$(basename "$TARBALL_URL")" "$TARBALL_BASE/$TARBALL_URL"
tar -xf "$(basename "$TARBALL_URL")"
TOOLCHAIN_DIR=$(find . -maxdepth 1 -type d -name "${BOOTLIN_ARCH}--musl--stable-*" | head -n1)
export PATH="$(realpath "$TOOLCHAIN_DIR")/bin:$PATH"
export CC=$(realpath "$(find "$TOOLCHAIN_DIR/bin" -name '*-gcc.br_real' -type f -executable | head -n1)")
[ -z "$CC" ] && { echo "No gcc.br_real found in $TOOLCHAIN_DIR/bin" >&2; exit 1; }
cd -
# Stamp the commit into per-commit (dev channel) builds only; tagged
# stable releases stay unstamped so config.IsDevBuild() returns false.
LDFLAGS="-w -s -linkmode external -extldflags '-static'"
if false; then
  LDFLAGS="$LDFLAGS -X github.com/mhsanaei/3x-ui/v3/internal/config.buildCommit=${GITHUB_SHA::8} -X github.com/mhsanaei/3x-ui/v3/internal/config.buildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi
go build -buildvcs=true -ldflags "$LDFLAGS" -o xui-release -v .
file xui-release
ldd xui-release || echo "Static binary confirmed"

mkdir x-ui
cp xui-release x-ui/
cp x-ui.service.debian x-ui/
cp x-ui.service.arch x-ui/
cp x-ui.service.rhel x-ui/
cp x-ui.sh x-ui/
mv x-ui/xui-release x-ui/x-ui
mkdir x-ui/bin
cd x-ui/bin

# Download dependencies
Xray_URL="https://github.com/XTLS/Xray-core/releases/download/v26.10.21/"
if [ "${NOADS_PLATFORM}" == "amd64" ]; then
  fetch ${Xray_URL}Xray-linux-64.zip
  unzip Xray-linux-64.zip
  rm -f Xray-linux-64.zip
elif [ "${NOADS_PLATFORM}" == "arm64" ]; then
  fetch ${Xray_URL}Xray-linux-arm64-v8a.zip
  unzip Xray-linux-arm64-v8a.zip
  rm -f Xray-linux-arm64-v8a.zip
elif [ "${NOADS_PLATFORM}" == "armv7" ]; then
  fetch ${Xray_URL}Xray-linux-arm32-v7a.zip
  unzip Xray-linux-arm32-v7a.zip
  rm -f Xray-linux-arm32-v7a.zip
elif [ "${NOADS_PLATFORM}" == "armv6" ]; then
  fetch ${Xray_URL}Xray-linux-arm32-v6.zip
  unzip Xray-linux-arm32-v6.zip
  rm -f Xray-linux-arm32-v6.zip
elif [ "${NOADS_PLATFORM}" == "386" ]; then
  fetch ${Xray_URL}Xray-linux-32.zip
  unzip Xray-linux-32.zip
  rm -f Xray-linux-32.zip
elif [ "${NOADS_PLATFORM}" == "armv5" ]; then
  fetch ${Xray_URL}Xray-linux-arm32-v5.zip
  unzip Xray-linux-arm32-v5.zip
  rm -f Xray-linux-arm32-v5.zip
elif [ "${NOADS_PLATFORM}" == "s390x" ]; then
  fetch ${Xray_URL}Xray-linux-s390x.zip
  unzip Xray-linux-s390x.zip
  rm -f Xray-linux-s390x.zip
fi
rm -f geoip.dat geosite.dat
fetch https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat
fetch https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat
fetch -O geoip_IR.dat https://github.com/chocolate4u/Iran-v2ray-rules/releases/latest/download/geoip.dat
fetch -O geosite_IR.dat https://github.com/chocolate4u/Iran-v2ray-rules/releases/latest/download/geosite.dat
fetch -O geoip_RU.dat https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat
fetch -O geosite_RU.dat https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat
mv xray xray-linux-${NOADS_PLATFORM}
# mtg-multi (MTProto sidecar) ships prebuilt release binaries whose
# platform labels match our matrix, so download and unpack the matching
# archive. Only the platforms the fork publishes are packaged — the tag
# lookup lives inside that branch so unpackaged platforms (s390x) never
# depend on it. The tag comes from the release-page redirect on
# github.com — the host the downloads need anyway — because api.github.com
# has 503'd whole release runs while asset downloads kept working.
case "${NOADS_PLATFORM}" in
  amd64|arm64|armv7|armv6|386)
    MTG_MULTI_VER=$(curl -sf $CURL_RETRY -o /dev/null -w '%{redirect_url}' "https://github.com/mhsanaei/mtg-multi/releases/latest" | sed -n 's#.*/releases/tag/##p')
    if [ -z "$MTG_MULTI_VER" ]; then echo "could not resolve the latest mtg-multi release tag"; exit 1; fi
    MTG_PKG="mtg-multi-${MTG_MULTI_VER#v}-linux-${NOADS_PLATFORM}"
    curl -sfLRO $CURL_RETRY "https://github.com/mhsanaei/mtg-multi/releases/download/${MTG_MULTI_VER}/${MTG_PKG}.tar.gz"
    tar -xzf "${MTG_PKG}.tar.gz"
    mv "${MTG_PKG}/mtg-multi" "mtg-linux-${NOADS_PLATFORM}"
    rm -rf "${MTG_PKG}" "${MTG_PKG}.tar.gz"
    ;;
esac
cd ../..

cp LICENSE NOADS.md .noads/provenance.json x-ui/
tar -zcvf x-ui-linux-${NOADS_PLATFORM}.tar.gz x-ui
sha256sum x-ui-linux-${NOADS_PLATFORM}.tar.gz > x-ui-linux-${NOADS_PLATFORM}.tar.gz.sha256
