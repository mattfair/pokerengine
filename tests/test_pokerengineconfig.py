#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2006 - 2010 Loic Dachary <loic@dachary.org>
# Copyright (C) 2006 Mekensleep
#
# Mekensleep
# 26 rue des rosiers
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#  Pierre-Andre (05/2006)
#  Loic Dachary <loic@dachary.org>
#

import unittest, sys
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

import os
import shutil
import tempfile
from lxml import etree

from pokerengine import version
from pokerengine import version_number
from pokerengine import pokerengineconfig

class PokerEngineConfigTestCase(unittest.TestCase):

    TestConfDirectory = path.join(TESTS_PATH, 'test-data/conf')
    TestUpgradeDirectory = path.join(TESTS_PATH, 'test-data/upgrade')

    TestConfigInvalidFile = 'unittest.config.invalid.xml'
    TestConfigNotFoundFile = 'unittest.config.notfound.xml'
    TestConfigTemplateFile = 'unittest.config.template.xml'

    TestUpgradeInvalidFile = 'unittest.config.invalid.xsl'
    TestUpgradeTemplateFile = 'unittest.config.template.xsl'

    TestConfigTemporaryFile = 'unittest.config.xml'


    # -----------------------------------------------------------------------------------------------------
    def setUp(self):
        def callback(ctx, str):
            pass #FIXME! if self.verbose >= 0: print "%s %s" % (ctx, str)
        #libxml2.registerErrorHandler(callback, "-->")
        self.Config = pokerengineconfig.Config([PokerEngineConfigTestCase.TestConfDirectory, tempfile.gettempdir()])

        self.ConfigTmplFile = path.join(PokerEngineConfigTestCase.TestConfDirectory, PokerEngineConfigTestCase.TestConfigTemplateFile)
        self.ConfigTempFile = path.join(tempfile.gettempdir(), PokerEngineConfigTestCase.TestConfigTemporaryFile)

        self.UpgradeTmplFile = path.join(PokerEngineConfigTestCase.TestUpgradeDirectory, PokerEngineConfigTestCase.TestUpgradeTemplateFile)
        self.UpgradeInvalidFile = path.join(PokerEngineConfigTestCase.TestUpgradeDirectory, PokerEngineConfigTestCase.TestUpgradeInvalidFile)

        if not self.CopyFile(self.ConfigTmplFile, self.ConfigTempFile):
            self.fail('Error during creation of configuration file ' + self.ConfigTempFile)

    # -----------------------------------------------------------------------------------------------------
    def tearDown(self):
        # self.DeleteFile(self.ConfigTempFile)
        pass
    # -----------------------------------------------------------------------------------------------------
    def testHeaderGet(self):
        """Test Poker Engine : Get header value"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestHeader', {'key' : 'val'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        self.failUnlessEqual(self.Config.headerGet('/bet/TestHeader/@key'), 'val')

    # -----------------------------------------------------------------------------------------------------
    def testHeaderSet(self):
        """Test Poker Engine : Set header value"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet','TestHeader', {'key1' : 'val1'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        self.Config.headerSet('/bet/TestHeader','key1','val2')
        self.failUnlessEqual(self.Config.headerGet('/bet/TestHeader/@key1'), 'val2')

        # Attribut not found
        self.failUnlessRaises(IndexError,self.Config.headerSet,'/bet/TestHeader', 'key2','val2')
        self.failUnlessEqual(self.Config.headerGet('/bet/TestHeader/@key2'), '')

    # -----------------------------------------------------------------------------------------------------
    def testHeaderGetInt(self):
        """Test Poker Engine : Get attribute value as integer"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestInt', {'int' : '500'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        self.failUnlessEqual(self.Config.headerGetInt('/bet/TestInt/@int'),500)

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestInt', {'int' : 'AB'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.Config.reload()
        self.failUnlessEqual(self.Config.headerGetInt('/bet/TestInt/@int'), 0)

    # -----------------------------------------------------------------------------------------------------
    def testHeaderGetList(self):
        """Test Poker Engine : Get list"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestList', {'attribute1' : 'val1', 'attribute2' : 'val2', 'attribute3' : 'val3'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        values = self.Config.headerGetList('/bet/TestList/@*')
        values.sort()
        self.failUnlessEqual(values, ['val1', 'val2', 'val3'])

    # -----------------------------------------------------------------------------------------------------
    def testHeaderGetProperties(self):
        """Test Poker Engine : Get properties"""

        properties = {'attribute1' : 'val1', 'attribute2' : 'val2', 'attribute3' : 'val3'}
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestProperties', properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        self.failUnlessEqual(self.Config.headerGetProperties('/bet/TestProperties')[0], properties)

    # -----------------------------------------------------------------------------------------------------
    def testSave(self):
        """Test Poker Engine : Save"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, {'attribute1' : 'val1'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.failUnlessEqual(self.Config.save(), None)
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))
        self.failUnlessEqual(self.Config.save(), None)

    # -----------------------------------------------------------------------------------------------------
    def testConfigLoadFileNotFound(self):
        """Test Poker Engine : Load file not found"""
        try:
            self.Config.load(PokerEngineConfigTestCase.TestConfigNotFoundFile)
            self.fail("Found file, although it shouldn't")
        except:
            pass

    # -----------------------------------------------------------------------------------------------------
    def testConfigLoadInvalidFile(self):
        """Test Poker Engine : Load invalid file"""

        self.failUnlessRaises(etree.XMLSyntaxError,self.Config.load,PokerEngineConfigTestCase.TestConfigInvalidFile)

    # -----------------------------------------------------------------------------------------------------
    def testConfigLoadValidFile(self):
        """Test Poker Engine : Load file"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, {'poker_engine_version' : version_number}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        pokerengineconfig.Config.upgrades_repository = './NotFound'
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        pokerengineconfig.Config.upgrades_repository = PokerEngineConfigTestCase.TestUpgradeDirectory
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

    # -----------------------------------------------------------------------------------------------------
    def testConfigReload(self):
        """Test Poker Engine : Reload file"""

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestReload', {'key' : 'val1'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        pokerengineconfig.Config.upgrades_repository = None
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        key_value = self.Config.headerGet('/bet/TestReload/@key')
        self.failUnlessEqual(key_value, 'val1')

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'TestReload', {'key' : 'val2'}):
            self.fail('Error during configuration file modification' + self.ConfigTempFile)

        key_value = self.Config.headerGet('/bet/TestReload/@key')
        self.failUnlessEqual(key_value, 'val1')

        self.Config.reload()
        key_value = self.Config.headerGet('/bet/TestReload/@key')
        self.failUnlessEqual(key_value, 'val2')

    # -----------------------------------------------------------------------------------------------------
    def testConfigCheckVersionUpToDate(self):
        """Test Poker Engine : Check version up to date"""

        pokerengineconfig.Config.upgrades_repository = None
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, {'poker_engine_version' : version_number}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))
        self.failUnless(self.Config.checkVersion('poker_engine_version',version_number,None))

    # -----------------------------------------------------------------------------------------------------
    def testConfigCheckVersionWithoutVersion(self):
        """Test Poker Engine : Check file version without version attribute"""

        pokerengineconfig.Config.upgrades_repository = None
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Save the version information
        pokerengineconfig.Config.upgrade_dry_run = False
        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))
        self.failUnless(self.Config.checkVersion('poker_engine_version',version_number,None,version_number))

        self.Config.reload()
        self.failUnlessEqual(self.Config.headerGet('/bet/@poker_engine_version'), version_number)

    # -----------------------------------------------------------------------------------------------------
    def testConfigCheckVersionWithInvalidVersion(self):
        """Test Poker Engine : Check file version with invalid version attribute"""

        pokerengineconfig.Config.upgrades_repository = None
        ver = version.Version(version_number)

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, {'poker_engine_version' : str(ver + 1)}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))
        self.failUnlessRaises(Exception,self.Config.checkVersion,'poker_engine_version',str(ver), None)

    # -----------------------------------------------------------------------------------------------------
    def testConfigCheckVersionUpgrade(self):
        """Test Poker Engine : Check file version upgrade"""

        pokerengineconfig.Config.upgrade_dry_run = True
        pokerengineconfig.Config.upgrades_repository = None
        ver = version.Version(version_number)

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, {'poker_engine_version' : str(ver), 'upgrade' : 'ToUpgrade'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))
        self.failIf(self.Config.checkVersion('poker_engine_version',str(ver+1),None))

        upgrade_file = 'upgrade' + str(ver) + '-' + str(ver + 1) + '.xsl'
        upgrade_file = path.join(tempfile.gettempdir(),upgrade_file)
        if not self.CopyFile(self.UpgradeTmplFile, upgrade_file):
            self.fail('Error during creation of upgrade file ' + upgrade_file)

        pokerengineconfig.Config.upgrade_dry_run = False
        self.failIf(self.Config.checkVersion('poker_engine_version',str(ver+1),tempfile.gettempdir()))
        self.failUnlessEqual(self.Config.headerGet('/bet/@upgrade'), 'Upgraded')

        self.DeleteFile(upgrade_file)

    # -----------------------------------------------------------------------------------------------------
    def testConfigCheckVersionInvalidUpgrade(self):
        """Test Poker Engine : Check file version invalid upgrade"""

        pokerengineconfig.Config.upgrade_dry_run = False
        pokerengineconfig.Config.upgrades_repository = None
        ver = version.Version(version_number)

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, {'poker_engine_version' : str(ver), 'upgrade' : 'ToUpgrade'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.failUnless(self.Config.load(PokerEngineConfigTestCase.TestConfigTemporaryFile))

        upgrade_file = 'upgrade' + str(ver) + '-' + str(ver + 1) + '.xsl'
        upgrade_file = path.join(tempfile.gettempdir(),upgrade_file)
        if not self.CopyFile(self.UpgradeInvalidFile, upgrade_file):
            self.fail('Error during creation of upgrade file ' + upgrade_file)

        self.failUnlessRaises(etree.XMLSyntaxError,self.Config.checkVersion, 'poker_engine_version',str(ver+1),tempfile.gettempdir())
        self.DeleteFile(upgrade_file)

    # -----------------------------------------------------------------------------------------------------
    def ModifyXMLFile(self, path, parent, child, attributes = {}):
        doc = etree.XML(open(path, 'r').read())
        node_parent = nodes = doc.xpath(parent)[0]
        child_path = parent

        if child != None:
            child_path += '/' + child

        nodes = doc.xpath(child_path)
        if len(nodes) > 0:
            node = nodes[0]
        else:
            node = etree.SubElement(node_parent, child)

        for attribute_name, attribute_value in attributes.items():
            node.attrib[attribute_name] = attribute_value

        xmlFile = open(path, 'w')
        xmlFile.write(etree.tostring(doc, pretty_print=True))
        xmlFile.close()

        return True

    # -----------------------------------------------------------------------------------------------------
    def CopyFile(self, src_path, dst_path):
        if src_path and not path.isfile(src_path):
            return False

        shutil.copyfile(src_path,dst_path)
        if path.isfile(dst_path):
            return True

        return False

    # -----------------------------------------------------------------------------------------------------
    def DeleteFile(self, file_path):
        if path.isfile(file_path):
            os.unlink(file_path)

# -----------------------------------------------------------------------------------------------------
def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerEngineConfigTestCase))
    # Comment out above and use line below this when you wish to run just
    # one test by itself (changing prefix as needed).
#    suite.addTest(unittest.makeSuite(PokerEngineConfigTestCase, prefix = "test2"))
    return suite

# -----------------------------------------------------------------------------------------------------
def GetTestedModule():
    return pokerengineconfig

# -----------------------------------------------------------------------------------------------------
def run():
    return unittest.TextTestRunner().run(GetTestSuite())

# -----------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    if run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "( cd .. ; ./config.status tests/test-pokerengineconfig.py ) ; ( cd ../tests ; make COVERAGE_FILES='../pokerengine/pokerengineconfig.py' TESTS='coverage-reset test-pokerengineconfig.py coverage-report' check )"
# End:
