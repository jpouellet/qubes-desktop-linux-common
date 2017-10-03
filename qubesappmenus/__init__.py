#!/usr/bin/python2
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2010  Joanna Rutkowska <joanna@invisiblethingslab.com>
# Copyright (C) 2013  Marek Marczykowski <marmarek@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.

import subprocess
import sys
import os
import os.path
import shutil
import dbus
import logging
import pkg_resources
import xdg.BaseDirectory

import qubesadmin
import qubesadmin.exc
import qubesadmin.tools
import qubesadmin.vm

import qubesimgconverter


basedir = os.path.join(xdg.BaseDirectory.xdg_data_home, 'qubes-appmenus')

class DispvmNotSupportedError(qubesadmin.exc.QubesException):
    '''Creating Disposable VM menu entries not supported by this template'''
    def __init__(self, msg=None):
        if msg is None:
            msg = 'Creating Disposable VM menu entries ' \
                  'not supported by this template'
            super(DispvmNotSupportedError, self).__init__(msg)


class AppmenusSubdirs:
    templates_subdir = 'apps.templates'
    template_icons_subdir = 'apps.tempicons'
    subdir = 'apps'
    icons_subdir = 'apps.icons'
    template_templates_subdir = 'apps-template.templates'
    whitelist = 'whitelisted-appmenus.list'


class AppmenusPaths:
    appmenu_start_hvm_template = \
        '/usr/share/qubes-appmenus/qubes-start.desktop'


