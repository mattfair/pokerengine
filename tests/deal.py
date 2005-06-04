#
# Copyright (C) 2004, 2005 Mekensleep
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#

import sys, os
sys.path.insert(0, "..")

from random import shuffle
import unittest
from pokerengine.pokergame import PokerGameServer
from pokerengine.pokerchips import PokerChips
from pokerengine.pokercards import PokerCards
from pokereval import PokerEval

poker_eval = PokerEval()
_initial_money = 10

class TestDeal(unittest.TestCase):

    def setUp(self):
        self.game = PokerGameServer("poker.%s.xml", [ "../conf" ])
        self.game.verbose = 3
        self.game.setVariant("7stud")
        self.game.setBettingStructure("0-0-limit")

    def tearDown(self):
        del self.game

    def log(self, string):
        print string

    def make_new_player(self, i, initial_money):
        self.assert_(self.game.addPlayer(i))
        player = self.game.serial2player[i]
        player.money = PokerChips(self.game.chips_values, initial_money)
        player.buy_in_payed = True
        self.assert_(self.game.sit(i))
        player.auto_blind_ante = True

    def test1(self):
        """
        8 players, non fold, last card is a community card
        """
        game = self.game
        for serial in xrange(1,9):
            self.make_new_player(serial, 200)
        game.beginTurn(1)
        while True:
            if game.isLastRound():
                self.assertEqual(len(game.board.tolist(True)) == 1)

            for x in xrange(1,9):
                serial = game.getSerialInPosition()
                self.assertEqual(game.check(serial), True)
                    
            if not game.isRunning():
                break;

def run():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDeal))
    unittest.TextTestRunner(verbosity=2).run(suite)
    
if __name__ == '__main__':
    run()
