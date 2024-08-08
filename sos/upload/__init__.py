# Copyright 2024 Red Hat, Inc. Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import sys
import logging
import importlib

from textwrap import fill
from sos.component import SoSComponent
from sos import _sos as _
from sos import __version__


class SoSUpload(SoSComponent):
    """
    This class is designed to upload files to a distribution
    defined location. These files can be either sos reports,
    sos collections, or other kind of files like: vmcores,
    application cores, logs, etc.

    """

    desc = """Upload a file to a user or policy defined remote location"""

    arg_defaults = {
        'upload_file': '',
        'case_id': '',
        'low_priority': False,
        'plugopts': [],
        'upload_url': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'upload_method': 'auto',
        'upload_no_ssl_verify': False,
        'upload_protocol': 'auto',
        'upload_s3_endpoint': 'https://s3.amazonaws.com',
        'upload_s3_region': None,
        'upload_s3_bucket': None,
        'upload_s3_access_key': None,
        'upload_s3_secret_key': None,
        'upload_s3_object_prefix': None,
        'upload_profile': None
    }

    def __init__(self, parser=None, args=None, cmdline=None, in_place=False,
                 hook_commons=None, archive=None):
        if not in_place:
            # we are running `sos upload` directly
            super().__init__(parser, args, cmdline)
            self.from_cmdline = True
        else:
            # we are being hooked by either SoSReport or SoSCollector, don't
            # re-init everything as that will cause issues, but instead load
            # the needed bits from the calling component
            self.opts = hook_commons['options']
            self.policy = hook_commons['policy']
            self.manifest = hook_commons['manifest']
            self.parser = parser
            self.cmdline = cmdline
            self.args = args
            self._upload_file = archive

            self.ui_log = logging.getLogger('sos_ui')
            self.from_cmdline = False
            self.archive = archive
        # add manifest section for upload
        self.manifest.components.add_section('upload')

        self.profiles_data = {
            'redhat': {
                'mod': "sos.upload.profiles.redhat",
                'class': "RHELUpload",
                'description': "Red Hat"
            },
            'ubuntu': {
                'mod': "sos.upload.profiles.ubuntu",
                'class': "UbuntuUpload",
                'description': "Ubuntu"
            },
            'generic': {
                'mod': "sos.upload.profiles",
                'class': "Upload",
                'description': "Generic"

            }
        }

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos upload FILE [options]'
        upload_grp = parser.add_argument_group(
            'Upload Options',
            'These options control how upload manages files'
            )
        upload_grp.add_argument("upload_file", metavar="FILE",
                                help="The file or archive to upload")
        upload_grp.add_argument("--case-id", action="store", dest="case_id",
                                help="specify case identifier")
        upload_grp.add_argument("--upload-url", default=None,
                                help="Upload the archive to specified server")
        upload_grp.add_argument("--upload-user", default=None,
                                help="Username to authenticate with")
        upload_grp.add_argument("--upload-pass", default=None,
                                help="Password to authenticate with")
        upload_grp.add_argument("--upload-directory", action="store",
                                dest="upload_directory",
                                help="Specify upload directory for archive")
        upload_grp.add_argument("--upload-s3-endpoint", default=None,
                                help="Endpoint to upload to for S3 bucket")
        upload_grp.add_argument("--upload-s3-region", default=None,
                                help="Region to upload to for S3 bucket")
        upload_grp.add_argument("--upload-s3-bucket", default=None,
                                help="Name of the S3 bucket to upload to")
        upload_grp.add_argument("--upload-s3-access-key", default=None,
                                help="Access key for the S3 bucket")
        upload_grp.add_argument("--upload-s3-secret-key", default=None,
                                help="Secret key for the S3 bucket")
        upload_grp.add_argument("--upload-s3-object-prefix", default=None,
                                help="Prefix for the S3 object/key")
        upload_grp.add_argument("--upload-method", default='auto',
                                choices=['auto', 'put', 'post'],
                                help="HTTP method to use for uploading")
        upload_grp.add_argument("--upload-protocol", default='auto',
                                choices=['auto', 'https', 'ftp', 'sftp', 's3'],
                                help="Manually specify the upload protocol")
        upload_grp.add_argument("--upload-no-ssl-verify", default=False,
                                action='store_true',
                                help="Disable SSL verification for upload url")
        upload_grp.add_argument("--upload-profile", default='local',
                                choices=['redhat', 'ubuntu', 'local'],
                                help=("Manually specify vendor-specific "
                                      "profile for uploads. Supported "
                                      "options are:\n"
                                      "redhat, ubuntu, local"))

    @classmethod
    def display_help(cls, section):
        section.set_title('SoS Upload Detailed Help')

        section.add_text(
            'The upload command is designed to upload already existing '
            'sos reports, as well as other files like logs and vmcores '
            'to a distribution specific location.'
        )

    def _fmt_msg(self, msg):
        width = 80
        _fmt = ''
        for line in msg.splitlines():
            _fmt = _fmt + fill(line, width, replace_whitespace=False) + '\n'
        return _fmt

    def intro(self):
        """Print the intro message and prompts for a case ID if one is not
        provided on the command line
        """
        disclaimer = """\
This utility is used to upload files to a profile location \
based either on a command line option or detecting the local \
distribution.

The archive to be uploaded may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No configuration changes will be made to the system running \
this utility.
"""
        self.ui_log.info(f"\nsos upload (version {__version__})")
        intro_msg = self._fmt_msg(disclaimer)
        self.ui_log.info(intro_msg)

        prompt = "\nPress ENTER to continue, or CTRL-C to quit\n"
        if not self.opts.batch:
            try:
                input(prompt)
                self.ui_log.info("")
            except KeyboardInterrupt:
                self._exit("Exiting on user cancel", 130)
            except Exception as e:
                self._exit(e, 1)

    def get_commons(self):
        return {
            'cmdlineopts': self.opts,
            'policy': self.policy,
            'case_id': self.opts.case_id,
            'upload_directory': self.opts.upload_directory
        }

    def set_commons(self, commons):
        """Set common host data for the Upload profiles
            to reference
        """
        self.commons = commons

    def set_upload_profile(self):
        if self.opts.upload_profile:
            if self.opts.upload_profile == "redhat":
                return self.load_upload_profile(self.profiles_data['redhat'])
            if self.opts.upload_profile == "ubuntu":
                return self.load_upload_profile(self.profiles_data['ubuntu'])
        return self.determine_local_profile()

    def load_upload_profile(self, profile):
        try:
            upload_mod = importlib.import_module(
                profile['mod']
            )
            upload_class = getattr(upload_mod, profile['class'])
            upload = (
                upload_class(
                            parser=self.parser,
                            args=self.args,
                            cmdline=self.cmdline
                )
            )
            upload.set_commons(self.get_commons())
            return upload
        except ImportError as e:
            self.ui_log.error(f"{profile['description']} upload "
                              f"profile not available: {e}")
            return None

    def determine_local_profile(self):
        self.ui_log.info(
            "Trying to determine local upload profile..."
        )

        from sos.policies.distros.redhat import RHELPolicy
        from sos.policies.distros.ubuntu import UbuntuPolicy

        if isinstance(self.policy, RHELPolicy):
            return self.load_upload_profile(self.profiles_data['redhat'])
        if isinstance(self.policy, UbuntuPolicy):
            return self.load_upload_profile(self.profiles_data['ubuntu'])
        self.ui_log.info(
            "Couldn't determine local profile. Using generic profile."
        )
        return self.load_upload_profile(self.profiles_data['default'])

    def pre_work(self):
        # This method will be called before upload begins
        self.commons = self.get_commons()
        cmdline_opts = self.commons['cmdlineopts']

        if cmdline_opts.low_priority:
            self.policy._configure_low_priority()

    def execute(self):
        self.pre_work()
        if self.from_cmdline:
            self.intro()
            self.archive = self.opts.upload_file
        self.upload_profile = self.set_upload_profile()
        try:
            if os.stat(self.archive).st_size > 0:
                if os.path.isfile(self.archive):
                    try:
                        # Check local profile that was either selected
                        # via the command line option, or detected locally
                        if self.upload_profile:
                            self.upload_profile.upload_archive(self.archive)
                        else:
                            # There was no upload profile set, so we'll throw
                            # an error here
                            self.ui_log.error(
                                "No upload profile found. Exiting"
                            )
                            sys.exit(1)
                        self.ui_log.info(
                            _(f"File {self.archive} uploaded successfully")
                        )
                    except Exception as err:
                        self.ui_log.error(_(f"Upload attempt failed: {err}"))
                        sys.exit(1)
                else:
                    self.ui_log.error(_(f"{self.archive} is not a file."))
            else:
                self.ui_log.error(_(f"File {self.archive} is empty."))
        except Exception as e:
            self.ui_log.error(_(f"Cannot upload {self.archive}: {e} "))

# vim: set et ts=4 sw=4 :
