from os import makedirs, environ
from shutil import copy, rmtree
from subprocess import Popen, PIPE
import unittest

# It must be set before import "utils"
environ["SVAROG_CONFIG_DIR"] = "tests/config"

from utils.globalvars import CONFIG_DIRECTORY  # noqa: E402

CLI = "./cli.py"


class TestCli(unittest.TestCase):

    def setUp(self):
        makedirs(CONFIG_DIRECTORY, exist_ok=True)
        copy("tests/config.yml", CONFIG_DIRECTORY)

    def tearDown(self):
        rmtree(CONFIG_DIRECTORY, ignore_errors=True)

    def run_cmd(self, binfile, params, env=None):
        """Runs file specified as binfile, passes all parameters.
        Returns a pair of returncode, stdout"""
        par = [binfile]
        if params and len(params):
            par += params

        # @todo: set passed env variable, if any
        p = Popen(par, stdout=PIPE)
        output = p.communicate()[0]
        return p.returncode, output.decode("utf-8")

    def check_output(self, output: str, strings):
        """Checks if specified output (presumably stdout) has appropriate content. strings
        is a list of strings that are expected to be present. They're expected
        to appear in the specified order, but there may be other things
        printed in between them. Will assert if string is not found. Returns number
        of found strings."""
        offset = 0
        cnt = 0
        for s in strings:
            new_offset = output.find(s, offset)

            if (new_offset == -1):
                assert False, "Not found an expected string: '%s'" % s

            cnt += 1
        return cnt

    def check_file(self, file, strings):
        """Checks if specified file contains specified strings."""
        with open(file, "r") as f:
            content = f.read()

        self.check_output(content, strings)

    def check_command(self, bin, params, exp_code=0, exp_strings=[]):
        """Runs specified command (bin) with parameters (params) and expected
        the return code to be exp_code. Returns the standard output."""

        # Run the command
        result = self.run_cmd(bin, params)

        assert result[0] == exp_code

        if (len(exp_strings)):
            self.check_output(result[1], exp_strings)

        return result[1]

    def test_cli_exec(self):
        """Checks if the cli.py file is there and is executable."""
        import os
        assert os.access(CLI, os.X_OK)

    def test_cli_config(self):
        """ Checks that cli config returns the expected content. Note the setUp() method
            copied over tests/config.yml, so we know exactly what to expect. """
        exp = ["{'aos_at': 12,",
               "'elevation': 123",
               "'latitude': 45.6",
               "'longitude': 78.9",
               "'name': 'Secret Lair'",
               "'max_elevation_greater_than': 0",
               "https://celestrak.org/NORAD/elements/gp.php?GROUP=noaa&FORMAT=tle",
               "{'freq': '137.62e6', 'name': 'NOAA 15'}",
               "{'freq': '137.9125e6', 'name': 'NOAA 18'}",
               "{'freq': '137.1e6', 'name': 'NOAA 19'}",
               "'server': {'id': 1,",
               "'secret': '1234567890abcdef01234567890abcde'",
               "'url': 'http://127.0.0.1:5000/receive'},",
               "'strategy': 'max-elevation'}"]
        self.check_command(CLI, ["config"], 0, exp)

    def test_cli_config_location(self):
        """Checks if cli config location returns the actual location."""
        self.check_command(CLI, ["config", "location"], 0,
                           ["{'elevation': 123, 'latitude': 45.6, 'longitude': 78.9, 'name': 'Secret Lair'}"])

    def test_cli_help(self):
        """Checks if help is printed and has reasonable information."""

        exp = ["usage: svarog [-h] {clear,logs,plan,pass,config,obs,metadata}",
               "positional arguments:",
               "{clear,logs,plan,pass,config,obs,metadata}",
               "clear               Clear all scheduled reception events",
               "logs                Show logs",
               "plan                Schedule planned reception events",
               "pass                Information about passes",
               "config              Configuration",
               "obs                 Local observations management",
               "metadata            Displays metadata",
               "-h, --help            show this help message and exit"
               ]
        exp_code = 0

        self.check_command(CLI, None, exp_code, exp)

    def test_plan(self):
        """Checks if cli.py plan really schedules anything in cron."""

        # Set the DEV_ENVIRONMENT, so the cron script writes to a crontab file in ./config/crontab rather than the
        # actual crontab file, but don't enable max logging.
        environ["DEV_ENVIRONMENT"] = "2"

        self.check_command(CLI, ["plan"], 0, ["Trying to set up cron job for periodic updates.", "At 04:00, every day"])

        del environ["DEV_ENVIRONMENT"]

        # This is not perfect, but it's better than nothing. It checks if the crontab file contains the following strings in
        # order. In fact, the entries should be:
        #
        # 55 3 * * * /home/thomson/devel/svarog/station/update.sh # svarog-update
        # 0 4 * * * python3 /home/thomson/devel/svarog/station/planner.py 86400 # svarog-plan
        # However, the /home/thomson/devel/svarog is very much deployment specific. So, we use a simplified approach
        # and just check if the beginnings and ends match.
        self.check_file("tests/config/crontab", ["55 3 * * *", "/station/update.sh # svarog-update",
                                                 "0 4 * * * python3", "station/planner.py 86400 # svarog-plan"])

    def test_pass(self):
        """Checks if cli.py pass can produce diagrams properly."""

        # The actual output produced are different. Testing exact output would be problematic (would need to add capability
        # to force specific time, also fake inserting TLE data into the database). Instead, we check couple things:
        # that the return code is 0 (it's 1 if there's an exception thrown), that some of the pass details, axes,
        # axes descriptions, and legend are shown.
        txt = self.check_command(CLI, ["pass", "NOAA 19"], 0,
                                 ["AOS:", "LOS:", "Duration:", "Red dot is AOS point", "⠒⡗⠒", "⠒⠒⠒⠒⠒⠒⠒", "(Degrees)  ^", "Time (local)", "Legend:",
                                  "⠤⠤ Azimuth", "⠤⠤ Elevation * 4"])

        # Ok, that's a lame check. But it's better than nothing.
        self.assertNotEqual(txt, "")
