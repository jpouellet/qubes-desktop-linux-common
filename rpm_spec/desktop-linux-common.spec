%{!?version: %define version %(cat version)}

Name:		qubes-desktop-linux-common
Version:	%{version}
Release:	1%{?dist}
Summary:	Common code used for multiple desktop environments' Qubes integration

Group:		Qubes
Vendor:		Invisible Things Lab
License:	GPL
URL:		http://www.qubes-os.org

BuildArch:	noarch
BuildRequires:	pandoc
BuildRequires:	python3
BuildRequires:	python3-devel
BuildRequires:	ImageMagick
Requires:	xdotool
Requires:	xorg-x11-utils
Requires:	python3-qubesimgconverter
Requires:	python3-qubesadmin
Requires:	python3-pyxdg

%define _builddir %(pwd)

%description
Common code used for multiple desktop environments' Qubes integration

%build
make
make -C doc manpages

%install
make DESTDIR=$RPM_BUILD_ROOT MANDIR=%{_mandir} install
make -C doc DESTDIR=$RPM_BUILD_ROOT MANDIR=%{_mandir} install

%post

for i in /usr/share/qubes/icons/*.png ; do
    xdg-icon-resource install --noupdate --novendor --size 48 $i
done
xdg-icon-resource forceupdate

xdg-desktop-menu install /usr/share/qubes-appmenus/qubes-dispvm.directory /usr/share/qubes-appmenus/qubes-dispvm-*.desktop

%preun
if [ "$1" = 0 ] ; then
    # no more packages left

    for i in /usr/share/qubes/icons/*.png ; do
        xdg-icon-resource uninstall --novendor --size 48 $i
    done

    xdg-desktop-menu uninstall /usr/share/qubes-appmenus/qubes-dispvm.directory /usr/share/qubes-appmenus/qubes-dispvm-*.desktop
fi


%files
%defattr(-,root,root,-)
%{_bindir}/qvm-xkill
%{_mandir}/man1/{qubes,qvm}-*.1*
%dir %{python3_sitelib}/qubesdesktop-*.egg-info
%{python3_sitelib}/qubesdesktop-*.egg-info/*
%dir %{python3_sitelib}/qubesappmenus
%dir %{python3_sitelib}/qubesappmenus/__pycache__
%{python3_sitelib}/qubesappmenus/__pycache__/*
%{python3_sitelib}/qubesappmenus/__init__.py
%{python3_sitelib}/qubesappmenus/receive.py
%{python3_sitelib}/qubesappmenus/qubes-appmenu-select.desktop.template
%{python3_sitelib}/qubesappmenus/qubes-servicevm.directory.template
%{python3_sitelib}/qubesappmenus/qubes-templatevm.directory.template
%{python3_sitelib}/qubesappmenus/qubes-vm.directory.template
%{python3_sitelib}/qubesappmenus/tests.py
%{python3_sitelib}/qubesappmenus/tests_integ.py
%{python3_sitelib}/qubesappmenus/test-data

%dir %{python3_sitelib}/qubesappmenusext
%dir %{python3_sitelib}/qubesappmenusext/__pycache__
%{python3_sitelib}/qubesappmenusext/__pycache__/*
%{python3_sitelib}/qubesappmenusext/__init__.py

/etc/qubes-rpc/qubes.SyncAppMenus
/usr/share/qubes-appmenus/qubes-dispvm-firefox.desktop
/usr/share/qubes-appmenus/qubes-dispvm-xterm.desktop
/usr/share/qubes-appmenus/qubes-dispvm.directory
/usr/share/qubes-appmenus/qubes-start.desktop
/usr/share/qubes-appmenus/hvm
/usr/share/qubes/icons/*.png
/usr/bin/qvm-sync-appmenus
/usr/bin/qvm-appmenus