class Appmenus(object):
    def templates_dir(self, vm):
        """

        :type vm: qubes.vm.qubesvm.QubesVM
        """
        if vm.updateable:
            return os.path.join(basedir, vm.name,
                AppmenusSubdirs.templates_subdir)
        elif hasattr(vm, 'template'):
            return self.templates_dir(vm.template)
        else:
            return None

    def template_icons_dir(self, vm):
        '''Directory for not yet colore icons'''
        if vm.updateable:
            return os.path.join(basedir, vm.name,
                AppmenusSubdirs.template_icons_subdir)
        elif hasattr(vm, 'template'):
            return self.template_icons_dir(vm.template)
        else:
            return None

    def appmenus_dir(self, vm):
        '''Desktop files generated for particular VM'''
        return os.path.join(basedir, str(vm), AppmenusSubdirs.subdir)

    def icons_dir(self, vm):
        '''Icon files generated (colored) for particular VM'''
        return os.path.join(basedir, str(vm), AppmenusSubdirs.icons_subdir)

    def whitelist_path(self, vm):
        '''File listing files wanted in menu'''
        return os.path.join(basedir, str(vm), AppmenusSubdirs.whitelist)

    def directory_template_name(self, vm, dispvm):
        '''File name of desktop directory entry template'''
        if dispvm:
            return 'qubes-dispvm.directory.template'
        elif vm.__class__.__name__ == 'TemplateVM':
            return 'qubes-templatevm.directory.template'
        elif vm.provides_network:
            return 'qubes-servicevm.directory.template'
        else:
            return 'qubes-vm.directory.template'

    def write_desktop_file(self, vm, source, destination_path, dispvm=False):
        """Format .desktop/.directory file

        :param vm: QubesVM object for which write desktop file
        :param source: desktop file template (path or template itself)
        :param destination_path: where to write the desktop file
        :param dispvm: create entries for launching in DispVM
        :return: True if target file was changed, otherwise False
        """
        if source.startswith('/'):
            with open(source) as f_source:
                source = f_source.read()
        if dispvm:
            if '\nX-Qubes-DispvmExec=' not in source and '\nExec=' in source:
                raise DispvmNotSupportedError()
            source = source.\
                replace('\nExec=', '\nX-Qubes-NonDispvmExec=').\
                replace('\nX-Qubes-DispvmExec=', '\nExec=')
        icon = vm.label.icon
        if dispvm:
            icon = icon.replace('appvm-', 'dispvm-')
        data = source.\
            replace("%VMNAME%", vm.name).\
            replace("%VMDIR%", os.path.join(basedir, vm.name)).\
            replace("%XDGICON%", icon)
        if os.path.exists(destination_path):
            current_dest = open(destination_path).read()
            if current_dest == data:
                return False
        with open(destination_path, "w") as f:
            f.write(data)
        return True

    def get_available(self, vm):
        # TODO icon path (#2885)
        templates_dir = self.templates_dir(vm)
        if templates_dir is None or not os.path.isdir(templates_dir):
            return
        for filename in os.listdir(templates_dir):
            with open(os.path.join(templates_dir, filename)) as file:
                name = None
                for line in file:
                    if line.startswith('Name=%VMNAME%: '):
                        name = line.partition('Name=%VMNAME%: ')[2].strip()
                        break
            assert name is not None, \
                'template {!r} does not contain name'.format(filename)
            yield (filename, name)

    def appmenus_create(self, vm, refresh_cache=True):
        """Create/update .desktop files

        :param vm: QubesVM object for which create entries
        :param refresh_cache: refresh desktop environment cache; if false,
        must be refreshed manually later
        :return: None
        """

        if vm.features.get('internal', False):
            return
        if isinstance(vm, qubesadmin.vm.DispVM):
            return

        vm.log.info("Creating appmenus")
        appmenus_dir = self.appmenus_dir(vm)
        if not os.path.exists(appmenus_dir):
            os.makedirs(appmenus_dir)

        dispvm = vm.features.check_with_template('appmenus-dispvm', False)

        anything_changed = False
        directory_file = os.path.join(appmenus_dir, vm.name + '-vm.directory')
        if self.write_desktop_file(vm,
                pkg_resources.resource_string(__name__,
                    self.directory_template_name(vm, dispvm)).decode(),
                directory_file,
                dispvm):
            anything_changed = True

        templates_dir = self.templates_dir(vm)
        if os.path.exists(templates_dir):
            appmenus = os.listdir(templates_dir)
        else:
            appmenus = []
        changed_appmenus = []
        if os.path.exists(self.whitelist_path(vm)):
            whitelist = [x.rstrip() for x in open(self.whitelist_path(vm))]
            appmenus = [x for x in appmenus if x in whitelist]

        for appmenu in appmenus:
            if self.write_desktop_file(vm,
                    os.path.join(templates_dir, appmenu),
                    os.path.join(appmenus_dir,
                        '-'.join((vm.name, appmenu))),
                    dispvm):
                changed_appmenus.append(appmenu)
        if self.write_desktop_file(vm,
                pkg_resources.resource_string(
                    __name__, 'qubes-vm-settings.desktop.template'
                ).decode(),
                os.path.join(appmenus_dir,
                    '-'.join((vm.name, 'qubes-vm-settings.desktop')))):
            changed_appmenus.append('qubes-vm-settings.desktop')

        if changed_appmenus:
            anything_changed = True

        target_appmenus = map(
            lambda x: '-'.join((vm.name, x)),
            appmenus + ['qubes-vm-settings.desktop']
        )

        # remove old entries
        installed_appmenus = os.listdir(appmenus_dir)
        installed_appmenus.remove(os.path.basename(directory_file))
        appmenus_to_remove = set(installed_appmenus).difference(set(
            target_appmenus))
        if len(appmenus_to_remove):
            appmenus_to_remove_fnames = map(
                lambda x: os.path.join(appmenus_dir, x), appmenus_to_remove)
            try:
                desktop_menu_cmd = ['xdg-desktop-menu', 'uninstall']
                if not refresh_cache:
                    desktop_menu_cmd.append('--noupdate')
                desktop_menu_cmd.extend(appmenus_to_remove_fnames)
                desktop_menu_env = os.environ.copy()
                desktop_menu_env['LC_COLLATE'] = 'C'
                subprocess.check_call(desktop_menu_cmd, env=desktop_menu_env)
            except subprocess.CalledProcessError:
                vm.log.warning("Problem removing old appmenus")

            for appmenu in appmenus_to_remove_fnames:
                os.unlink(appmenu)

        # add new entries
        if anything_changed:
            try:
                desktop_menu_cmd = ['xdg-desktop-menu', 'install']
                if not refresh_cache:
                    desktop_menu_cmd.append('--noupdate')
                desktop_menu_cmd.append(directory_file)
                desktop_menu_cmd.extend(map(
                    lambda x: os.path.join(
                        appmenus_dir, '-'.join((vm.name, x))),
                    changed_appmenus))
                desktop_menu_env = os.environ.copy()
                desktop_menu_env['LC_COLLATE'] = 'C'
                subprocess.check_call(desktop_menu_cmd, env=desktop_menu_env)
            except subprocess.CalledProcessError:
                vm.log.warning("Problem creating appmenus for %s", vm.name)

        if refresh_cache:
            if 'KDE_SESSION_UID' in os.environ:
                subprocess.call(['kbuildsycoca' +
                                 os.environ.get('KDE_SESSION_VERSION', '4')])

    def appmenus_remove(self, vm, refresh_cache=True):
        '''Remove desktop files for particular VM

        Warning: vm may be either QubesVM object, or just its name (str).
        Actual VM may be already removed at this point.
        '''
        appmenus_dir = self.appmenus_dir(vm)
        if os.path.exists(appmenus_dir):
            if hasattr(vm, 'log'):
                vm.log.info("Removing appmenus")
            else:
                if logging.root.getEffectiveLevel() <= logging.INFO:
                    print("Removing appmenus for {!s}".format(vm),
                        file=sys.stderr)
            installed_appmenus = os.listdir(appmenus_dir)
            directory_file = os.path.join(self.appmenus_dir(vm),
                str(vm) + '-vm.directory')
            installed_appmenus.remove(os.path.basename(directory_file))
            if installed_appmenus:
                appmenus_to_remove_fnames = map(
                    lambda x: os.path.join(appmenus_dir, x), installed_appmenus)
                try:
                    desktop_menu_cmd = ['xdg-desktop-menu', 'uninstall']
                    if not refresh_cache:
                        desktop_menu_cmd.append('--noupdate')
                    desktop_menu_cmd.append(directory_file)
                    desktop_menu_cmd.extend(appmenus_to_remove_fnames)
                    desktop_menu_env = os.environ.copy()
                    desktop_menu_env['LC_COLLATE'] = 'C'
                    subprocess.check_call(desktop_menu_cmd,
                        env=desktop_menu_env)
                except subprocess.CalledProcessError:
                    if hasattr(vm, 'log'):
                        vm.log.warning(
                            "Problem removing appmenus for %s", vm.name)

                    else:
                        print(
                            "Problem removing appmenus for {!s}".format(vm),
                            file=sys.stderr)
            shutil.rmtree(appmenus_dir)

        if refresh_cache:
            if 'KDE_SESSION_UID' in os.environ:
                subprocess.call(['kbuildsycoca' +
                                 os.environ.get('KDE_SESSION_VERSION', '4')])

    def appicons_create(self, vm, srcdir=None, force=False):
        """Create/update applications icons"""
        if srcdir is None:
            srcdir = self.template_icons_dir(vm)
        if srcdir is None:
            return
        if not os.path.exists(srcdir):
            return

        if vm.features.get('internal', False):
            return
        if isinstance(vm, qubesadmin.vm.DispVM):
            return

        whitelist = self.whitelist_path(vm)
        if os.path.exists(whitelist):
            whitelist = [line.strip() for line in open(whitelist)]
        else:
            whitelist = None

        dstdir = self.icons_dir(vm)
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        elif not os.path.isdir(dstdir):
            os.unlink(dstdir)
            os.makedirs(dstdir)

        if whitelist:
            expected_icons = \
                list(map(lambda x: os.path.splitext(x)[0] + '.png', whitelist))
        else:
            expected_icons = os.listdir(srcdir)

        for icon in os.listdir(srcdir):
            if icon not in expected_icons:
                continue

            src_icon = os.path.join(srcdir, icon)
            dst_icon = os.path.join(dstdir, icon)
            if not os.path.exists(dst_icon) or force or \
                    os.path.getmtime(src_icon) > os.path.getmtime(dst_icon):
                qubesimgconverter.tint(src_icon, dst_icon, vm.label.color)

        for icon in os.listdir(dstdir):
            if icon not in expected_icons:
                os.unlink(os.path.join(dstdir, icon))

    def appicons_remove(self, vm):
        '''Remove icons

        Warning: vm may be either QubesVM object, or just its name (str).
        Actual VM may be already removed at this point.
        '''
        if not os.path.exists(self.icons_dir(vm)):
            return
        shutil.rmtree(self.icons_dir(vm))

    def appmenus_init(self, vm, src=None):
        '''Initialize directory structure on VM creation, copying appropriate
        data from VM template if necessary

        :param src: source VM to copy data from
        '''
        os.makedirs(os.path.join(basedir, vm.name))
        if src is None:
            try:
                src = vm.template
            except AttributeError:
                pass
        if vm.updateable and src is None:
            os.makedirs(self.templates_dir(vm))
            os.makedirs(self.template_icons_dir(vm))

        if vm.virt_mode == 'hvm' and src is None:
            vm.log.info("Creating appmenus directory: {0}".format(
                self.templates_dir(vm)))
            shutil.copy(AppmenusPaths.appmenu_start_hvm_template,
                        self.templates_dir(vm))

        source_whitelist_filename = 'vm-' + AppmenusSubdirs.whitelist
        if src and os.path.exists(
                os.path.join(basedir, src.name, source_whitelist_filename)):
            vm.log.info("Creating default whitelisted apps list: {0}".
                    format(basedir + '/' + vm.name + '/' +
                           AppmenusSubdirs.whitelist))
            shutil.copy(
                os.path.join(basedir, src.name, source_whitelist_filename),
                os.path.join(basedir, vm.name, AppmenusSubdirs.whitelist))

        if src and vm.updateable:
            for whitelist in (
                    AppmenusSubdirs.whitelist,
                        'vm-' + AppmenusSubdirs.whitelist,
                        'netvm-' + AppmenusSubdirs.whitelist):
                if os.path.exists(os.path.join(basedir, src.name, whitelist)):
                    vm.log.info("Copying whitelisted apps list: {0}".
                        format(whitelist))
                    shutil.copy(os.path.join(basedir, src.name, whitelist),
                        os.path.join(basedir, vm.name, whitelist))

            vm.log.info("Creating/copying appmenus templates")
            if os.path.isdir(self.templates_dir(src)):
                shutil.copytree(self.templates_dir(src),
                                self.templates_dir(vm))
            if os.path.isdir(self.template_icons_dir(src)):
                shutil.copytree(self.template_icons_dir(src),
                                self.template_icons_dir(vm))

    def set_default_whitelist(self, vm, applications_list):
        '''Update default applications list for VMs created on this template

        :param vm: VM object
        :param applications_list: list of applications to include
        '''
        if not os.path.exists(os.path.join(basedir, vm.name)):
            return
        with open(os.path.join(basedir, str(vm),
                        'vm-' + AppmenusSubdirs.whitelist), 'w') as \
                default_whitelist:
            default_whitelist.write('\n'.join(applications_list))

    def set_whitelist(self, vm, applications_list):
        '''Update list of applications to be included in the menu

        :param vm: VM object
        :param applications_list: list of applications to include
        '''
        if not os.path.exists(os.path.join(basedir, vm.name)):
            return
        with open(self.whitelist_path(vm), 'w') as whitelist:
            whitelist.write('\n'.join(applications_list))

    def get_whitelist(self, vm):
        '''Retrieve list of applications to be included in the menu

        :param vm: VM object
        :return: list of applications (.desktop file names), or None if not set
        '''
        if not os.path.exists(self.whitelist_path(vm)):
            return None
        with open(self.whitelist_path(vm), 'r') as whitelist:
            for line in whitelist:
                line = line.strip()
                if not line:
                    continue
                yield line

    def appmenus_update(self, vm, force=False):
        '''Update (regenerate) desktop files and icons for this VM and (in
        case of template) child VMs'''
        self.appicons_create(vm, force=force)
        self.appmenus_create(vm, refresh_cache=False)
        if hasattr(vm, 'appvms'):
            for child_vm in vm.appvms:
                try:
                    self.appicons_create(child_vm, force=force)
                    self.appmenus_create(child_vm, refresh_cache=False)
                except Exception as e:
                    child_vm.log.error("Failed to recreate appmenus for "
                                       "'{0}': {1}".format(child_vm.name,
                        str(e)))
        subprocess.call(['xdg-desktop-menu', 'forceupdate'])
        if 'KDE_SESSION_UID' in os.environ:
            subprocess.call([
                'kbuildsycoca' + os.environ.get('KDE_SESSION_VERSION', '4')])

        # Apparently desktop environments heavily caches the icons,
        # see #751 for details
        if "plasma" in os.environ.get("DESKTOP_SESSION", ""):
            try:
                os.unlink(os.path.expandvars(
                    "$HOME/.kde/cache-$HOSTNAME/icon-cache.kcache"))
            except:
                pass
            try:
                notify_object = dbus.SessionBus().get_object(
                    "org.freedesktop.Notifications",
                    "/org/freedesktop/Notifications")
                notify_object.Notify(
                    "Qubes", 0, vm.label.icon, "Qubes",
                    "You will need to log off and log in again for the VM icons "
                    "to update in the KDE launcher menu",
                    [], [], 10000,
                    dbus_interface="org.freedesktop.Notifications")
            except:
                pass


