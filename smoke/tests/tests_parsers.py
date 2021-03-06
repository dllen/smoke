# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import uuid

from django.test import TestCase
from smoke.services.parsers import ApplicationMasterLaunchedParser, \
    TaskFinishedWithProgressParser, MessageFromShellParser
from smoke.tests.utils import MessageServiceMock


GENERAL_INVALID_LINES = (

    # empty line
    "",

    # line with some characters
    "xxxxxx",

    # a real line, but any parser handles it
    ("14/08/23 12:48:53 INFO scheduler.DAGScheduler: "
     "Completed ShuffleMapTask(1, 0)")

)


class TestApplicationMasterLaunchedParser(TestCase):

    def test(self):
        cookie = uuid.uuid4().hex
        msg_service = MessageServiceMock()
        parser = ApplicationMasterLaunchedParser(msg_service, cookie)

        LINE = ("14/09/13 12:22:52 INFO yarn.Client: Command for starting "
                "the Spark ApplicationMaster: List($JAVA_HOME/bin/java, "
                "-server, -Xmx512m, -Djava.io.tmpdir=$PWD/tmp, "
                "--executor-memory, 1024, --executor-cores, 2, "
                "--num-executors , 2, 1>, <LOG_DIR>/stdout, 2>, "
                "<LOG_DIR>/stderr)")

        for invalid_line in GENERAL_INVALID_LINES:
            self.assertFalse(parser.parse(invalid_line))

        self.assertTrue(parser.parse(LINE))

        appMasterLaunched = [item.get('appMasterLaunched', False)
                             for sublist in msg_service.messages
                             for item in sublist
                             if isinstance(item, dict)]

        self.assertIn(True, appMasterLaunched)


class TestTaskFinishedWithProgressParser(TestCase):

    def test(self):
        cookie = uuid.uuid4().hex
        msg_service = MessageServiceMock()
        parser = TaskFinishedWithProgressParser(msg_service, cookie)

        LINE = ("14/08/23 12:48:53 INFO "
                "scheduler.TaskSetManager: "
                "Finished TID 0 in 7443 ms on "
                "hadoop-hitachi80gb.hadoop.dev.docker.data-tsunami.com "
                "(progress: 4/10)")

        for invalid_line in GENERAL_INVALID_LINES:
            self.assertFalse(parser.parse(invalid_line))

        self.assertTrue(parser.parse(LINE))

        progressUpdate = [item.get('progressUpdate', False)
                          for sublist in msg_service.messages
                          for item in sublist
                          if isinstance(item, dict)]

        self.assertIn(True, progressUpdate)


class TestMessageFromShellParser(TestCase):

    def test_invalid_lines(self):
        cookie = uuid.uuid4().hex
        msg_service = MessageServiceMock()
        parser = MessageFromShellParser(msg_service, cookie)

        INVALID_LINES = (
            "@@@@",
            "@@some text@@",
            "@@<some_xml></some_xml>@@",
            "@@<msgFromShell></msgFromShell>@@",
            "@@<msgFromShell><errorLine>ERR</errorLine></msgFromShell>@@",
        )

        # -----

        for invalid_line in GENERAL_INVALID_LINES:
            self.assertFalse(parser.parse(invalid_line))

        for invalid_line in INVALID_LINES:
            self.assertFalse(parser.parse(invalid_line))

    def test_wrong_cookie(self):
        cookie = uuid.uuid4().hex
        wrong_cookie = uuid.uuid4().hex
        msg_service = MessageServiceMock()
        parser = MessageFromShellParser(msg_service, cookie)

        WRONG_COOKIE = ("@@"
                        "<msgFromShell cookie='{0}'>"
                        "<errorLine>This is the line</errorLine>"
                        "</msgFromShell>"
                        "@@".format(wrong_cookie))

        # -----

        self.assertFalse(parser.parse(WRONG_COOKIE))

    def test_errorLine_is_parsed(self):
        cookie = uuid.uuid4().hex
        msg_service = MessageServiceMock()
        parser = MessageFromShellParser(msg_service, cookie)

        error_msg = "This-is-the-line-" + uuid.uuid4().hex
        LINE = ("@@"
                "<msgFromShell cookie='{0}'>"
                "<errorLine>{1}</errorLine>"
                "</msgFromShell>"
                "@@".format(cookie,
                            error_msg))

        # -----

        self.assertTrue(parser.parse(LINE))

        error_msg_found = [error_msg == item
                           for sublist in msg_service.messages
                           for item in sublist]

        self.assertIn(True, error_msg_found)

    def test_outputFileName_is_parsed(self):
        cookie = uuid.uuid4().hex
        msg_service = MessageServiceMock()
        parser = MessageFromShellParser(msg_service, cookie)

        output_filename = "/tmp/output-file-" + uuid.uuid4().hex
        LINE = ("@@"
                "<msgFromShell cookie='{0}'>"
                "<outputFileName>{1}</outputFileName>"
                "</msgFromShell>"
                "@@".format(cookie,
                            output_filename))

        # -----

        self.assertTrue(parser.parse(LINE))

        outputFilenameReported = [item.get('outputFilenameReported', False)
                                  for sublist in msg_service.messages
                                  for item in sublist
                                  if isinstance(item, dict)]

        self.assertIn(output_filename, outputFilenameReported)
