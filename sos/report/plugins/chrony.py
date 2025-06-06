# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Chrony(Plugin):

    short_desc = 'Chrony clock (for Network time protocol)'

    plugin_name = "chrony"
    profiles = ('system', 'services')

    packages = ('chrony',)

    def setup(self):
        self.add_cmd_output([
            "chronyc activity",
            "chronyc tracking",
            "chronyc sourcestats",
            "chronyc serverstats",
            "chronyc ntpdata",
            "chronyc -n clients",
            "chronyc -N authdata",
            "chronyc -n selectdata",
        ])
        self.add_cmd_output("chronyc -n sources", tags="chronyc_sources")

        if self.get_option("all_logs"):
            self.add_copy_spec([
                    "/var/log/chrony/*",
            ])
        else:
            self.add_copy_spec([
                    "/var/log/chrony/*.log",
            ])


class RedHatChrony(Chrony, RedHatPlugin):
    def setup(self):
        super().setup()
        self.add_copy_spec([
            "/etc/chrony.conf",
            "/var/lib/chrony/drift"
        ])
        self.add_journal(units="chronyd")


class DebianChrony(Chrony, DebianPlugin, UbuntuPlugin):
    def setup(self):
        super().setup()
        self.add_copy_spec([
            "/etc/chrony/chrony.conf",
            "/etc/chrony/conf.d",
            "/etc/chrony/sources.d",
            "/var/lib/chrony/chrony.drift",
            "/etc/default/chrony"
        ])
        self.add_journal(units="chrony")

# vim: et ts=4 sw=4
