import subprocess
import unittest
from unittest.mock import patch

from benchmark import measure

class LifecycleTests(unittest.TestCase):
    def test_success_still_cleans_up_with_bounded_docker_grace(self):
        with patch("benchmark.subprocess.run") as command, patch(
            "benchmark.check_targets", return_value=[]
        ):
            command.side_effect = [
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, stdout="127.0.0.1:20001\n"),
                subprocess.CompletedProcess([], 0, stdout="127.0.0.1:20002\n"),
                subprocess.CompletedProcess([], 0),
            ]
            self.assertEqual(measure("cold")["mode"], "cold")
            cleanup = command.call_args.args[0]
            self.assertEqual(cleanup[cleanup.index("down"):],
                             ["down", "--timeout", "2", "--volumes", "--remove-orphans"])
            self.assertTrue(command.call_args.kwargs["check"])
            self.assertGreater(command.call_args.kwargs["timeout"], 8)
