install:
	install -d $(DESTDIR)/etc/xdg/menus
	install -m 644 menus/*.menu $(DESTDIR)/etc/xdg/menus/

	ln -s applications.menu $(DESTDIR)/etc/xdg/menus/kde4-qubes-applications.menu
	ln -s applications.menu $(DESTDIR)/etc/xdg/menus/kf5-qubes-applications.menu

	install -d $(DESTDIR)/usr/share/desktop-directories
	install -m 644 directory-files/*.directory $(DESTDIR)/usr/share/desktop-directories/

	mkdir -p $(DESTDIR)/etc/xdg/menus/applications-merged ||:
	mkdir -p $(DESTDIR)/etc/xdg/menus/preferences-merged ||:
	mkdir -p $(DESTDIR)/etc/xdg/menus/preferences-post-merged ||:
	mkdir -p $(DESTDIR)/etc/xdg/menus/settings-merged ||:

	# create the settings-merged to prevent gamin from looking for it
	# in a loop
	mkdir -p $(DESTDIR)/etc/xdg/menus/settings-merged ||:

