# Copyright (C) 2023 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin)


class Kea(Plugin):

    """
    Kea is a Kea is the next generation of DHCP software, developed by Internet
    Systems Consortium (ISC). It supports both the DHCPv4 and DHCPv6 protocols
    along with their extensions, e.g. prefix delegation and dynamic updates to
    DNS.
    """
    short_desc = 'Kea DHCP and DDNS server from ISC'

    plugin_name = "kea"
    packages = ("kea", )

    def setup(self):
        self.add_copy_spec([
            "/etc/kea/*",
        ])


class RedHatKea(Kea, RedHatPlugin):

    def setup(self):
        super().setup()
        self.add_cmd_output([
            "keactrl status",
        ])

    def postproc(self):
        """ format is "password": "kea", """
        self.do_path_regex_sub(
            '/etc/kea/*',
            r'(^\s*"password":\s*)(".*"),',
            r'\1********'
        )

# vim: set et ts=4 sw=4 :
