include $(TOPDIR)/rules.mk

PKG_NAME:=luci-theme-proton2025
PKG_VERSION:=1.4.0
PKG_RELEASE:=1

LUCI_TITLE:=Proton2025 - Elegant Dark Theme for LuCI
LUCI_DEPENDS:=+luci-base
LUCI_PKGARCH:=all

define Package/$(PKG_NAME)/conffiles
/etc/config/proton2025
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
chmod -R 755 /www/luci-static/proton2025 /usr/share/ucode/luci/template/themes/proton2025 2>/dev/null || true
find /www/luci-static/proton2025 -type f -exec chmod 644 {} + 2>/dev/null || true
find /usr/share/ucode/luci/template/themes/proton2025 -type f -exec chmod 644 {} + 2>/dev/null || true
exit 0
endef

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature

