#
# Copyright (C) 2005 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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
#  Loic Dachary <loic@gnu.org>
#

import sys, os
sys.path.insert(0, "..")

from pprint import pprint
import unittest
from pokerengine.pokergame import PokerGameServer

class TestSit(unittest.TestCase):

    def setUp(self):
        self.game = PokerGameServer("poker.%s.xml", [ "../conf" ])
        self.game.verbose = 3
        self.game.setVariant("holdem")
        self.game.setBettingStructure("2-4-limit")

    def tearDown(self):
        del self.game

    def log(self, string):
        print string

    def make_new_player(self, serial, seat):
        game = self.game
        self.failUnless(game.addPlayer(serial, seat))
        self.failUnless(game.payBuyIn(serial, game.buyIn()))
        self.failUnless(game.sit(serial))

    def pay_blinds(self):
        game = self.game
        for serial in game.serialsAll():
            game.autoBlindAnte(serial)
        for serial in game.serialsAll():
            game.noAutoBlindAnte(serial)

    def bot_players(self):
        game = self.game
        for serial in game.serialsAll():
            game.botPlayer(serial)
        
    def check_blinds(self, descriptions):
        players = self.game.playersAll()
        players.sort(lambda a,b: int(a.seat - b.seat))
        for player in players:
            (blind, missed, wait) = descriptions.pop(0)
            if(blind != player.blind or missed != player.missed_blind or wait != player.wait_for):
                print "check_blinds FAILED actual %s != from expected %s" % ( (player.blind, player.missed_blind, player.wait_for), (blind, missed, wait) )
                self.fail()
            
            
    def test1(self):
        for (serial, seat) in ((1, 0), (2, 1)):
            self.make_new_player(serial, seat)
        self.game.beginTurn(1)
        #
        # New player comes in while others are paying the blinds.
        # He does not participate in the game.
        #
        for (serial, seat) in ((3, 2),):
            self.make_new_player(serial, seat)
        self.pay_blinds()
        self.assertEqual(self.game.player_list, [1,2])
        self.bot_players()

        #
        # Next round the new player is waiting for the late blind
        #
        self.game.beginTurn(2)
        self.assertEqual(self.game.player_list, [1,2])
        self.pay_blinds()

        #
        # This round the new player is in
        #
        self.game.beginTurn(3)
        self.assertEqual(self.game.player_list, [1,2,3])
        self.pay_blinds()

def run():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSit))
    unittest.TextTestRunner(verbosity=2).run(suite)
    
if __name__ == '__main__':
    run()