parser = qubesadmin.tools.QubesArgumentParser()

parser_stdin_mode = parser.add_mutually_exclusive_group()

parser.add_argument('--init', action='store_true',
    help='Initialize directory structure for appmenus (on VM creation)')
parser.add_argument('--create', action='store_true',
    help='Create appmenus')
parser.add_argument('--remove', action='store_true',
    help='Remove appmenus')
parser.add_argument('--update', action='store_true',
    help='Update appmenus')
parser.add_argument('--get-available', action='store_true',
    help='Get list of applications available')
parser.add_argument('--get-whitelist', action='store_true',
    help='Get list of applications to include in the menu')
parser_stdin_mode.add_argument('--set-whitelist', metavar='PATH', action='store',
    help='Set list of applications to include in the menu,'
         'use \'-\' to read from stdin')
parser_stdin_mode.add_argument('--set-default-whitelist', metavar='PATH', action='store',
    help='Set default list of applications to include in menu '
         'for VMs based on this template,'
         'use \'-\' to read from stdin')
parser.add_argument('--source', action='store', default=None,
    help='Source VM to copy data from (for --init option)')
parser.add_argument('--force', action='store_true', default=False,
    help='Force refreshing files, even when looks up to date')
parser.add_argument('--i-understand-format-is-unstable', dest='fool',
    action='store_true',
    help='required pledge for --get-available')
