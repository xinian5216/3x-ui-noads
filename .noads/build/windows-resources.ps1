$ErrorActionPreference="Stop"
$retry = @{ MaximumRetryCount = 5; RetryIntervalSec = 10 }
mkdir x-ui
Copy-Item xui-release.exe x-ui\3x-ui.exe
mkdir x-ui\bin
cd x-ui\bin

# Download Xray for Windows
$Xray_URL = "https://github.com/XTLS/Xray-core/releases/download/v26.10.21/"
Invoke-WebRequest @retry -Uri "${Xray_URL}Xray-windows-64.zip" -OutFile "Xray-windows-64.zip"
Expand-Archive -Path "Xray-windows-64.zip" -DestinationPath .
Remove-Item "Xray-windows-64.zip"
Remove-Item geoip.dat, geosite.dat -ErrorAction SilentlyContinue
Invoke-WebRequest @retry -Uri "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" -OutFile "geoip.dat"
Invoke-WebRequest @retry -Uri "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" -OutFile "geosite.dat"
Invoke-WebRequest @retry -Uri "https://github.com/chocolate4u/Iran-v2ray-rules/releases/latest/download/geoip.dat" -OutFile "geoip_IR.dat"
Invoke-WebRequest @retry -Uri "https://github.com/chocolate4u/Iran-v2ray-rules/releases/latest/download/geosite.dat" -OutFile "geosite_IR.dat"
Invoke-WebRequest @retry -Uri "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat" -OutFile "geoip_RU.dat"
Invoke-WebRequest @retry -Uri "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat" -OutFile "geosite_RU.dat"
Rename-Item xray.exe xray-windows-amd64.exe

# mtg-multi (MTProto sidecar) publishes a prebuilt Windows binary, so
# download and unpack it instead of compiling. The tag comes from the
# release-page redirect on github.com — not api.github.com, whose
# outages have failed release runs while asset downloads kept working.
$MTG_MULTI_VER = (curl.exe -sf --retry 5 --retry-all-errors --retry-delay 3 -o NUL -w '%{redirect_url}' "https://github.com/mhsanaei/mtg-multi/releases/latest") -replace '^.*/releases/tag/', ''
if (-not $MTG_MULTI_VER -or $MTG_MULTI_VER -notmatch '^v[\d.]+$') { throw "could not resolve the latest mtg-multi release tag" }
$MTG_PKG = "mtg-multi-$($MTG_MULTI_VER.TrimStart('v'))-windows-amd64"
curl.exe -sfLRO --retry 5 --retry-all-errors --retry-delay 3 "https://github.com/mhsanaei/mtg-multi/releases/download/$MTG_MULTI_VER/$MTG_PKG.zip"
Expand-Archive -Path "$MTG_PKG.zip" -DestinationPath "mtg-tmp" -Force
Move-Item "mtg-tmp/$MTG_PKG/mtg-multi.exe" "mtg-windows-amd64.exe"
Remove-Item -Recurse -Force "mtg-tmp", "$MTG_PKG.zip"

cd ..
Copy-Item -Path ..\windows_files\* -Destination . -Recurse
cd ..

Copy-Item LICENSE, NOADS.md, .noads/provenance.json x-ui/
