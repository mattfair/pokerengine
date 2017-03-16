#
# Copyright (C) 2006 - 2010 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
#  Loic Dachary <loic@dachary.org>
#
import os
from os.path import exists, expanduser, abspath, isfile
from pokerengine.version import Version, version
from pokerengine import log as engine_log
log = engine_log.get_child('config')
import re

from lxml import etree

class Config:

    upgrades_repository = None
    upgrade_dry_run = False

    def __init__(self, dirs):
        self.path = None
        self.header = None
        self.doc = None
        self.dirs = [ expanduser(dir) for dir in dirs ]
        self.version = version

    def __del__(self):
        self.free()

    def free(self):
        self.doc = None
        self.header = None

    def reload(self):
        self.free()
        self.doc = etree.XML(open(self.path, 'r').read())

    def load(self, path):
        for prefix in self.dirs:
            tmppath = abspath(expanduser((prefix + "/" + path) if prefix and path[0] != "/" else path ))
            if exists(tmppath):
                self.path = tmppath
                break
        self.free()
        if self.path:
            self.doc = etree.XML(open(self.path, 'r').read())
            if Config.upgrades_repository:
                self.checkVersion("poker_engine_version", version, Config.upgrades_repository)
            return True
        else:
            raise Exception("load: unable to find '%s' in directories %s" % (path, self.dirs))
            return False

    def checkVersion(self, version_attribute, software_version, upgrades_repository, default_version = "1.0.5"):
        for record in self.doc:
            if record is not None:
                version_node = record.xpath("/child::*/@" + version_attribute)
                if len(version_node) > 0:
                    version_node = version_node[0]
        if not version_node:
            self.doc.attrib[version_attribute] = default_version
            if not self.upgrade_dry_run:
                self.save()
            file_version = Version(default_version)
            log.inform("checkVersion: '%s': set default version to %s", self.path, default_version)
        else:
            file_version = Version(version_node)

        if software_version != file_version:
            if software_version > file_version:
                log.inform("checkVersion: '%s': launch upgrade from %s to %s using repository %s",
                    self.path,
                    file_version,
                    software_version,
                    upgrades_repository
                )
                self.upgrade(version_attribute, file_version, software_version, upgrades_repository)
                return False
            else:
                raise Exception, "Config: %s requires an upgrade to software version %s or better" % ( self.path, str(file_version) )
        else:
            log.inform("checkVersion: '%s': up to date", self.path)
            return True

    def upgrade(self, version_attribute, file_version, software_version, upgrades_repository):
        if upgrades_repository and os.path.exists(upgrades_repository):
            files = map(lambda f: upgrades_repository + "/" + f, os.listdir(upgrades_repository))
            files = filter(lambda f: isfile(f) and ".xsl" in f, files)
            for upgradefile in file_version.upgradeChain(software_version, files):
                log.inform("upgrade: '%s' with '%s'", self.path, upgradefile)
                xslt_root = etree.XML(open(upgradefile, 'r').read())
                transform = etree.XSLT(xslt_root)
                result = etree.tostring(transform(self.doc))

                if not self.upgrade_dry_run:
                    output_file = open(self.path, 'w')
                    output_file.write(result)
                    output_file.close()

                if not self.upgrade_dry_run:
                    self.reload()
        else:
            log.inform("upgrade: '%s' is not a directory, ignored", upgrades_repository)
        if not self.upgrade_dry_run:
            self.headerSet("/child::*", version_attribute, str(software_version))
            self.save()

    def save(self):
        if not self.path:
            log.error("save: unable to write back, invalid path")
            return
        xmlFile = open(self.path, 'w')
        xmlFile.write(etree.tostring(self.doc, pretty_print=True))
        xmlFile.close()

    def headerGetList(self, name):
        result = self.doc.xpath(name)
        if len(result)>0 and (type(result[0]) == etree.Element or type(result[0]) == etree._Element):
            lst = []
            for o in result:
                if o.text == None:
                    lst.append('')
                else:
                    lst.append(o.text)
            return lst
        else:
            return [o for o in result]

    def headerGetInt(self, name):
        string = self.headerGet(name)
        if re.match("[0-9]+$", string):
            return int(string)
        else:
            return 0

    def headerGet(self, name):
        results = self.doc.xpath(name)
        if type(results) == str:
            return results
        elif len(results)>0 and (type(results[0]) == etree.Element or type(results[0]) == etree._Element):
            return results[0].text
        else:
            if len(results) > 0:
                return results[0]
            elif len(results) == 0 and type(results) == list:
                return ''
            else:
                return results

    def headerSet(self, parent, name, value):
        header = self.doc.xpath(parent)[0]
        if name in header.attrib.keys():
            header.attrib[name] = value
        else:
            raise IndexError

    def headerGetProperties(self, name):
        results = []
        for node in self.doc.xpath(name):
            results.append(self.headerNodeProperties(node))
        return results

    def headerNodeProperties(self, node):
        return node.attrib
