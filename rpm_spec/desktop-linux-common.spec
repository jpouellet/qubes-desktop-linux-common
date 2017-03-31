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
Requires:	xdotool
Requires:	xorg-x11-utils

%define _builddir %(pwd)

%description
Common code used for multiple desktop environments' Qubes integration

%build
python -m compileall appmenus-scripts
python -O -m compileall appmenus-scripts
make -C doc manpages

%install
install -D -m755 tools/qvm-xkill $RPM_BUILD_ROOT%{_bindir}/qvm-xkill
make -C doc DESTDIR=$RPM_BUILD_ROOT MANDIR=%{_mandir} install

%files
%defattr(-,root,root,-)
%{_bindir}/qvm-xkill
%{_mandir}/man1/{qubes,qvm}-*.1*
