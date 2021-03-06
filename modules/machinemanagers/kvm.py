# Copyright (C) 2010-2012 Cuckoo Sandbox Developers.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from lib.cuckoo.common.abstracts import MachineManager
from lib.cuckoo.common.exceptions import CuckooDependencyError, CuckooMachineError

try:
    import libvirt
except ImportError:
    raise CuckooDependencyError("Unable to import libvirt")

class KVM(MachineManager):
    """Virtualization layer for KVM based on python-libvirt."""

    def _initialize_check(self):
        """Runs all checks when a machine manager is initialized.
        @raise CuckooMachineError: if libvirt version is not supported.
        """
        # KVM specific checks.
        if not self._version_check():
            raise CuckooMachineError("Libvirt version is not supported, please get an updated version")
        # Base checks.
        super(KVM, self)._initialize_check()

    def start(self, label):
        """Starts a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to start virtual machine.
        """
        conn = self._connect()
        vm = self._lookup(conn, label)

        # Get current snapshot.
        try:
            snap = vm.hasCurrentSnapshot(flags=0)
        except libvirt.libvirtError:
            self._disconnect(conn)
            raise CuckooMachineError("Unable to get current snapshot for virtual machine %s" % label)

        # Revert to latest snapshot.
        if snap:
            try:
                vm.revertToSnapshot(vm.snapshotCurrent(flags=0), flags=0)
            except libvirt.libvirtError:
                raise CuckooMachineError("Unable to restore snapshot on virtual machine %s" % label)
            finally:
                self._disconnect(conn)
        else:
            self._disconnect(conn)
            raise CuckooMachineError("No snapshot found for virtual machine %s" % label)

    def stop(self, label):
        """Stops a virtual machine. Kill them all.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to stop virtual machine.
        """
        conn = self._connect()
        vm = self._lookup(conn, label)

        # Force virtual machine shutdown.
        try:
            vm.destroy() # Machete's way!
        except libvirt.libvirtError:
            raise CuckooMachineError("Error stopping virtual machine %s" % label)
        finally:
            self._disconnect(conn)

    def _connect(self):
        """Connects to libvirt subsystem.
        @raise CuckooMachineError: if cannot connect to libvirt.
        """
        try:
            return libvirt.open("qemu:///system")
        except libvirt.libvirtError:
            raise CuckooMachineError("Cannot connect to libvirt")

    def _disconnect(self, conn):
        """Disconnects to libvirt subsystem.
        @raise CuckooMachineError: if cannot disconnect from libvirt.
        """
        try:
            conn.close()
        except libvirt.libvirtError:
            raise CuckooMachineError("Cannot disconnect from libvirt")

    def _lookup(self, conn, label):
        """Search for a virtual machine.
        @param conn: libvirt connection handle.
        @param label: virtual machine name.
        @raise CuckooMachineError: if virtual machine is not found.
        """
        try:
            vm = conn.lookupByName(label)
        except libvirt.libvirtError:
                raise CuckooMachineError("Cannot found machine %s" % label)

        return vm

    def _list(self):
        """List available virtual machines.
        @raise CuckooMachineError: if unable to list virtual machines.
        """
        conn = self._connect()
        try:
            names = conn.listDefinedDomains()
        except libvirt.libvirtError:
            raise CuckooMachineError("Cannot list domains")
        finally:
            self._disconnect(conn)

        return names

    def _version_check(self):
        """Check if libvirt release supports snapshots.
        @return: True or false.
        """
        if libvirt.getVersion() >= 8000:
            return True
        else:
            return False