parser.add_argument('domains', metavar='VMNAME', nargs='+',
    help='VMs on which perform requested actions')


def retrieve_list(path):
    '''Helper function to retrieve data from given path, or stdin if '-'
    specified, then return it as a list of lines.

    :param path: path or '-'
    :return: list of lines
    '''
    if path == '-':
        return sys.stdin.readlines()
    else:
        with open(path, 'r') as file:
            return file.readlines()


def main(args=None, app=None):
    args = parser.parse_args(args=args, app=app)
    appmenus = Appmenus()
    if args.source is not None:
        args.source = args.app.domains[args.source]
    for vm in args.domains:
        # allow multiple actions
        # for remove still use just VM name (str), because VM may be already
        # removed
        if args.remove:
            appmenus.appmenus_remove(vm)
            appmenus.appicons_remove(vm)
            shutil.rmtree(os.path.join(basedir, str(vm)))
        # for other actions - get VM object
        if args.init or args.create or args.update or args.set_whitelist or \
                args.set_default_whitelist or args.get_whitelist or \
                args.get_available:
            vm = args.app.domains[vm]
            if args.init:
                appmenus.appmenus_init(vm, src=args.source)
            if args.get_whitelist:
                whitelist = appmenus.get_whitelist(vm)
                print('\n'.join(whitelist))
            if args.set_default_whitelist:
                whitelist = retrieve_list(args.set_default_whitelist)
                appmenus.set_default_whitelist(vm, whitelist)
            if args.set_whitelist:
                whitelist = retrieve_list(args.set_whitelist)
                appmenus.set_whitelist(vm, whitelist)
            if args.create:
                appmenus.appicons_create(vm, force=args.force)
                appmenus.appmenus_create(vm)
            if args.update:
                appmenus.appmenus_update(vm, force=args.force)
            if args.get_available:
                if not args.fool:
                    parser.error(
                        'this requires --i-understand-format-is-unstable '
                        'and a sacrifice of one cute kitten')
                sys.stdout.write(''.join('{} - {}\n'.format(*available)
                    for available in appmenus.get_available(vm)))

if __name__ == '__main__':
    sys.exit(main())
