#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

import os
import sys
import shutil
import string
import tempfile
import math
import unittest
from lxml import etree

from os import path
TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from tests.log_history import log_history

from collections import namedtuple

from pokerengine import pokercards
from pokerengine import pokergame

from tests.testmessages import search_output, clear_all_messages, get_messages
try:
    from nose.plugins.attrib import attr
except ImportError, e:
    def attr(fn): return fn

CallbackIds = None
CallbackArgs = None

# ---------------------------------------------------------
def InitCallback():
    global CallbackIds
    global CallbackArgs

    CallbackIds = None
    CallbackArgs = None

# ---------------------------------------------------------
def Callback(id, *args):
    global CallbackIds
    global CallbackArgs

    if not CallbackIds: CallbackIds = []
    if not CallbackArgs: CallbackArgs = []

    CallbackIds.append(id)
    CallbackArgs.append(args)

# ---------------------------------------------------------
class PokerPredefinedDecks:
    def __init__(self, decks):
        self.decks = decks
        self.index = 0

    def shuffle(self, deck):
        deck[:] = self.decks[self.index][:]
        self.index += 1
        if self.index >= len(self.decks):
            self.index = 0

# ---------------------------------------------------------
class PokerGameTestCase(unittest.TestCase):

    TestConfDirectory = path.join(TESTS_PATH, 'test-data/conf')

    TestVariantInvalidFile = 'unittest.variant.invalid.xml'
    TestVariantTemplateFile = 'unittest.variant.template.xml'
    TestConfigTemplateFile = 'unittest.config.template.xml'
    TestLevelsTemplateFile = 'unittest.levels.template.xml'

    TestUrl = 'unittest.%s.xml'

    TestConfigTemporaryFile = 'config'
    TestVariantTemporaryFile = 'variant'

    # ---------------------------------------------------------
    def setUp(self):
        self.VariantInvalidFile = path.join(PokerGameTestCase.TestConfDirectory, PokerGameTestCase.TestVariantInvalidFile)
        self.ConfigTmplFile = path.join(PokerGameTestCase.TestConfDirectory, PokerGameTestCase.TestConfigTemplateFile)
        self.VariantTmplFile = path.join(PokerGameTestCase.TestConfDirectory, PokerGameTestCase.TestVariantTemplateFile)
        self.LevelsTmplFile = path.join(PokerGameTestCase.TestConfDirectory, PokerGameTestCase.TestLevelsTemplateFile)

        self.ConfigTempFile = path.join(tempfile.gettempdir(), PokerGameTestCase.TestUrl % PokerGameTestCase.TestConfigTemporaryFile)
        self.VariantTempFile = path.join(tempfile.gettempdir(), PokerGameTestCase.TestUrl % PokerGameTestCase.TestVariantTemporaryFile)

        self.CreateGameServer()
        self.InitGame()
        InitCallback()

    # ---------------------------------------------------------
    def tearDown(self):
        self.DeleteFile(self.ConfigTempFile)
        self.DeleteFile(self.VariantTempFile)

    # ---------------------------------------------------------
    def testUniq(self):
        """Test Poker Game: Uniq"""

        self.failUnlessEqual(pokergame.uniq([1, 4, 4, 7]).sort(), [1, 4, 7].sort())
        self.failUnlessEqual(pokergame.uniq([1, 4, 4, 7, 3, 3, 3, 9, 7]).sort(), [1, 3, 4, 7, 9].sort())

    # ---------------------------------------------------------
    def testGetSerialByNameNoCase(self):
        """Test Poker Game: Get serial by name no case sensitive"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Set the player's name
        player1.name = 'Player1'
        player2.name = 'Player2'

        # Seach player by his name (no case sensitive)
        self.failUnlessEqual(self.game.getSerialByNameNoCase('player1'), 1)
        self.failUnlessEqual(self.game.getSerialByNameNoCase('pLaYEr2'), 2)
        self.failUnlessEqual(self.game.getSerialByNameNoCase('unknown'), 0)

    # ---------------------------------------------------------
    def testSetPosition(self):
        """Test Poker Game: Set position"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Position initially set to -1
        self.failUnlessEqual(self.game.position, -1)

        # The game is not running, the set position function is not avalaible
        self.failIf(self.game.isRunning())
        self.game.setPosition(5)
        self.failUnlessEqual(self.game.position, -1)

        # Blind and ante turn
        self.game.forced_dealer_seat = 2
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The game is running, the set position function is available
        self.failUnless(self.game.isRunning())
        self.game.setPosition(2)
        self.failUnlessEqual(self.game.position, 2)
        self.failUnlessEqual(self.game.getSerialInPosition(), 3)

        # Invalid position
        self.game.setPosition(-1)
        self.failUnlessEqual(self.game.getSerialInPosition(), 0)

    # ---------------------------------------------------------
    def testPokerGameSetInvalidMaxPlayer(self):
        """Test Poker Game: Set an invalid number max of player"""

        # The minimum number of player is 2
        self.game.setMaxPlayers(0)
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)
        self.failUnlessEqual(self.game.seatsCount(), 0)

        self.game.setMaxPlayers(1)
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)
        self.failUnlessEqual(self.game.seatsCount(), 0)

        # The maximum number of player is sepcified by the ABSOLUTE_MAX_PLAYERS constant
        self.game.setMaxPlayers(pokergame.ABSOLUTE_MAX_PLAYERS + 1)
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)
        self.failUnlessEqual(self.game.seatsCount(), 0)

    # ---------------------------------------------------------
    def testPokerGameSetValidMaxPlayer(self):
        """Test Poker Game: Set a valid number max of player"""

        # Test all the valid numbers of player
        for num in range(2,pokergame.ABSOLUTE_MAX_PLAYERS):
            self.game.setMaxPlayers(num)
            self.failUnlessEqual(self.game.seatsLeftCount(), num)
            self.failUnlessEqual(self.game.seatsCount(), num)

    # ---------------------------------------------------------
    def testSetSeats(self):
        """Test Poker Game: Set seats"""

        # Set the number maximum of players, the available seats are [1, 3, 6, 8]
        self.game.setMaxPlayers(4)

        # Create players
        for player in range(1, 5):
            player = self.AddPlayerAndSit(player)

        # Set the seats of all the players
        seats = [0] * pokergame.ABSOLUTE_MAX_PLAYERS

        seats[1] = 1
        seats[3] = 3
        seats[6] = 4
        seats[8] = 2

        self.game.setSeats(seats)
        self.failUnlessEqual(self.GetPlayer(1).seat, 1)
        self.failUnlessEqual(self.GetPlayer(2).seat, 8)
        self.failUnlessEqual(self.GetPlayer(3).seat, 3)
        self.failUnlessEqual(self.GetPlayer(4).seat, 6)

        # Set the seats of all the players
        # The seat of the player 3 is not available
        seats = [0] * pokergame.ABSOLUTE_MAX_PLAYERS

        seats[1] = 1
        seats[4] = 3
        seats[6] = 4
        seats[8] = 2

        self.game.setSeats(seats)
        self.failUnlessEqual(self.GetPlayer(3).seat, -1)

    def testGetBestSeat(self):
        self.game.setMaxPlayers(6)
        # seats_left: 0, 2, 4, 5, 7, 8
        #                D     S     B

        # Test for empty game
        self.assertTrue(self.game.getBestSeat() is not None)

        # Test with one player
        dealer_seat = 2
        small_blind_seat = 5
        big_blind_seat = 8
        self.assertTrue(self.game.addPlayer(1, seat=dealer_seat, name="dealer") is not None)
        self.game.isRunning = lambda : True

        best_seat = self.game.getBestSeat()
        self.assertTrue(best_seat in self.game.seats_left and best_seat != dealer_seat)

        self.assertTrue(self.game.addPlayer(2, seat=small_blind_seat, name="small") is not None)
        self.game.player_list = [1,2]
        self.game.dealer = 0

        self.assertEqual(self.game.getBestSeat(), 4)

        self.assertTrue(self.game.addPlayer(3, seat=big_blind_seat, name="big") is not None)
        self.game.player_list = [1,2,3]

        self.assertTrue(self.game.addPlayer(10, name="whatever") is not None)
        self.assertEqual(self.game.getPlayer(10).seat, 0)
        self.assertTrue(self.game.addPlayer(20, name="whatever") is not None)
        self.assertEqual(self.game.getPlayer(20).seat, 4)
        self.assertEqual(self.game.getBestSeat(), 7)




    # ---------------------------------------------------------
    def testPokerGameOpen(self):
        """Test Poker Game: Open and close"""

        self.failUnlessEqual(self.game.is_open, True)
        self.game.close()
        self.failUnlessEqual(self.game.is_open, False)
        self.game.open()
        self.failUnlessEqual(self.game.is_open, True)

    # ---------------------------------------------------------
    def testPokerGameCanAddPlayer(self):
        """Test Poker Game: Can add player"""

        # The player can be added to the game
        self.failUnless(self.game.canAddPlayer(1))

        # No player can be added if the game is closed
        self.game.close()
        self.failIf(self.game.canAddPlayer(2))

        # Player can be added if the game is opened
        self.game.open()
        self.failUnless(self.game.canAddPlayer(2))

    # ---------------------------------------------------------
    def testPokerGameAddPlayerWithoutSelectedSeat(self):
        """Test Poker Game: Add a player without a selected seat"""

        # Add a new player
        p1 = self.game.addPlayer(1)
        self.failUnless(p1 != None)
        self.failUnless(self.game.isSeated(1))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add the same player
        self.failUnless(p1 == self.game.addPlayer(1))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Add a new player
        self.failUnless(self.game.addPlayer(2))
        self.failUnless(self.game.isSeated(2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)

        # Try to add new one but there is no seat left
        self.failIf(self.game.addPlayer(3))
        self.failIf(self.game.isSeated(3))
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)

    # ---------------------------------------------------------
    def testPokerGameAddPlayerWithSelectedSeat(self):
        """Test Poker Game: Add a player with a selected seat"""

        # Add a player on the seat 2
        self.failUnless(self.game.addPlayer(1,2))
        self.failUnless(self.game.isSeated(1))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add the same player on the same seat
        self.failUnless(self.game.addPlayer(1,2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add the same player on another seat
        self.failIf(self.game.addPlayer(1,7))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add a new player on an invalid seat
        self.failIf(self.game.addPlayer(2,3))
        self.failIf(self.game.isSeated(2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add a new player on an unavailable seat
        self.failIf(self.game.addPlayer(2,2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Add a player on the seat 7
        self.failUnless(self.game.addPlayer(2,7))
        self.failUnless(self.game.isSeated(2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)

    # ---------------------------------------------------------
    def testPokerGameAddPlayerClientGame(self):
        """Test Poker Game: Add a player client game"""

        # Create a client game
        self.CreateGameClient()
        self.InitGame()

        # Try to add a new player without a selected seat
        self.failIf(self.game.addPlayer(1))
        self.failIf(self.game.isSeated(1))
        self.failUnlessEqual(self.game.seatsLeftCount(), 2)

        # Add a player on the seat 2
        self.failUnless(self.game.addPlayer(1,2))
        self.failUnless(self.game.isSeated(1))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add the same player on the same seat
        self.failUnless(self.game.addPlayer(1,2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add the same player on another seat
        self.failUnless(self.game.addPlayer(1,7) == None)
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add a new player on an invalid seat
        self.failUnless(self.game.addPlayer(2,3) == None)
        self.failIf(self.game.isSeated(2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Try to add a new player on an unavailable seat
        self.failUnless(self.game.addPlayer(2,2) == None)
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Add a player on the seat 7
        self.failUnless(self.game.addPlayer(2,7))
        self.failUnless(self.game.isSeated(2))
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)

    # ---------------------------------------------------------
    def testPokerGameGetPlayer(self):
        """Test Poker Game: Get player"""

        self.failUnlessEqual(self.game.serialsAll(), [])
        self.failUnlessEqual(self.game.playersAll(), [])
        self.failUnlessEqual(self.game.allCount(), 0)

        self.failUnless(self.game.addPlayer(1))
        player = self.GetPlayer(1)
        self.failUnlessEqual(self.game.getPlayer(2), None)

        self.failUnlessEqual(self.game.serialsAll(), [1])
        self.failUnlessEqual(self.game.playersAll(), [player])
        self.failUnlessEqual(self.game.allCount(), 1)

    # ---------------------------------------------------------
    def testPokerGameSeats(self):
        """Test Poker Game: Seats"""

        seats = self.game.seats()
        for seat in seats:
            self.failUnlessEqual(seats[seat], 0)

        self.failIf(self.game.addPlayer(1, 2) == None)
        self.failIf(self.game.addPlayer(2, 7) == None)

        seats = self.game.seats()
        self.failUnlessEqual(seats[2], 1)
        self.failUnlessEqual(seats[7], 2)

    def testPokerGameSeatsAreDeterministic(self):
        game = self.game
        game.variant = 'holdem'
        game.setMaxPlayers(3)
        self.assertEqual(game.seats_all, [2,7,5])
        self.assertEqual(game.seats_left, [2,7,5])

        self.AddPlayerAndSit(1, 2)
        self.AddPlayerAndSit(2, 5)
        self.assertEqual(game.seats_left, [7])

        game.removePlayer(2)
        self.assertEqual(game.seats_left, [7,5])

        player3 = self.AddPlayerAndSit(3)
        self.assertEqual(player3.seat, 7)

    # ---------------------------------------------------------
    def testPokerGamePlayerCanComeBack(self):
        """Test Poker Game: Player can come back"""

        # Unknown player
        self.failIf(self.game.canComeBack(1))
        self.failIf(self.game.comeBack(1))

        # Add a new player
        player1 = self.AddPlayerAndSit(1, 2)

        # Initially the player are connected and not auto
        self.failIf(self.game.canComeBack(1))
        self.failIf(self.game.comeBack(1))

        # Player disconnected
        player1.remove_next_turn = True
        self.failUnlessEqual(self.game.serialsDisconnected(), [1])

        # The player can now come back
        self.failUnless(self.game.canComeBack(1))
        self.failUnless(self.game.comeBack(1))

        # The player is now in the game
        self.failIf(self.game.canComeBack(1))
        self.failIf(player1.remove_next_turn)
        self.failIf(player1.sit_out_next_turn)
        self.failIf(player1.sit_requested)
        self.failIf(player1.auto)

        # The player is an automatic player
        player1.auto = True
        self.failUnless(player1.isAuto())

        # The player now can come back
        self.failUnless(self.game.canComeBack(1))
        self.failUnless(self.game.comeBack(1))

        # The player is now in the game
        self.failIf(self.game.canComeBack(1))
        self.failIf(player1.remove_next_turn)
        self.failIf(player1.sit_out_next_turn)
        self.failIf(player1.sit_requested)
        self.failIf(player1.auto)

    # ---------------------------------------------------------
    def testPokerGameSitPlayer(self):
        """Test Poker Game: Player sit"""

        self.failUnlessEqual(self.game.sitCount(), 0)
        self.failUnlessEqual(self.game.serialsSit(), [])
        self.failUnlessEqual(self.game.playersSit(), [])

        self.failUnlessEqual(self.game.sitOutCount(), 0)
        self.failUnlessEqual(self.game.serialsSitOut(), [])
        self.failUnlessEqual(self.game.playersSitOut(), [])

        self.failIf(self.game.addPlayer(1) == None)

        player = self.GetPlayer(1)

        self.failUnlessEqual(self.game.sitCount(), 0)
        self.failUnlessEqual(self.game.serialsSit(), [])
        self.failUnlessEqual(self.game.playersSit(), [])

        self.failUnlessEqual(self.game.sitOutCount(), 1)
        self.failUnlessEqual(self.game.serialsSitOut(), [1])
        self.failUnlessEqual(self.game.playersSitOut(), [player])

        player.sit_out = False
        self.failUnlessEqual(self.game.sitCount(), 1)
        self.failUnlessEqual(self.game.serialsSit(), [1])
        self.failUnlessEqual(self.game.playersSit(), [player])

        self.failUnlessEqual(self.game.sitOutCount(), 0)
        self.failUnlessEqual(self.game.serialsSitOut(), [])
        self.failUnlessEqual(self.game.playersSitOut(), [])

    # ---------------------------------------------------------
    def testPokerGameCallback(self):
        """Test Poker Game: Callback"""

        # No callback registered
        InitCallback()
        self.game.runCallbacks('Args1', 'Args2')
        self.failUnlessEqual(len(self.game.callbacks), 0)
        self.failUnlessEqual(CallbackIds, None)
        self.failUnlessEqual(CallbackArgs, None)

        # Register a callback
        InitCallback()
        self.game.registerCallback(Callback)
        self.game.runCallbacks('Args1', 'Args2')
        self.failUnlessEqual(len(self.game.callbacks), 1)
        self.failUnlessEqual(CallbackIds, [self.game.id])
        self.failUnlessEqual(CallbackArgs, [('Args1', 'Args2')])

        # Unregister the previous callback
        InitCallback()
        self.game.unregisterCallback(Callback)
        self.game.runCallbacks('Args1', 'Args2')
        self.failUnlessEqual(len(self.game.callbacks), 0)
        self.failUnlessEqual(CallbackIds, None)
        self.failUnlessEqual(CallbackArgs, None)

    # ---------------------------------------------------------
    def testPokerGameBettingStructure(self):
        """Test Poker Game: Initialisation of the betting structure"""

        self.failUnlessEqual(self.game.getBettingStructureName(), 'Bet Description')
        self.failUnlessEqual(self.game.buyIn(), 50)
        self.failUnlessEqual(self.game.maxBuyIn(), 10000)
        self.failUnlessEqual(self.game.bestBuyIn(), 1600)
        self.failUnlessEqual(self.game.getChipUnit(), 300)

        bet_properties = {
            'buy-in': '100',
            'max-buy-in': '20000',
            'best-buy-in': '1000',
            'unit': '600'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', None, bet_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.buyIn(), 100)
        self.failUnlessEqual(self.game.maxBuyIn(), 20000)
        self.failUnlessEqual(self.game.bestBuyIn(), 1000)
        self.failUnlessEqual(self.game.getChipUnit(), 600)

        rounds_properties = [
            { 'name': 'pre-flop', 'cap': '3' },
            { 'name': 'flop', 'cap': str(sys.maxint) },
            { 'name': 'turn', 'cap': str(sys.maxint) },
            { 'name': 'river', 'cap': '3' }
        ]

        self.failUnlessEqual(len(self.game.bet_info), len(rounds_properties))

        self.game.current_round = 0
        for round_properties in rounds_properties:
            for prop, value in round_properties.items():
                self.failUnlessEqual(self.game.betInfo()[prop], value)

            self.game.current_round += 1

    # ---------------------------------------------------------
    def testPokerGameBlindBettingStructure(self):
        """Test Poker Game: Initialisation of the blind betting structure"""

        self.failUnlessEqual(self.game.smallBlind(), 500)
        self.failUnlessEqual(self.game.bigBlind(), 1000)

        # Change the blind properties
        blind_properties = { 'small': '1000', 'big': '2000' }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.smallBlind(), 1000)
        self.failUnlessEqual(self.game.bigBlind(), 2000)

        # Change the blind properties
        blind_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'small': '2000',
            'big': '4000'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.blind_info['small'], 2000)
        self.failUnlessEqual(self.game.blind_info['small_reference'], 2000)
        self.failUnlessEqual(self.game.blind_info['big'], 4000)
        self.failUnlessEqual(self.game.blind_info['big_reference'], 4000)

        # Change the blind properties
        blind_properties = { 'change': 'levels', 'levels': PokerGameTestCase.TestLevelsTemplateFile }

        levels_info = [
            { 'small': 1000, 'big': 1500, 'value': 100, 'bring-in': 150 },
            { 'small': 1500, 'big': 3000, 'value': 150, 'bring-in': 300 },
            { 'small': 2500, 'big': 5000, 'value': 250, 'bring-in': 500 }
        ]

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.blind_info["levels"], levels_info)

    # ---------------------------------------------------------
    def testPokerGameAnteBettingStructure(self):
        """Test Poker Game: Initialisation of the ante betting structure"""

        # Change the ante properties
        ante_properties = { 'value': '200', 'bring-in': '1000' }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.ante_info["value"], 200)
        self.failUnlessEqual(self.game.ante_info["bring-in"] , 1000)

        # Change the ante properties
        ante_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'value': '50',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/ante', None, ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.ante_info['value'], 50)
        self.failUnlessEqual(self.game.ante_info['value_reference'], 50)
        self.failUnlessEqual(self.game.ante_info['bring-in'], 200)
        self.failUnlessEqual(self.game.ante_info['bring-in_reference'], 200)

        # Change the ante properties
        ante_properties = { 'change': 'levels', 'levels': PokerGameTestCase.TestLevelsTemplateFile }

        levels_info = [
            { 'small': 1000, 'big': 1500, 'value': 100, 'bring-in': 150 },
            { 'small': 1500, 'big': 3000, 'value': 150, 'bring-in': 300 },
            { 'small': 2500, 'big': 5000, 'value': 250, 'bring-in': 500 }
        ]

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/ante', None, ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.ante_info["levels"], levels_info)

    # ---------------------------------------------------------
    def testPokerGameGetLevelValues(self):
        """Test Poker Game: Get level values"""

        # Change the blind properties
        blind_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'small': '2000',
            'big': '4000'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Change the ante properties
        ante_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'value': '50',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Change double, check the blind and ante infos
        for level in range(3):
            blind_info, ante_info = self.game.getLevelValues(level)

            self.failUnlessEqual(blind_info['small'], 2000 * pow(2, level - 1))
            self.failUnlessEqual(blind_info['big'], 4000 * pow(2, level - 1))
            self.failUnlessEqual(ante_info['value'], 50 * pow(2, level - 1))
            self.failUnlessEqual(ante_info['bring-in'], 200 * pow(2, level - 1))

        # Change the blind properties
        blind_properties = { 'change': 'levels',
                                'levels': PokerGameTestCase.TestLevelsTemplateFile
                            }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Change the ante properties
        ante_properties = { 'change': 'levels', 'levels': PokerGameTestCase.TestLevelsTemplateFile }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/ante', None, ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Change levels, check the blind and ante infos
        levels_info = [
            { 'small': 1000, 'big': 1500, 'value': 100, 'bring-in': 150 },
            { 'small': 1500, 'big': 3000, 'value': 150, 'bring-in': 300 },
            { 'small': 2500, 'big': 5000, 'value': 250, 'bring-in': 500 }
        ]

        for level in range(3):
            blind_info, ante_info = self.game.getLevelValues(level + 1)

            self.failUnlessEqual(blind_info['small'], levels_info[level]['small'])
            self.failUnlessEqual(blind_info['big'], levels_info[level]['big'])
            self.failUnlessEqual(ante_info['value'], levels_info[level]['value'])
            self.failUnlessEqual(ante_info['bring-in'], levels_info[level]['bring-in'])

        # Change the blind properties
        blind_properties = { 'change': 'invalid' }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Change the ante properties
        ante_properties = { 'change': 'invalid' }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/ante', None, ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Change invalid, check the blind and ante infos
        blind_info, ante_info = self.game.getLevelValues(0)
        self.failUnlessEqual(blind_info, None)
        self.failUnlessEqual(blind_info, ante_info)

    # ---------------------------------------------------------
    def testPokerGameSetLevelValues(self):
        """Test Poker Game: Set level values"""

        # Change the blind properties
        blind_properties = {
            'change': 'levels',
            'frequency': '15',
            'unit': 'minute',
            'levels': PokerGameTestCase.TestLevelsTemplateFile
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Change the ante properties
        ante_properties = {
            'change': 'levels',
            'frequency': '15',
            'unit': 'minute',
            'levels': PokerGameTestCase.TestLevelsTemplateFile
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Change the level and check the blind and ante infos
        levels_info = [
            { 'small': 1000, 'big': 1500, 'value': 100, 'bring-in': 150 },
            { 'small': 1500, 'big': 3000, 'value': 150, 'bring-in': 300 },
            { 'small': 2500, 'big': 5000, 'value': 250, 'bring-in': 500 }
        ]

        # Change the level and check
        for level in range(3):
            blind_info, ante_info = self.game.getLevelValues(level + 1)

            self.game.setLevel(level + 1)
            self.failUnlessEqual(self.game.getLevel(), level + 1)
            self.failUnlessEqual(self.game.blind_info['small'], blind_info['small'])
            self.failUnlessEqual(self.game.blind_info['big'], blind_info['big'])
            self.failUnlessEqual(self.game.ante_info['value'], ante_info['value'])
            self.failUnlessEqual(self.game.ante_info['bring-in'], ante_info['bring-in'])
            self.failUnlessEqual(self.game.blind_info['hands'], self.game.hands_count)
            self.failUnlessEqual(self.game.blind_info['time'], self.game.time)
            self.failUnlessEqual(self.game.ante_info['hands'], self.game.hands_count)
            self.failUnlessEqual(self.game.ante_info['time'], self.game.time)

    # ---------------------------------------------------------
    def testPokerGameSetVariantInvalid(self):
        """Test Poker Game: Variant with invalid specifications"""

        if not self.CopyFile(self.VariantInvalidFile, self.VariantTempFile):
            self.fail('Error during creation of variant file ' + self.VariantInvalidFile)

        self.failUnlessRaises(UserWarning, self.game.setVariant,PokerGameTestCase.TestVariantTemporaryFile)

    # ---------------------------------------------------------
    def testPokerGameSetVariantWinnerOrder(self):
        """Test Poker Game: Set variant winner order"""

        # The winner order is set to high in the self.VariantTmplFile file
        self.failIf(self.game.isLow())
        self.failIf(self.game.hasLow())
        self.failUnless(self.game.isHigh())
        self.failUnless(self.game.hasHigh())
        self.failIf(self.game.isHighLow())

        # Change the winner order to low
        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/wins/winner', None, {'order': 'low8'}):
            self.fail('Error during modification of variant file ' + self.VariantTempFile)

        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)

        # The winner order is now low
        self.failUnless(self.game.isLow())
        self.failUnless(self.game.hasLow())
        self.failIf(self.game.isHigh())
        self.failIf(self.game.hasHigh())
        self.failIf(self.game.isHighLow())

        # Invalid winner order
        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/wins/winner', None, {'order': 'invalid'}):
            self.fail('Error during modification of variant file ' + self.VariantTempFile)

        # An exception is raised if the order is not low8 or hi
        self.failUnlessRaises(UserWarning,self.game.setVariant, PokerGameTestCase.TestVariantTemporaryFile)

    # ---------------------------------------------------------
    def testPokerGameSetVariantRoundInfos(self):
        """Test Poker Game: Set variant round infos"""

        # 2 rounds in the template file
        self.failUnlessEqual(len(self.game.round_info),4)
        self.failUnlessEqual(len(self.game.round_info_backup),4)

        for round in range(len(self.game.round_info)):
            self.failUnlessEqual(self.game.round_info[round],self.game.round_info_backup[round])

        round1_info = {
            'name': 'pre-flop',
            'position': 'under-the-gun',
            'board': [],
            'board_size': 0,
            'hand_size': 2,
            'cards': ['down', 'down']
        }

        round2_info = {
            'name': 'flop',
            'position': 'next-to-dealer',
            'board': ['', '', ''],
            'board_size': 3,
            'hand_size': 2,
            'cards': []
        }

        self.failUnlessEqual(self.game.round_info[0], round1_info)
        self.failUnlessEqual(self.game.round_info[1], round2_info)

        self.failUnlessEqual(self.game.round_info[0],self.game.round_info_backup[0])
        self.failUnlessEqual(self.game.round_info[1],self.game.round_info_backup[1])

    # ---------------------------------------------------------
    def testPokerGameResetRoundInfos(self):
        """Test Poker Game: Reset round infos"""

        round1_info = {
            'name': 'pre-flop',
            'position': 'under-the-gun',
            'board': [],
            'board_size': 0,
            'hand_size': 2,
            'cards': ['down', 'down']
        }

        # The round info are loaded from the VariantTmplFile file
        self.failUnlessEqual(self.game.round_info[0], round1_info)

        # Change all the round infos
        self.game.round_info[0]['name'] = 'ModifiedRound'
        self.game.round_info[0]['position'] = 'ModifiedPosition'
        self.game.round_info[0]['board'] = ['ModifiedBoard']
        self.game.round_info[0]['board_size'] = 'ModifiedBoardSize'
        self.game.round_info[0]['hand_size'] = 'ModifiedHandSize'
        self.game.round_info[0]['cards'] = ['up']

        # Restore the round backup
        self.failIfEqual(self.game.round_info[0], round1_info)
        self.game.resetRoundInfo()
        self.failUnlessEqual(self.game.round_info[0], round1_info)

    # ---------------------------------------------------------
    def testPokerGameLoadTournamentLevels(self):
        """Test Poker Game: Load tournament levels"""

        # The levels are loaded from the LevelsTmplFile file
        levels_info = [
            { 'small': 1000, 'big': 1500, 'value': 100, 'bring-in': 150 },
            { 'small': 1500, 'big': 3000, 'value': 150, 'bring-in': 300 },
            { 'small': 2500, 'big': 5000, 'value': 250, 'bring-in': 500 }
        ]

        levels = self.game.loadTournamentLevels(self.TestLevelsTemplateFile)
        self.failUnlessEqual(levels, levels_info)

    # ---------------------------------------------------------
    def testPokerGamePayBuyIn(self):
        """Test Poker Game: Pay buy in"""

        self.failIf(self.game.addPlayer(1) == None)
        player = self.GetPlayer(1)

        # Get the buy in values
        self.failUnlessEqual(self.game.buyIn(), 50)
        self.failUnlessEqual(self.game.maxBuyIn(), 10000)
        self.failUnlessEqual(self.game.bestBuyIn(), 1600)

        # Can not pay more then the max buy in
        self.failIf(self.game.payBuyIn(1,20000))
        self.failIf(player.isBuyInPayed())

        # Can not pay less than the min buy in
        self.failIf(self.game.payBuyIn(1,40))
        self.failIf(player.isBuyInPayed())

        # Pay the buy in
        self.failUnless(self.game.payBuyIn(1,100))
        self.failUnless(player.isBuyInPayed())
        self.failUnlessEqual(self.game.getPlayerMoney(1), 100)

        # The game in now a tournament, there is no maximum limit

        # Change the blind properties
        blind_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'small': '2000',
            'big': '4000'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # The player can pay more than the max buy in
        self.failUnless(self.game.payBuyIn(1,20000))
        self.failUnless(player.isBuyInPayed())
        self.failUnlessEqual(self.game.getPlayerMoney(1), 20000)

    # ---------------------------------------------------------
    def testPokerGameSitRequested(self):
        """Test Poker Game: Sit requested"""

        self.failIf(self.game.addPlayer(1) == None)
        self.game.sitRequested(1)
        player = self.GetPlayer(1)

        self.failUnlessEqual(player.isSitRequested(), True)
        self.failUnlessEqual(player.isWaitForBlind(), False)
        self.failUnlessEqual(player.sit_out_next_turn, False)

    # ---------------------------------------------------------
    def testPokerGameSit(self):
        """Test Poker Game: Sit"""

        self.failIf(self.game.addPlayer(1) == None)
        player = self.GetPlayer(1)
        # Can not sit because of missing buyin
        self.failUnlessEqual(self.game.sit(1), False)

        # Can sit after buyin
        self.failUnlessEqual(self.game.payBuyIn(1,self.game.bestBuyIn()), True)
        self.failUnlessEqual(player.isBuyInPayed(), True)
        self.failUnlessEqual(self.game.sit(1), True)

        # Can not sit, again, after being already seated
        self.failUnlessEqual(self.game.sit(1), False)

        # Can sit in if sit_out_next_turn
        self.game.isInTurn = lambda serial: True
        self.game.sitOutNextTurn(1)
        self.failUnlessEqual(self.game.sit(1), True)

        # Can sit in if autoPlayer
        self.game.autoPlayer(1)
        self.failUnlessEqual(self.game.sit(1), True)

    # ---------------------------------------------------------
    def testPokerGameBuildPlayerList(self):
        """Test Poker Game: Build player list"""

        player1 = self.AddPlayerAndSit(1, 7)

        self.failUnless(self.game.addPlayer(2, 2))
        self.failUnless(self.game.payBuyIn(2,self.game.bestBuyIn()))

        # Can not construct the player list because there is only one player sit
        self.failIf(self.game.buildPlayerList(False))

        # The player 2 is now sit
        self.failUnlessEqual(self.game.sit(2), True)

        # The construction of the player list is now possible
        self.failUnless(self.game.buildPlayerList(False))

        # The players are ordered by his seat
        self.failUnlessEqual(self.game.player_list, [2, 1])

        # The player 1 is waiting for blind and first round
        player1.wait_for = 'first_round'
        self.failUnless(player1.isWaitForBlind())
        self.failUnless(self.game.buildPlayerList(False))
        self.failUnlessEqual(self.game.player_list, [2])

        self.failUnless(self.game.buildPlayerList(True))
        self.failUnlessEqual(self.game.player_list, [2])

        # The player 1 is only waiting for blind
        player1.wait_for = 'big'
        self.failUnless(player1.isWaitForBlind())
        self.failUnless(self.game.buildPlayerList(False))
        self.failUnlessEqual(self.game.player_list, [2])

        self.failUnless(self.game.buildPlayerList(True))
        self.failUnlessEqual(self.game.player_list, [2, 1])

    # ---------------------------------------------------------
    def testMoveDealerLeft(self):
        """Test Poker Game: Move dealer left"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The construction of the player list
        self.failUnless(self.game.buildPlayerList(False))
        self.failUnlessEqual(self.game.player_list, [1, 2])

        # The dealer is the player 1
        self.failUnlessEqual(self.game.dealer_seat, 2)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getPlayerDealer(), player1)

        # Move the dealer
        self.game.moveDealerLeft()

        # The player 2 is now the dealer
        self.failUnlessEqual(self.game.dealer_seat, 7)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getPlayerDealer(), player2)

        # Re init the game players
        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # The construction of the player list
        self.failUnless(self.game.buildPlayerList(False))
        self.failUnlessEqual(self.game.player_list, [1, 2, 3])

        # The dealer is the player 1
        self.failUnlessEqual(self.game.dealer_seat, 2)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getPlayerDealer(), player1)

        # Move the dealer
        player2.missed_blind = None
        self.game.moveDealerLeft()

        # The player 2 is now the dealer
        self.failUnlessEqual(self.game.dealer_seat, 5)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getPlayerDealer(), player2)

        # No blind info, nothing done
        self.game.blind_info = None
        player1.missed_blind = None
        self.game.moveDealerLeft()

        # The player 2 is still the dealer
        self.failUnlessEqual(self.game.dealer_seat, 5)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getPlayerDealer(), player2)

    # ---------------------------------------------------------
    def testDealerFromDealerSeat(self):
        """Test Poker Game: Dealer from dealer seat"""

        self.game.setMaxPlayers(3)

        self.failUnlessEqual(self.game.dealer, -1)
        self.failUnlessEqual(self.game.dealer_seat, -1)

        self.game.dealerFromDealerSeat()

        # The dealer and his seat are not initialised
        self.failUnlessEqual(self.game.dealer, -1)
        self.failUnlessEqual(self.game.dealer_seat, -1)

        # Create player 1
        player1 = self.AddPlayerAndSit(1, 2)

        self.failUnlessEqual(self.game.dealer_seat, 2)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.dealer, -1)

        # Create player 2
        player2 = self.AddPlayerAndSit(2, 5)

        self.failUnlessEqual(self.game.dealer_seat, 2)

        # Construct the player list
        self.failUnlessEqual(self.game.buildPlayerList(False), True)
        self.failUnlessEqual(self.game.player_list, [1, 2])

        # The dealer is the player 1
        self.failUnlessEqual(self.game.dealer_seat, 2)
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getSerialDealer(), 1)
        self.failUnlessEqual(self.game.getPlayerDealer(), player1)

        # Change the dealer seat
        self.game.dealer_seat = 5

        # The dealer is now the player 2
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getSerialDealer(), 2)
        self.failUnlessEqual(self.game.getPlayerDealer(), player2)

        # Add a player but do not reconstruct the player list
        player3 = self.AddPlayerAndSit(3)

        # Change the dealer seat
        self.game.dealer_seat = 7

        # The dealder is still the player 2
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getSerialDealer(), 2)
        self.failUnlessEqual(self.game.getPlayerDealer(), player2)

    # ---------------------------------------------------------
    def testSetDealer(self):
        """Test Poker Game: Set dealer"""

        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Construct the player list
        self.failUnless(self.game.buildPlayerList(False))

        # The game is not running
        self.failIf(self.game.isRunning())

        # The dealer can be set because the game is not running
        self.game.setDealer(7)

        # The dealer is the player 2
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getSerialDealer(), 2)

        # The dealer can be set because the game is not running
        self.game.setDealer(2)

        # The dealer is the player 1
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getSerialDealer(), 1)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The game is now running
        self.failUnless(self.game.isRunning())
        self.failUnlessEqual(self.game.getSerialDealer(), 1)

        # The set dealer function has no effect
        self.game.setDealer(7)

        # The dealer is still the player 1
        self.game.dealerFromDealerSeat()
        self.failUnlessEqual(self.game.getSerialDealer(), 1)

    # ---------------------------------------------------------
    def testPokerGameMoney2Bet(self):
        """Test Poker Game: Money to bet"""

        self.game.registerCallback(Callback)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Initial player money and bet
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)

        # Transfert from money to bet
        InitCallback()
        self.game.money2bet(1, 500)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)
        self.failUnlessEqual(player1.bet, 500)
        self.failUnlessEqual(player1.isAllIn(), False)

        # Check the callback
        self.failUnlessEqual(CallbackIds, [self.game.id])
        self.failUnlessEqual(CallbackArgs, [('money2bet', 1, 500)])

        # Initial player money and bet
        InitCallback()
        self.failUnlessEqual(player2.bet, 0)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1600)

        # Transfert from money to bet
        self.game.money2bet(2, 2000)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 0)
        self.failUnlessEqual(player2.bet, 1600)
        self.failUnlessEqual(player2.isAllIn(), True)

        # Check the callback
        self.failUnlessEqual(CallbackIds, [self.game.id, self.game.id])
        self.failUnlessEqual(CallbackArgs, [('money2bet', 2, 1600), ('all-in', 2)])

    # ---------------------------------------------------------
    def testNotFoldCount(self):
        """Test Poker Game: Not fold count"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnlessEqual(self.game.notFoldCount(), 2)
        self.failUnlessEqual(self.game.serialsNotFold(), [1, 2])
        self.failUnlessEqual(self.game.playersNotFold(), [player1, player2])

        player1.fold = True
        self.failUnlessEqual(self.game.notFoldCount(), 1)
        self.failUnlessEqual(self.game.serialsNotFold(), [2])
        self.failUnlessEqual(self.game.playersNotFold(), [player2])

    # ---------------------------------------------------------
    def testPot2Money(self):
        """Test Poker Game: Pot to money"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnlessEqual(self.game.getPlayerMoney(1), self.game.bestBuyIn())
        self.game.pot = 500
        self.game.pot2money(1)
        self.failUnlessEqual(self.game.getPlayerMoney(1), self.game.bestBuyIn() + 500)
        self.failUnlessEqual(self.game.pot, 0)

    # ---------------------------------------------------------
    def testGetPotAmount(self):
        """Test Poker Game: getPotAmount"""

        # Create players
        player1 = self.AddPlayerAndSit(1)
        player2 = self.AddPlayerAndSit(2)

        self.game.beginTurn(1)
        self.failUnlessEqual(0 ,self.game.getPotAmount())

        self.game.state = pokergame.GAME_STATE_END
        self.failUnlessEqual(0 ,self.game.getPotAmount())

    # ---------------------------------------------------------
    def testCancelState(self):
        """Test Poker Game: Cancel state"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        attribs = {
            'current_round': -2,
            'position': -1,
            'state': 'end'
        }

        self.game.position = -1
        self.game.cancelState()

        for key, value in attribs.items():
            self.failUnlessEqual(getattr(self.game,key), value)

        self.game.position = 0
        self.game.turn_history = []
        self.game.cancelState()

        self.failUnlessEqual(self.game.turn_history, [('position', -1, None)] )

    # ---------------------------------------------------------
    def testHighestBet(self):
        """Test Poker Game: Highest bet"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(player2.bet, 0)
        player1.bet = 500
        self.failUnlessEqual(self.game.highestBetNotFold(), 500)
        self.failUnlessEqual(self.game.highestBetInGame(), 500)
        player2.bet = 1000
        self.failUnlessEqual(self.game.highestBetNotFold(), 1000)
        self.failUnlessEqual(self.game.highestBetInGame(), 1000)
        player2.fold = True
        self.failUnlessEqual(self.game.highestBetNotFold(), 500)
        self.failUnlessEqual(self.game.highestBetInGame(), 500)
        player2.fold = False
        player2.all_in = True
        self.failUnlessEqual(self.game.highestBetNotFold(), 1000)
        self.failUnlessEqual(self.game.highestBetInGame(), 500)

    # ---------------------------------------------------------
    def testBetsEqual(self):
        """Test Poker Game: Bets equal"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(player2.bet, 0)
        player1.bet = 500
        self.failUnlessEqual(self.game.betsEqual(), False)
        player2.bet = 500
        self.failUnlessEqual(self.game.betsEqual(), True)
        player2.bet = 1000
        player2.all_in = True
        self.failUnlessEqual(self.game.betsEqual(), False)
        player2.fold = True
        self.failUnlessEqual(self.game.betsEqual(), True)
        player2.fold = False
        player1.all_in = True
        self.failUnlessEqual(self.game.betsEqual(), True)

    # ---------------------------------------------------------
    def testCanCall(self):
        """Test Poker Game: Can call"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())


        self.failIf(self.game.canCall(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        player1.bet = 1000
        self.failUnless(self.game.canCall(2))
        player2.bet = 1500
        self.failIf(self.game.canCall(2))

    # ---------------------------------------------------------
    def testCall(self):
        """Test Poker Game: Call"""

        self.game.setMaxPlayers(3)

        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.call(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        self.failIf(self.game.canAct(1))
        self.failIf(self.game.call(1))

        # Deal cards
        self.game.dealCards()

        self.failUnless(self.game.callNraise(1, 100))

        self.failUnless(self.game.canAct(2))
        self.failIf(player2.talked_once)

        self.failUnless(self.game.call(2))

        self.failUnlessEqual(player2.bet, 100)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1500)
        self.failUnless(player2.talked_once)

        self.failUnless(self.game.canAct(3))

    # ---------------------------------------------------------
    def testCanCheck(self):
        """Test Poker Game: Can check"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.canCheck(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        player1.bet = 1000
        player2.bet = 500
        self.failIf(self.game.canCheck(2))
        player2.bet = 1000
        self.failUnless(self.game.canCheck(2))
        player2.bet = 1500
        self.failUnless(self.game.canCheck(2))

    # ---------------------------------------------------------
    def testCheck(self):
        """Test Poker Game: Check"""

        # Create Players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Check is not available during blind and ante round
        self.failIf(self.game.check(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # Player 1 can now raise
        self.failUnless(self.game.canAct(1))
        self.failUnless(self.game.callNraise(1, 100))

        # Player 2 bet is less than the highest bet
        self.failUnless(self.game.canAct(2))
        self.failIf(self.game.canCheck(2))
        self.failIf(self.game.check(2))

        # Player 2 can now check
        player2.bet = 100
        self.failUnless(self.game.canCheck(2))
        self.failIf(player2.talked_once)

        # Player 2 check
        self.failUnless(self.game.check(2))

        # Second round
        self.failUnless(self.game.isSecondRound())

    # ---------------------------------------------------------
    def testCanFold(self):
        """Test Poker Game: Can fold"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player can not fold
        self.failIf(self.game.canFold(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # The player can now fold
        self.failUnless(self.game.canFold(1))

        # The player 2 is not in game so he can not fold
        player2.all_in = True
        self.failIf(self.game.isInGame(2))
        self.failIf(self.game.canFold(2))

    # ---------------------------------------------------------
    def testFold(self):
        """Test Poker Game: Fold"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Player can not fold
        self.failIf(self.game.fold(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Player 1 not in position
        self.failIf(self.game.canAct(1))
        self.failIf(self.game.fold(1))

        # Deal cards
        self.game.dealCards()

        # Player 1 raise
        self.failUnless(self.game.callNraise(1, 100))

        # Player 2 already fold, the fold function has no effect
        player2.fold = True
        self.failUnless(self.game.canAct(2))
        self.failUnless(self.game.fold(2))
        self.failUnless(self.game.canAct(2))

        # Player 2 fold
        player2.fold = False

        player2.bet = 300
        self.failIf(player2.isFold())
        self.failUnless(self.game.canAct(2))

        self.failUnless(self.game.fold(2))

        self.failUnless(player2.isFold())
        self.failUnlessEqual(player2.bet, 0)
        self.failUnlessEqual(self.game.pot, 300)

        # Player 3 can act
        self.failUnless(self.game.canAct(3))

    # ---------------------------------------------------------
    def testCanRaise(self):
        """Test Poker Game: Can raise"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.canRaise(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # The player can now raise
        self.failUnless(self.game.canRaise(1))

        self.game.round_cap_left = 0
        self.failIf(self.game.canRaise(1))
        self.game.round_cap_left = sys.maxint

        player1.bet = 1000
        player1.money = 600
        self.failUnless(self.game.canRaise(2))

        player1.talked_once = False
        self.failUnless(self.game.canRaise(1))
        player1.talked_once = True
        self.failIf(self.game.canRaise(1))

        player1.bet = player2.money + 1000
        self.failIf(self.game.canRaise(2))

        player2.bet = 1600
        player2.money = 0
        self.failIf(self.game.canRaise(2))

    # ---------------------------------------------------------
    def testCallNRaise(self):
        """Test Poker Game: Call N raise"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3 ,7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.canAct(1))
        self.failIf(self.game.callNraise(1, 100))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # The card are not dealt so the players can not act
        self.failIf(self.game.canAct(1))
        self.failIf(self.game.callNraise(1, 100))

        # Deal cards
        self.game.dealCards()

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'min': '100', 'max': '300'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnlessEqual(self.game.betLimitsForSerial(1), (100, 300, 100))

        self.failUnless(self.game.callNraise(1, 50))
        self.failUnlessEqual(player1.bet, 100)
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (200, 400, 100))

        self.failUnless(self.game.canAct(2))

        self.failUnless(self.game.callNraise(2, 500))
        self.failUnlessEqual(player2.bet, 400)

        self.failUnless(self.game.canAct(3))

        self.game.round_cap_left = 0
        self.failIf(self.game.callNraise(3, 100))

        self.game.round_cap_left = -1
        self.failIf(self.game.callNraise(3, 100))

    # ---------------------------------------------------------
    def testCanAct(self):
        """Test Poker Game: Can act"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # It the blind and ante turn so the player can act
        self.failUnless(self.game.canAct(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Can not act because the cards are not dealt
        self.failIf(self.game.cardsDealt())
        self.failIf(self.game.canAct(1))

        # Deal cards
        self.game.dealCards()

        # The cards are now dealt so the player 1 can act
        self.failUnless(self.game.cardsDealt())
        self.failUnless(self.game.canAct(1))

        # The player 2 can not act because it is not its turn
        self.failIfEqual(self.game.getSerialInPosition(), 2)
        self.failIf(self.game.canAct(2))

        self.game.callNraise(1, 1000)

        # The player 2 can now play
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)
        #self.game.setPosition(1)
        self.failUnless(self.game.canAct(2))

    # ---------------------------------------------------------
    def testWillAct(self):
        """Test Poker Game: Will act"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The game is not running
        self.failIf(self.game.isRunning())
        self.failIf(self.game.willAct(1))

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()
        self.failUnless(self.game.isRunning())

        # The player 1 can not call
        self.failIf(self.game.canCall(1))
        self.failUnless(self.game.willAct(1))

        # The player 1 raise
        self.game.callNraise(1, 100)

        # The player 2 can call and will act
        self.failUnless(self.game.canCall(2))
        self.failIf(player2.talked_once)
        self.failUnless(self.game.willAct(2))

        # The player 2 call
        self.game.callNraise(2, 200)

        # The player 2 has talked so he won't act
        self.failUnless(player2.talked_once)
        self.failIf(self.game.willAct(2))

    # ---------------------------------------------------------
    def testPossibleActions(self):
        """Test Poker Game: Possible actions"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # It is the blind and ante turn so there is no possible action
        self.failUnless(self.game.canAct(1))
        self.failUnless(self.game.isBlindAnteRound())
        self.failUnlessEqual(self.game.possibleActions(1), [])

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # The player 1 can raise or check
        self.failUnless(self.game.canAct(1))
        self.failUnlessEqual(self.game.possibleActions(1), ['raise', 'check'])

        # The player 2 can not do anything because it is not its turn
        self.failUnlessEqual(self.game.possibleActions(2), [])

        # The player 1 raise 1000
        self.game.callNraise(1, 1000)

        # The player 2 can now call, raise or fold
        self.failUnlessEqual(self.game.possibleActions(2), ['call', 'raise', 'fold'])

        # The player 2 can not raise because he has not enough money
        player1.bet = 1800
        self.failUnlessEqual(self.game.possibleActions(2), ['call', 'fold'])

    # ---------------------------------------------------------
    def testBetsNull(self):
        """Test Poker Game: Bets null"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Game is not running
        self.failIf(self.game.betsNull())

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Game is running
        self.failUnless(self.game.betsNull())

        # The player 1 has bet
        player1.bet = 1000
        self.failIf(self.game.betsNull())

        # Th eplayer 1 is fold
        player1.fold =True
        self.failUnless(self.game.betsNull())

    # ---------------------------------------------------------
    def testRoundCap(self):
        """Test Poker Game: Round cap"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Round cap is 0 because the game is not running
        self.failIf(self.game.isRunning())
        self.failUnlessEqual(self.game.roundCap(), 0)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # The game is running
        self.failUnless(self.game.isRunning())

        # First round cap initially equal to 3
        self.failUnlessEqual(self.game.roundCap(), 3)

        # Change the cap of the first level
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round[@name="pre-flop"]', None, {'cap': '20'}):
            self.fail('Error during modification of variant file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # First round cap equal to 20
        self.failUnlessEqual(self.game.roundCap(), 20)

    # ---------------------------------------------------------
    def testBetLimits(self):
        """Test Poker Game: Bet limits"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The game is not running
        self.failUnlessEqual(self.game.betLimitsForSerial(1), (0,0,0))

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # No limit set in the configuration file
        player1.bet = 1000
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (1000, 1600 , 1000))

        # MIN and MAX limits
        # Change the bet infos
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'min': '100', 'max': '300'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Check the bet limits
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (1100, 1300 , 1000))


        # MIN and POT limits
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'min': 'big', 'max': 'pot'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Check the bet limts
        player1.bet = 400
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (1400, 1400, 1000))


        # POW LEVEL limits
        # Change the bet infos
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'pow_level': '100'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Check the bet limits for level 0
        self.failUnlessEqual(self.game.getLevel(), 0)
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (400 + 100 * math.pow(2,-1), 400 + 100 * math.pow(2,-1), 400))


        # FIXED limits
        # Change the bet infos
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'fixed': '100'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Check the bet limits
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (500, 500, 400))

        # ROUND CAP LEFT 0
        self.game.round_cap_left = 0

        # Check the bet limits
        self.failUnlessEqual(self.game.betLimitsForSerial(2), (0, 0, 400))

    # ---------------------------------------------------------
    def testBestHand(self):
        """Test Poker Game: Best hand"""

        player1 = self.AddPlayerAndSit(1, 2)
        player1.hand = pokercards.PokerCards(['Ad', 'As', 'Ah', '3s'])
        self.game.board = pokercards.PokerCards(['9d', '6s', 'Td', '4d', '4h'])

        self.failUnless(self.game.isHigh())

        self.game.variant = 'holdem'
        bestHand = pokercards.PokerCards(['Ad', 'Ah', 'As', '4d', '4h'])
        hand = self.game.bestHand('hi', 1)
        self.failUnlessEqual(pokercards.PokerCards(hand[1][1:]), bestHand)
        self.failUnlessEqual(self.game.readablePlayerBestHand('hi', 1), 'Aces full of Fours: As, Ad, Ah, 4d, 4h')

        self.game.variant = 'omaha'
        bestHand = pokercards.PokerCards(['Ad', 'Ah', '4d', '4h', 'Td'])
        hand = self.game.bestHand('hi', 1)
        self.failUnlessEqual(pokercards.PokerCards(hand[1][1:]), bestHand)
        self.failUnlessEqual(self.game.readablePlayerBestHand('hi', 1), 'Two pairs Aces and Fours, Ten kicker: Ad, Ah, 4d, 4h, Td')

        value, cards = self.game.bestHand('hi', 1)
        self.failUnlessEqual(self.game.bestHandValue('hi', 1), value)
        self.failUnlessEqual(self.game.bestHandCards('hi', 1), cards)

    # ---------------------------------------------------------
    def testBestHands(self):
        """Test Poker Game: Best hands"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Players and board cards
        player1.hand = pokercards.PokerCards(['Ad', 'As', 'Ah', '3s'])
        player2.hand = pokercards.PokerCards(['Jh', '5c', '7d', '2d'])
        self.game.board = pokercards.PokerCards(['9d', '6s', 'Td', '4d', '4h'])

        # Best hands
        bestHand1 = pokercards.PokerCards(['Ad', 'Ah', 'As', '4d', '4h'])
        bestHand2 = pokercards.PokerCards(['7d', '2d', '9d', 'Td', '4d'])

        self.game.variant = 'holdem'
        self.failUnless(self.game.isHigh())

        # Check best hands
        results = self.game.bestHands([1, 2])

        # Player 1 hand
        self.failUnless(1 in results)
        self.failUnless('hi' in results[1])
        self.failUnlessEqual(pokercards.PokerCards(results[1]['hi'][1][1:]), bestHand1)
        self.failUnlessEqual(self.game.readablePlayerBestHands(1), 'Aces full of Fours: As, Ad, Ah, 4d, 4h')

        # Player 2 hand
        self.failUnless(2 in results)
        self.failUnless('hi' in results[2])
        self.failUnlessEqual(pokercards.PokerCards(results[2]['hi'][1][1:]), bestHand2)
        self.failUnlessEqual(self.game.readablePlayerBestHands(2), 'Flush Ten: Td, 9d, 7d, 4d, 2d')

        # Then hand with a NOCARD can not be evaluate
        player1.hand = pokercards.PokerCards(['Jh', '5c', '7d', pokercards.PokerCards.NOCARD])
        results = self.game.bestHands([1])
        self.failUnlessEqual(len(results), 0)

    # ---------------------------------------------------------
    def testBestHandsHoldemFlopStreet(self):
        """Test Poker Game: Best hands, holdem viariant, flop street"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Players and board cards
        player1.hand = pokercards.PokerCards(['Ad', 'As'])
        player2.hand = pokercards.PokerCards(['Jh', '5c'])
        self.game.board = pokercards.PokerCards(['9d', '6s', 'Td'])

        self.game.variant = 'holdem'
        self.failUnless(self.game.isHigh())

        # Player 1 hand
        self.failUnlessEqual(self.game.readablePlayerBestHands(1), 'A pair of Aces, Ten kicker: As, Ad, Td, 9d, 6s')

        # Player 2 hand
        self.failUnlessEqual(self.game.readablePlayerBestHands(2), 'High card Jack: Jh, Td, 9d, 6s, 5c')

    # ---------------------------------------------------------
    def testReadableHandValue(self):
        """Test Poker Game: Readable hand value"""

        self.game.variant = 'holdem'
        player1 = self.AddPlayerAndSit(1, 2)

        player1.hand = pokercards.PokerCards(['2h', '5s', '6h', '9s', 'Ks'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'High card King')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'High card King')

        player1.hand = pokercards.PokerCards(['2h', '2s', '6h', '9s', 'Ks'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Pair of Deuces')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'A pair of Deuces, King kicker')

        player1.hand = pokercards.PokerCards(['3h', '3s', '6h', '6s', 'Ks'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Pairs of Sixes and Treys')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Two pairs Sixes and Treys, King kicker')

        player1.hand = pokercards.PokerCards(['Th', 'Ts', 'Td', '6s', 'Qs'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Trips Tens')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Three of a kind Tens, Queen kicker')

        player1.hand = pokercards.PokerCards(['7h', '8s', '9d', 'Ts', 'Js'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Straight Jack')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Straight Jack to Seven')

        player1.hand = pokercards.PokerCards(['2s', '5s', '6s', '9s', 'Ks'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Flush King')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Flush King')

        player1.hand = pokercards.PokerCards(['Qh', 'Qs', 'Qc', 'Ts', 'Td'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Queens full of Tens')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Queens full of Tens')

        player1.hand = pokercards.PokerCards(['6h', '6s', '6d', '6c', 'Qs'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Quads Sixes, Queen kicker')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Four of a kind Sixes, Queen kicker')

        player1.hand = pokercards.PokerCards(['7h', '8h', '9h', 'Th', 'Jh'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Straight flush')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Straight flush Jack')

        player1.hand = pokercards.PokerCards(['Ts', 'Js', 'Qs', 'Ks', 'As'])
        cards = self.game.bestHandCards('hi', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('hi', cards[0], cards[1:]), 'Royal flush')
        self.failUnlessEqual(self.game.readableHandValueLong('hi', cards[0], cards[1:]), 'Royal flush')

        player1.hand = pokercards.PokerCards(['Ac', '2s', '3h', '4d', '5s'])
        cards = self.game.bestHandCards('low', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('low', cards[0], cards[1:]), 'The wheel')
        self.failUnlessEqual(self.game.readableHandValueLong('low', cards[0], cards[1:]), 'The wheel')

        player1.hand = pokercards.PokerCards(['8h', '2s', '3h', '4d', '5s'])
        cards = self.game.bestHandCards('low', 1)
        self.failUnlessEqual(self.game.readableHandValueShort('low', cards[0], cards[1:]), '8, 5, 4, 3, 2')
        self.failUnlessEqual(self.game.readableHandValueLong('low', cards[0], cards[1:]), '8, 5, 4, 3, 2')

        # Unknown values
        self.failUnlessEqual(self.game.readableHandValueShort('low', 'Unknown', cards[1:]), 'Unknown')
        self.failUnlessEqual(self.game.readableHandValueLong('low', 'Unknown', cards[1:]), 'Unknown')

    # ---------------------------------------------------------
    def testHandEV(self):
        """Test Poker Game: Hand eval"""

        self.game.variant = 'holdem'

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        player1.hand = pokercards.PokerCards(['Ad', 'As'])
        self.failUnless(self.game.handEV(1, 10000) in range(830,870))

        player1.hand = pokercards.PokerCards(['2c', '7s'])
        self.failUnless(self.game.handEV(1, 10000) in range(330,370))

        self.game.board = pokercards.PokerCards(['2c', '3c', '4s'])
        self.failUnless(self.game.handEV(1, 10000) in range(430,470))

        player2.hand = pokercards.PokerCards(['4h', '5c'])
        self.failUnless(self.game.handEV(1, 10000, True) in range(430,470))

        self.failUnless(self.game.handEV(1, 10000) in range(100, 140))

        self.failUnless(self.game.handEV(2, 10000, True) in range(690, 730))
        self.failUnless(self.game.handEV(2, 10000) in range(860, 900))

        self.failUnlessEqual(self.game.handEV(3, 10000), None)

    # ---------------------------------------------------------
    def testMoneyMap(self):
        """Test Poker Game: Money map"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)
        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        player1.money = 1500
        player2.money = 600
        self.failUnlessEqual(self.game.moneyMap(), { 1: 1500, 2: 600})

        player2.fold = True
        self.failUnlessEqual(self.game.moneyMap(), { 1: 1500})

    # ---------------------------------------------------------
    def testHasLevel(self):
        """Test Poker Game: Has level"""

        self.failIf(self.game.hasLevel())

        # Change the blind properties
        blind_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'small': '2000',
            'big': '4000'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnless(self.game.hasLevel())

        if not self.CopyFile(self.ConfigTmplFile, self.ConfigTempFile):
            self.fail('Error during creation of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failIf(self.game.hasLevel())

        # Change the ante properties
        ante_properties = {
            'change': 'double',
            'frequency': '15',
            'unit': 'minute',
            'value': '50',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnless(self.game.hasLevel())

    # ---------------------------------------------------------
    def testLevelUp(self):
        """Test Poker Game: Level up"""

        # The blind properties
        self.failIf(self.game.delayToLevelUp())

        # Change the blind properties
        blind_properties = {
            'change': 'levels',
            'levels': PokerGameTestCase.TestLevelsTemplateFile,
            'frequency': '3',
            'unit': 'minute',
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.failUnless(self.game.hasLevel())

        # Level 0
        self.game.setLevel(0)
        self.failUnless(self.game.delayToLevelUp(), (0, 'minute'))

        # Level 1
        self.game.setLevel(1)
        # The level is not finished
        self.failIf(self.game.levelUp())

        # 3 minutes to wait is a little bit long so this test is not active
        # time.sleep(3 * 60)
        # self.failUnless(self.game.levelUp())

        # Change the blind properties
        blind_properties = {
            'change': 'levels',
            'levels': PokerGameTestCase.TestLevelsTemplateFile,
            'frequency': '3',
            'unit': 'hand',
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Level 0
        self.game.setLevel(0)
        self.failUnless(self.game.delayToLevelUp(), (0, 'hand'))

        # Level 1
        self.game.setLevel(1)
        self.game.setHandsCount(2)
        self.failUnless(self.game.delayToLevelUp(), (5, 'hand'))
        self.failIf(self.game.levelUp())

        # Change the blind properties
        blind_properties = {
            'change': 'levels',
            'levels': PokerGameTestCase.TestLevelsTemplateFile,
            'frequency': '3',
            'unit': 'Invalid',
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        self.failIf(self.game.delayToLevelUp())

        # The game is not directing
        self.game.is_directing = False
        self.failIf(self.game.levelUp())

    # ---------------------------------------------------------
    def testCardsDealt(self):
        """Test Poker Game: Cards dealt"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnless(self.game.cardsDealt())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        self.failIf(self.game.cardsDealt())
        self.failUnlessEqual(self.game.roundInfo()["hand_size"], 2)
        self.failUnlessEqual(self.game.roundInfo()["board_size"], 0)

        player1.hand = pokercards.PokerCards(['Ad', 'As'])
        player2.hand = pokercards.PokerCards(['4d', 'Ts'])

        self.failUnless(self.game.cardsDealt())

        # Second round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isSecondRound())

        self.failIf(self.game.cardsDealt())

        self.failUnlessEqual(self.game.roundInfo()["hand_size"], 2)
        self.failUnlessEqual(self.game.roundInfo()["board_size"], 3)

        self.game.board = pokercards.PokerCards(['Qd', 'Kh', '8c'])
        self.failUnless(self.game.cardsDealt())

    # ---------------------------------------------------------
    def testBet2Pot(self):
        """Test Poker Game: Bet to pot"""

        self.game.registerCallback(Callback)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        InitCallback()
        player1.bet = 500
        self.game.bet2pot(serial = 1, dead_money = True)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(player1.dead, 500)
        self.failUnlessEqual(self.game.pot, 500)

        self.failUnlessEqual(CallbackIds, [self.game.id])
        self.failUnlessEqual(CallbackArgs, [('bet2pot', 1, 500)])

    # ---------------------------------------------------------
    def testDealCards(self):
        """Test Poker Game: Deal cards"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Client game, the deal card has no effect
        self.failIf(self.game.cardsDealt())
        self.game.is_directing = False

        # Deal cards
        self.game.dealCards()

        self.failIf(self.game.cardsDealt())
        self.game.is_directing = True

        # Deal the cards
        self.failIf(self.game.cardsDealt())

        # Deal cards
        self.game.dealCards()

        self.failUnless(self.game.cardsDealt())

        # The cards are hidden
        self.failUnless(player1.hand.areHidden())
        self.failUnless(player2.hand.areHidden())

        # Check the players cards
        player1_cards = pokercards.PokerCards(['8s', 'As'])
        player2_cards = pokercards.PokerCards(['3h', '6d'])
        player1_cards.allHidden()
        player2_cards.allHidden()

        self.failUnlessEqual(player1.hand, player1_cards)
        self.failUnlessEqual(player2.hand, player2_cards)

        # Second round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isSecondRound())

        # Deal cards
        self.game.dealCards()

        # Check the board cards
        self.failUnlessEqual(self.game.board, pokercards.PokerCards(['6s', '6h', 'Ah']))

        # Next round
        self.game.nextRound()
        self.game.initRound()

        # There is not enough cards in the deck for all the players
        info = self.game.roundInfo()
        info['board'] = ['board', 'board']
        info["board_size"] = 2

        info['cards'] = ['up', 'down']
        info["hand_size"] = 2

        self.game.deck = ['8d', '2h', '2c', '8c']

        # Deal cards
        self.game.dealCards()

        # The player cards are transfered to the board
        self.failUnlessEqual(info["hand_size"], 0)
        self.failUnlessEqual(info["board_size"], 4)

        # Can not deal all the cards needed
        info = self.game.roundInfo()
        info['board'] = ['board', 'board']
        info["board_size"] = 2

        info['cards'] = ['up', 'unknown', 'down']
        info["hand_size"] = 3

        self.game.deck = ['8d', '2h', '2c', '8c']

        self.failUnlessRaises(UserWarning,self.game.dealCards)

    # ---------------------------------------------------------
    def testBotAutoPlay(self):
        """Test Poker Game: Bot auto play"""

        # Change the bet properties
        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'min': '100', 'max': '300'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        # Change the variant name for cards evaluation
        self.game.variant = 'holdem'

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # No possible action because the cards are not dealt
        self.failUnlessEqual(self.game.possibleActions(1), [])
        self.game.botPlayer(1)
        self.failIf(player1.talked_once)

        # Deal cards
        self.game.dealCards()

        # Player 1 is a bot
        self.failUnlessEqual(self.game.possibleActions(1), ['raise', 'check'])
        self.game.botPlayer(1)
        self.failUnless(player1.isBot())
        self.failUnless(player1.isAutoBlindAnte())
        self.failUnlessEqual(player1.auto_muck, pokergame.AUTO_MUCK_ALWAYS)
        self.failUnless(player1.isAuto())

        # Player 1 automatically bet the minimum
        self.failUnlessEqual(player1.bet, 100)
        self.failUnlessEqual(player1.money, 1500)
        self.failUnless(player1.talked_once)

        # Player 2 automatically call
        self.game.botPlayer(2)

        # The game is finished
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)

    # ---------------------------------------------------------
    def testGetRequestedAction(self):
        """Test Poker Game: Get requested action"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 2 is in position
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)
        self.failUnlessEqual(self.game.getRequestedAction(1), None)
        self.failUnlessEqual(self.game.getRequestedAction(2), 'blind_ante')

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Player 2 is in position
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)
        self.failUnlessEqual(self.game.getRequestedAction(2), 'play')

        # Add a third player
        self.failUnless(self.game.addPlayer(3))
        player3 = self.GetPlayer(3)

        # The buy in is not payed
        self.failIf(player3.isBuyInPayed())
        self.failUnlessEqual(self.game.getRequestedAction(3), 'buy-in')

        # Pay the buy in
        self.failUnless(self.game.payBuyIn(3,self.game.bestBuyIn()))
        self.failUnlessEqual(self.game.getRequestedAction(3), None)

        # Player 3 has no money
        player3.money = 0
        self.failUnlessEqual(self.game.getRequestedAction(3), 'rebuy')

        # Change the blind properties
        blind_properties = {
            'change': 'levels',
            'levels': PokerGameTestCase.TestLevelsTemplateFile,
            'frequency': '15',
            'unit': 'minute'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # The game is now a tournament
        self.failUnless(self.game.isTournament())

        # The player 1 and 3 are not in position
        self.failUnlessEqual(self.game.getRequestedAction(3), None)
        self.failUnlessEqual(self.game.getRequestedAction(1), None)

        # The player 2 is in position
        self.failUnlessEqual(self.game.getRequestedAction(2), 'play')

    # ---------------------------------------------------------
    def testTalked(self):
        """Test Poker Game: Talked"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.call(1))

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # Player 1 can talk
        self.failUnless(self.game.isInPosition(1))
        self.failUnless(self.game.canAct(1))
        self.failIf(player1.talked_once)

        self.failUnless(self.game.callNraise(1, 600))

        self.failUnlessEqual(player1.bet, 600)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1000)
        self.failUnless(player1.talked_once)

        # Player 2 can talk
        self.failUnless(self.game.isInPosition(2))
        self.failUnless(self.game.canAct(2))
        self.failIf(player2.talked_once)

        self.failUnless(self.game.call(2))

        self.failUnlessEqual(self.game.getPlayerMoney(2), 1000)

        # Second round
        self.failUnless(self.game.isSecondRound())

    # ---------------------------------------------------------
    def testTalkedClientGame(self):
        """Test Poker Game: Talked Client game"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.call(1))

        # Automatically pay the blind
        self.game.autoBlindAnte(1)
        self.game.autoBlindAnte(2)

        # First round
        self.failUnless(self.game.isFirstRound())

        # Client game
        self.game.is_directing = False

        # player 1 raise
        self.failUnless(self.game.callNraise(1, 600))

        # Player 2 call
        self.failUnless(self.game.call(2))

        # Init round is not done
        # The players are mot reset
        self.failUnless(player1.talked_once)
        self.failUnless(player2.talked_once)

    # ---------------------------------------------------------
    def testBlindInfo(self):
        """Test Poker Game: Blind info"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Blind info has been set
        self.failUnless(self.game.blind_info)

        # Check the blind values
        self.failUnlessEqual(self.game.bigBlind(), 1000)
        self.failUnlessEqual(self.game.smallBlind(), 500)

        # Check blind amounts
        self.game.setPlayerBlind(1, 'big')
        self.failUnlessEqual(self.game.blindAmount(1), (self.game.bigBlind(), 0, 'big'))
        self.game.setPlayerBlind(1, 'late')
        self.failUnlessEqual(self.game.blindAmount(1), (self.game.bigBlind(), 0, 'late'))
        self.game.setPlayerBlind(1, 'small')
        self.failUnlessEqual(self.game.blindAmount(1), (self.game.smallBlind(), 0, 'small'))
        self.game.setPlayerBlind(1, 'big_and_dead')
        self.failUnlessEqual(self.game.blindAmount(1), (self.game.bigBlind(), self.game.smallBlind(), 'big_and_dead'))
        self.game.setPlayerBlind(1, False)
        self.failUnlessEqual(self.game.blindAmount(1), (0, 0, False))
        self.game.setPlayerBlind(1, True)
        self.failUnlessEqual(self.game.blindAmount(1), (0, 0, True))
        self.game.setPlayerBlind(1, 'invalid')
        self.failUnlessEqual(self.game.blindAmount(1), None)

        # Unset the blind infos
        self.game.blind_info = None
        self.failUnlessEqual(self.game.bigBlind(), None)
        self.failUnlessEqual(self.game.smallBlind(), None)
        self.failUnlessEqual(self.game.blindAmount(1), (0, 0, False))

    # ---------------------------------------------------------
    def testSitOutNextTurn(self):
        """Test Poker Game: Sit out next turn"""

        self.game.setMaxPlayers(3)

        # Create all the players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 2 is in position
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)

        # The player 2 sit out next turn
        self.failIf(self.game.isSitOut(2))
        self.failUnless(self.game.sitOutNextTurn(2))
        self.failUnless(player2.isSitOut())
        self.failIf(player2.sit_out_next_turn)
        self.failIf(player2.sit_requested)
        self.failIf(player2.wait_for)

        # The player 1 is not in position but he want to sit out
        self.failIfEqual(self.game.getSerialInPosition(), 1)
        self.failIf(player1.sit_out_next_turn)
        self.failIf(player1.sit_requested)
        self.failIf(self.game.sitOutNextTurn(1))
        self.failUnless(player1.sit_out_next_turn)
        self.failIf(player1.sit_requested)

        # Client game
        self.game.is_directing = False

        # Player 3 sit out
        self.failUnlessEqual(self.game.getSerialInPosition(), 3)
        self.failIf(player3.sit_out_next_turn)
        self.failIf(player3.sit_requested)
        self.failIf(self.game.sitOutNextTurn(3))
        self.failUnless(player3.sit_out_next_turn)
        self.failIf(player3.sit_requested)
        self.failUnlessEqual(player3.wait_for, False)

    # ---------------------------------------------------------
    def testSitOut(self):
        """Test Poker Game: Sit out"""

        self.game.setMaxPlayers(4)

        player1 = self.AddPlayerAndSit(1, 1)
        player2 = self.AddPlayerAndSit(2, 3)
        player3 = self.AddPlayerAndSit(3, 6)
        player4 = self.AddPlayerAndSit(4, 8)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Sit out
        self.game.setPosition(0)
        self.failIf(self.game.getSitOut(1))
        self.failUnless(self.game.sitOut(1))
        self.failUnless(self.game.getSitOut(1))
        self.failIf(player1.sit_out_next_turn)
        self.failIf(player1.sit_requested)
        self.failIf(player1.wait_for)

        # the player is already sit out
        self.failIf(self.game.sitOut(1))

        self.game.setPosition(1)
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)

        self.game.setPosition(2)
        self.failIf(self.game.getSitOut(3))
        self.failUnless(self.game.sitOut(3))
        self.failUnless(self.game.getSitOut(3))
        self.failIf(player3.sit_out_next_turn)
        self.failIf(player3.sit_requested)
        self.failIf(player3.wait_for)

        self.failUnlessEqual(self.game.getSerialInPosition(), 4)

        #
        # Check that autoPayBlindAnte skips players that are sit out for some reason.
        #
        player1.sit_out = True
        self.game.setPosition(0)
        self.assertEquals([1, 2, 3, 4], self.game.player_list)
        self.game.autoPayBlindAnte()

    # ---------------------------------------------------------
    def testSit(self):
        """Test Poker Game: Sit"""

        self.game.setMaxPlayers(3)

        # Add Player
        self.failUnless(self.game.addPlayer(1, 2))
        player1 = self.GetPlayer(1)
        self.failIf(player1.isSit())

        # The buy in is not payed, the player can not be added
        self.failIf(player1.isBuyInPayed())
        self.failIf(self.game.sit(1))

        # Pay the buy in
        self.failUnless(self.game.payBuyIn(1,self.game.bestBuyIn()))
        self.failUnless(player1.isBuyInPayed())

        # The player is broke, the player can not be added
        money = self.game.getPlayerMoney(1)
        player1.money = 0
        self.failUnless(self.game.isBroke(1))
        self.failIf(self.game.sit(1))

        # Restore the player money
        player1.money = money
        self.failIf(self.game.isBroke(1))

        # The player can sit
        player1.wait_for = 'big'
        self.failUnless(self.game.sit(1))

        self.failUnless(player1.isSit())
        self.failUnlessEqual(player1.wait_for, False)
        self.failIf(player1.auto)

        # Add a second player
        player2 = self.AddPlayerAndSit(2, 5)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Add the third player
        self.failUnless(self.game.addPlayer(3, 7))
        self.failUnless(self.game.payBuyIn(3,self.game.bestBuyIn()))
        player3 = self.GetPlayer(3)
        self.failIf(player3.isSit())

        # The player sit
        self.failUnless(self.game.sit(3))
        self.failUnless(player3.isSit())
        self.failUnlessEqual(player3.wait_for, 'first_round')

    # ---------------------------------------------------------
    def testRebuy(self):
        """Test Poker Game: Rebuy"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        self.failUnlessEqual(self.game.maxBuyIn(), 10000)

        # The player 3 is unknown so it can not rebuy
        self.failIf(self.game.rebuy(3, 100))

        # The player money + the rebuy amount is too low
        player1.money = 10
        self.failIf(self.game.rebuy(1, 10))

        # The player money + the rebuy amount is too high
        player1.money = 5000
        self.failIf(self.game.rebuy(1, 5001))

        # Test rebuy when game is not directing
        self.game.is_directing = False

        # The player money + the rebuy amount is too low, but game is not directing
        player1.money = 10
        self.failUnless(self.game.rebuy(1, 10))

        # The player money + the rebuy amount is too high, but game is not directing
        player1.money = 5000
        self.failUnless(self.game.rebuy(1, 5001))

        # Reset game and player money
        self.game.is_directing = True
        player1.money = 5000

        # The player 1 rebuy 1000 but the game is not running so the money is added to it rebuy amount
        self.failIf(self.game.isPlaying(1))
        self.failUnless(self.game.rebuy(1, 1000))
        self.failUnless(self.game.getPlayerMoney(1), 5000)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 1 rebuy 1000 and the game is not running so the money is added directly to its money amount
        self.failUnless(self.game.isPlaying(1))
        self.failUnless(self.game.rebuy(1, 1000))
        self.failUnless(self.game.getPlayerMoney(1), 6000)

    # ---------------------------------------------------------
    def testFullEmpty(self):
        """Test Poker Game: Full empty"""

        # The game must be empty
        self.failUnless(self.game.empty())
        self.failIf(self.game.full())

        # Add one player
        player1 = self.AddPlayerAndSit(1, 2)

        # The game is not empty and not full
        self.failIf(self.game.empty())
        self.failIf(self.game.full())

        # Add the second player, the game is now full
        player2 = self.AddPlayerAndSit(2, 7)

        self.failIf(self.game.empty())
        self.failUnless(self.game.full())

    # ---------------------------------------------------------
    def testSerialsAllSorted(self):
        """Test Poker Game: Serials all sorted"""

        self.game.setMaxPlayers(3)

        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # The dealer is not specified or incorrect so get the list of player sorted by serial number
        self.game.dealer = -1
        self.failUnlessEqual(self.game.serialsAllSorted(), [1, 2, 3])
        self.game.dealer = 4
        self.failUnlessEqual(self.game.serialsAllSorted(), [1, 2, 3])

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnlessEqual(self.game.dealer, 0)
        self.failUnlessEqual(self.game.serialsAllSorted(), [2, 3, 1])

        # Remove the player 1, do not reconstruct the player list
        del self.game.serial2player[1]
        self.failUnlessEqual(self.game.serialsAll(), [2, 3])
        self.failUnlessEqual(self.game.player_list, [1, 2, 3])

        # The dealer can not be the player 2
        self.failUnlessEqual(self.game.serialsAllSorted(), [3, 2])

    # ---------------------------------------------------------
    def testSerialsInactive(self):
        self.game.setMaxPlayers(3)

        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # pre-test: all players should not be on auto when started
        self.assertEquals(player3.auto, False)

        self.assertEquals(self.game.serialsInactive(), [])

        player1.auto = True
        self.assertEquals(self.game.serialsInactive(), [player1.serial])

        player2.auto = True
        player2.action_issued = True
        self.assertEquals(self.game.serialsInactive(), [player1.serial])

    # ---------------------------------------------------------
    def testBlind(self):
        """Test Poker Game: Blind"""

        self.game.setMaxPlayers(3)

        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Not Blind or Ante turn
        self.failIf(self.game.isBlindAnteRound())
        self.failIf(self.game.blind(1))

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 1 can not act so it can not blind
        self.failIf(self.game.canAct(1))
        self.failIf(self.game.isBlindRequested(1))
        self.failIf(self.game.blind(1))

        # Get the blind limits for player 2
        self.game.setPlayerBlind(2, 'big_and_dead')
        self.failUnlessEqual(self.game.blindAmount(2), (1000, 500, 'big_and_dead'))

        # The player 2 can blind, use the defined limits
        self.failUnless(self.game.isBlindRequested(2))
        self.game.blind(2)
        self.failUnlessEqual(player2.bet, 1000)
        self.failUnlessEqual(self.game.pot, 500)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 100)

        # The player 2 has blind
        self.failUnless(player2.blind)
        self.failUnlessEqual(player2.missed_blind, None)
        self.failIf(player2.wait_for)

        # The player 3 can blind, bet 400 and 200 for the dead
        self.failUnless(self.game.isBlindRequested(3))
        self.game.blind(3, 400, 200)
        self.failUnlessEqual(player3.bet, 400)
        self.failUnlessEqual(self.game.pot, 500 + 200)
        self.failUnlessEqual(player3.money, 1000)

        # Blind structure unknown
        self.game.blind_info = None

        # The blind has not effect
        self.failIf(self.game.isBlindRequested(1))
        self.game.blind(1, 400, 200)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.pot, 500 + 200)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)

    # ---------------------------------------------------------
    def testBlindAnteRoundEnd(self):
        """Test Poker Game: Blind and ante round end"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # No effect for server game
        self.game.blindAnteRoundEnd()
        self.failUnless(self.game.isBlindAnteRound())

        # Client game
        self.game.is_directing = False

        # First Round
        self.game.blindAnteRoundEnd()
        self.failUnless(self.game.isFirstRound())

        # Blind and ante round
        self.game.resetRound()
        self.game.initBlindAnte()
        self.failUnless(self.game.isBlindAnteRound())

        # Player 1 is all in
        self.game.payBlind(1, 1600, 0)
        self.failUnlessEqual(player1.bet, 1600)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 0)
        self.failUnless(player1.isAllIn())
        self.failIf(self.game.isInGame(1))

        self.game.payBlind(2, 1600, 0)

        # All the players are all in except one
        self.game.blindAnteRoundEnd()
        self.failUnlessEqual(self.game.pot, 3200)

        # First Round
        self.failUnless(self.game.isFirstRound())

    # ---------------------------------------------------------
    def testPayBlind(self):
        """Test Poker Game: Pay blind"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.isBlindAntePayed())

        # The player 1 pay blind
        self.game.payBlind(1, 600, 200)
        self.failUnlessEqual(player1.bet, 600)
        self.failUnlessEqual(self.game.pot, 200)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 800)
        self.failUnless(player1.blind)
        self.failUnlessEqual(player1.missed_blind, None)
        self.failIf(player1.wait_for)

        # All blinds are not payed
        self.failIf(self.game.isBlindAntePayed())

        # The blind is higher than the player money
        self.game.payBlind(2, 2000, 100)
        self.failUnlessEqual(player2.bet, 1600)
        self.failUnlessEqual(self.game.pot, 200 + 0)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 0)
        self.failUnless(player2.blind)
        self.failUnlessEqual(player2.missed_blind, None)
        self.failIf(player2.wait_for)

        # All blinds are not payed
        self.failIf(self.game.isBlindAntePayed())

        # The blind + the dead is higher than the player money
        self.game.payBlind(3, 1000, 1000)
        self.failUnlessEqual(player3.bet, 1000)
        self.failUnlessEqual(self.game.pot, 200 + 0 + 600)
        self.failUnlessEqual(player3.money, 0)
        self.failUnless(player3.blind)
        self.failUnlessEqual(player3.missed_blind, None)
        self.failIf(player3.wait_for)

        # All blinds are now payed
        self.failUnless(self.game.isBlindAntePayed())

    # ---------------------------------------------------------
    def testWaitBigBlind(self):
        """Test Poker Game: Wait big blind"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 2 can not act
        self.failIf(self.game.canAct(2))
        self.failIf(self.game.waitBigBlind(2))

        # No blind info
        blind_info = self.game.blind_info
        self.game.blind_info = None
        self.failIf(self.game.waitBigBlind(1))
        self.failIf(self.game.waitBigBlind(2))
        self.game.blind_info = blind_info

        # The player 1 can act
        self.failUnless(self.game.canAct(1))
        self.failUnless(self.game.waitBigBlind(1))
        self.failUnlessEqual(player1.wait_for, 'big')

        # Player 2 pay the blind
        self.failUnless(self.game.canAct(2))
        self.game.autoBlindAnte(2)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 600)
        self.failUnlessEqual(player2.bet, 1000)
        self.failUnless(player2.isBlind())

        # Player 1 pay the blind
        self.failUnless(self.game.canAct(1))
        self.game.autoBlindAnte(1)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)
        self.failUnlessEqual(player1.bet, 500)
        self.failUnless(player1.isBlind())

        # Blind and ante turn finished
        self.failIf(self.game.isBlindAnteRound())

        # Waiting big blind is unavalaible
        self.failIf(self.game.waitBigBlind(1))
        self.failIf(self.game.waitBigBlind(2))

    # ---------------------------------------------------------
    def testAnte(self):
        """Test Poker Game: Ante"""

        # Change the ante properties
        ante_properties = {
            'value': '100',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        self.game.setMaxPlayers(3)

        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Not Blind or Ante turn
        self.failIf(self.game.isBlindAnteRound())
        self.failIf(self.game.ante(1))

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 1 can not act so it can not ante
        self.failIf(self.game.canAct(1))
        self.failIf(self.game.isAnteRequested(1))
        self.failIf(self.game.ante(1))

        # Get the ante value
        self.failUnlessEqual(self.game.ante_info['value'], 100)

        # The player 2 can ante, use the defined limits
        self.failUnless(self.game.isAnteRequested(2))
        self.game.ante(2)
        self.failUnlessEqual(player2.bet, 0)
        self.failUnlessEqual(self.game.pot, 100)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1500)

        # The player 2 has ante
        self.failUnless(player2.ante)

        # The player 3 can ante 400
        self.failUnless(self.game.isAnteRequested(3))
        self.game.ante(3, 400)
        self.failUnlessEqual(player3.bet, 0)
        self.failUnlessEqual(self.game.pot, 100 + 400)
        self.failUnlessEqual(player3.money, 1200)

        # Ante structure unknown
        self.game.ante_info = None

        # The ante has not effect
        self.failIf(self.game.isAnteRequested(1))
        self.game.ante(1, 400)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.pot, 100 + 400)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)

    # ---------------------------------------------------------
    def testAutoPayBlind(self):
        """ Test Poker Game: Auto pay blind"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players are not auto
        self.failIf(player1.isAutoBlindAnte())
        self.failIf(player2.isAutoBlindAnte())
        self.failIf(player3.isAutoBlindAnte())

        # The auto pay blind has no effect
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)
        self.game.autoPayBlindAnte()

        # The player 2 is still in position
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)

        # The turn is still blind and ante
        self.failUnless(self.game.isBlindAnteRound())

        # pay the blind for player 2
        player2.auto_blind_ante = True
        self.game.autoPayBlindAnte()

        # The player 3 sit out
        self.failUnless(self.game.sitOut(3))
        self.failUnless(player3.isSitOut())
        self.failUnlessEqual(self.game.getSerialInPosition(), 1)

        # pay the blind for player 1
        player1.auto_blind_ante = True
        self.game.autoPayBlindAnte()
        self.failUnlessEqual(True, player1.isBlind())

        # The blind of the player 1 and 2 are automatically payed
        self.game.autoPayBlindAnte()

        self.failUnlessEqual(self.game.getPlayerMoney(1), 600)
        self.failUnlessEqual(player1.bet, 1000)
        self.failUnless(player1.blind)

        self.failUnlessEqual(self.game.getPlayerMoney(2), 1100)
        self.failUnlessEqual(player2.bet, 500)
        self.failUnless(player2.blind)

        # First round
        self.failUnless(self.game.isFirstRound())

    # ---------------------------------------------------------
    def testAutoPayBlindAllIn(self):
        """ Test Poker Game: Auto pay blind all in"""

        self.game.variant = 'holdem'

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player1.money = 400
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players 1 automatically pay the blind
        self.game.autoBlindAnte(1)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 0)
        self.failUnlessEqual(player1.bet, 400)
        self.failUnless(player1.blind)

        # Player 1 is all in
        self.failUnless(player1.isAllIn())

        # The players 2 automatically pay the blind
        self.game.autoBlindAnte(2)

        # The game is finished
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)

        # Check the end information
        self.failUnless(self.game.isGameEndInformationValid())

        # The player 1 win
        self.failUnlessEqual(self.game.winners, [1])
        self.failUnlessEqual(player1.money, 400 + ( 400 - self.game.getRakedAmount() ))
        self.failUnlessEqual(player2.money, 1600 - 400)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(player2.bet, 0)
        self.failUnlessEqual(self.game.pot, 0)

    # ---------------------------------------------------------
    def testAutoPayBlindAllIn2(self):
        """ Test Poker Game: Auto pay blind all in and a third player is to act"""

        self.game.variant = 'holdem'

        # Create players
        self.game.setMaxPlayers(3)
        player1 = self.AddPlayerAndSit(1, 2)
        player1.money = 600
        player2 = self.AddPlayerAndSit(2, 5)
        player2.money = 400
        player3 = self.AddPlayerAndSit(3, 7)
        player3.money = 600

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players 2 automatically pay the blind
        self.game.autoBlindAnte(2)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 0)
        self.failUnlessEqual(player2.bet, 400)
        self.failUnless(player2.blind)

        # Player 2 is all in
        self.failUnless(player2.isAllIn())

        # The players 3 automatically pay the blind
        self.game.autoBlindAnte(3)

        # The players 1 is to act and calls
        self.failUnless(self.game.canAct(1))
        self.failUnless(self.game.call(1))

        # The game is finished
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)

        # Check the end information
        self.failUnless(self.game.isGameEndInformationValid())

        # The player 3 win
        self.failUnlessEqual(self.game.winners, [3])
        self.failUnlessEqual(player3.money, 600 + 600 + 400 - self.game.getRakedAmount() )
        self.failUnlessEqual(player2.money, 0)
        self.failUnlessEqual(player1.money, 0)
        self.failUnlessEqual(self.game.pot, 0)

    # ---------------------------------------------------------
    def testAutoPayAnte(self):
        """ Test Poker Game: Auto pay ante"""

        # Change the ante properties
        ante_properties = {
            'value': '100',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Reset the blind infos
        self.game.blind_info = None

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players are not auto
        self.failIf(player1.isAutoBlindAnte())
        self.failIf(player2.isAutoBlindAnte())

        # The auto pay ante has no effect
        self.failUnlessEqual(self.game.getSerialInPosition(), 1)
        self.game.autoPayBlindAnte()
        # The player 2 is still in position
        self.failUnlessEqual(self.game.getSerialInPosition(), 1)
        # The turn is still blind and ante
        self.failUnless(self.game.isBlindAnteRound())

        # The antes will be automatically payed
        player1.auto_blind_ante = True
        player2.auto_blind_ante = True

        # The ante of the player 1 and 2 are automatically payed
        self.game.autoPayBlindAnte()

        self.failUnlessEqual(self.game.getPlayerMoney(1), 1500)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnless(player1.ante)

        self.failUnlessEqual(self.game.getPlayerMoney(2), 1500)
        self.failUnlessEqual(player2.bet, 0)
        self.failUnless(player2.ante)

        self.failUnlessEqual(self.game.pot, 100 + 100)

        # The blind and ante turn is finished
        self.failIf(self.game.isBlindAnteRound())

    # ---------------------------------------------------------
    def testAutoPayAnteAllIn(self):
        """ Test Poker Game: Auto pay ante all in"""

        self.game.variant = 'holdem'

        # Change the ante properties
        ante_properties = {
            'value': '900',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Reset the blind infos
        self.game.blind_info = None

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players 1 automatically pay the blind
        self.game.autoBlindAnte(1)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 700)
        self.failUnlessEqual(self.game.pot, 900)
        self.failUnless(player1.ante)

        # Player 1 is all in
        player1.all_in = True
        self.failUnless(player1.isAllIn())

        # The players 2 automatically pay the blind
        self.game.autoBlindAnte(2)

        # The game is finished
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)

        # Check the end information
        self.failUnless(self.game.isGameEndInformationValid())

        # The player 1 win
        self.failUnlessEqual(self.game.winners, [1])

        rake = self.game.getRakedAmount()
        self.failUnlessEqual(int(1800 * 0.05), rake)
        self.failUnlessEqual(player1.money, 1600 + ( 900 - rake ))
        self.failUnlessEqual(player2.money, 1600 - ( 900 ))
        self.failUnlessEqual(self.game.pot, 0)

        #
        # The rake must be deduced from the delta
        #
        showdown_info = self.game.showdown_stack[0]
        self.failUnlessEqual(900 - rake, showdown_info['serial2delta'][1])
        self.failUnlessEqual(-900, showdown_info['serial2delta'][2])

    # ---------------------------------------------------------
    def testPayAnte(self):
        """Test Poker Game: Pay ante"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        self.game.variant = 'holdem'

        # Change the ante properties
        ante_properties = {
            'value': '100',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Reset the blind infos
        self.game.blind_info = None

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failIf(self.game.isBlindAntePayed())

        # The player 1 pay ante
        self.game.payAnte(1, 600)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.pot, 600)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1000)
        self.failUnless(player1.ante)

        # All antes are not payed
        self.failIf(self.game.isBlindAntePayed())

        # The ante is higher than the player money
        self.game.payAnte(2, 2000)
        self.failUnlessEqual(player2.bet, 0)
        self.failUnlessEqual(self.game.pot, 600 + 1600)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 0)
        self.failUnless(player2.ante)

        # All antes are not payed
        self.failIf(self.game.isBlindAntePayed())

        # The player 3 is sit out
        self.game.setPosition(2)
        self.failUnless(self.game.sitOut(3))

        # All antes are now payed
        self.failUnless(self.game.isBlindAntePayed())

    # ---------------------------------------------------------
    def testMinMoney(self):
        """Test Poker Game: min money"""

        #
        # game with blinds
        #
        self.failUnless(self.game.minMoney() > self.game.blind_info["big"]);

        #
        # game with antes
        #
        # Change the ante properties
        ante_properties = {
            'value': '100',
            'bring-in': '200'
        }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet', 'ante', ante_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Reset the blind infos
        self.game.blind_info = None
        self.failUnless(self.game.minMoney() > self.game.ante_info["bring-in"]);

        #
        # tournament
        #
        self.game.ante_info["change"] = True;
        self.failUnlessEqual(self.game.minMoney(), 0)

        #
        # no blinds, no antes
        #
        self.game.blind_info = None
        self.game.ante_info = None
        self.failUnlessEqual(self.game.minMoney(), 0)

    # ---------------------------------------------------------
    def testIsBroke(self):
        """Test Poker Game: Is broke"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Unknown players are not broke
        self.failIf(self.game.isBroke(3))

        # No player is broke
        self.failIf(self.game.isBroke(1))
        self.failIf(self.game.isBroke(2))
        self.failUnlessEqual(self.game.brokeCount(), 0)

        # The player 1 is broke, no money
        player1.money = 0

        # One player broke
        self.failUnless(self.game.isBroke(1))
        self.failUnlessEqual(self.game.brokeCount(), 1)
        self.failUnlessEqual(self.game.serialsBroke(), [1])
        self.failUnlessEqual(self.game.playersBroke(), [player1])

        # The player 2 is borke, not enough money to play
        self.failIf(self.game.isTournament())

        # Change the blind properties
        blind_properties = { 'small': '1000',
                                    'big': '2000',
                                }

        if not self.ModifyXMLFile(self.ConfigTempFile, '/bet/blind', None, blind_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)

        # Nothing should have changed
        self.failIf(self.game.isBroke(2))
        self.failUnlessEqual(self.game.brokeCount(), 1)
        self.failUnlessEqual(self.game.serialsBroke(), [1])
        self.failUnlessEqual(self.game.playersBroke(), [player1])

    # ---------------------------------------------------------
    def testAllIn(self):
        """Test Poker Game: All in"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players are not initially all in
        self.failIf(player1.isAllIn())
        self.failIf(player2.isAllIn())
        self.failUnlessEqual(self.game.allInCount(), 0)

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # The player 1 put all his money
        self.failUnless(self.game.callNraise(1, self.game.getPlayerMoney(1)))
        self.failUnless(player1.isAllIn())
        self.failUnlessEqual(self.game.allInCount(), 1)
        self.failUnlessEqual(self.game.serialsAllIn(), [1])
        self.failUnlessEqual(self.game.playersAllIn(), [player1])

    # ---------------------------------------------------------
    def testUncalledInvalid(self):
        """Test Poker Game: uncalled amount does not pass distributeMoney checks"""

        self.game.setVariant('holdem')

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)
        player2.money += player1.money
        uncalled = player2.money

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The players are not initially all in
        self.failIf(player1.isAllIn())
        self.failIf(player2.isAllIn())
        self.failUnlessEqual(self.game.allInCount(), 0)

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # The player 1 put all his money
        self.failUnless(self.game.call(1))
        self.failUnless(self.game.callNraise(2, self.game.getPlayerMoney(2)))
        self.failUnless(player2.isAllIn())
        self.failUnlessEqual(self.game.allInCount(), 1)
        self.failUnlessEqual(self.game.serialsAllIn(), [2])
        self.failUnlessEqual(self.game.playersAllIn(), [player2])
        self.failUnlessEqual(self.game.uncalled, uncalled)
        distributeMoney = self.game.distributeMoney
        def f():
            self.game.uncalled = 42 # invalid value
            distributeMoney()
        self.game.distributeMoney = f
        try:
            self.game.call(1)
        except UserWarning, arg:
            self.failUnlessEqual(str(arg), "serial2side_pot[winner.serial] != self.uncalled (1600 != 42)")


    # ---------------------------------------------------------
    def testRakeContributions(self):
        """Test Poker Game: rake contributions"""

        self.game.setVariant('holdem')
        # Create players
        self.game.setMaxPlayers(3)
        for i in xrange(1, 4):
            self.AddPlayerAndSit(i)
            self.game.botPlayer(i)

        self.game.beginTurn(1)

        self.failIf(self.game.isRunning())
        self.failUnlessEqual(150, self.game.getRakedAmount())
        self.failUnlessEqual(3000, self.game.getPotAmount())
        self.failUnlessEqual({1: 50, 2: 50, 3: 50}, self.game.getRakeContributions())

    # ---------------------------------------------------------
    def testRakeContributionsUncalled(self):
        """Test Poker Game: rake contributions uncalled"""

        self.game.setVariant('holdem')
        # Create players
        self.game.setMaxPlayers(3)
        for i in xrange(1, 4):
            player = self.AddPlayerAndSit(i)
            self.game.botPlayer(i)
            player.money = 100
        player.money = 3000

        self.game.beginTurn(1)

        self.failIf(self.game.isRunning())
        self.failUnlessEqual(15, self.game.getRakedAmount())
        self.failUnlessEqual(700, self.game.getPotAmount())
        self.failUnlessEqual({1: 5, 2: 5, 3: 5}, self.game.getRakeContributions())

    # ---------------------------------------------------------
    def testRake(self):
        self.game.variant = 'holdem'
        class PokerRakeHalf:
            def __init__(self, game):
                pass
            def getRake(self, pot, uncalled, is_tournament):
                return int((pot - uncalled) * .4)

        self.game.rake = PokerRakeHalf(self.game)
        cards = [4, 37, 2, 29, 48, 16, 22, 23, 8, 3, 7]
        self.game.deck = self.game.eval.card2string(cards)
        self.game.shuffler = PokerPredefinedDecks([cards])

        # Create players
        player_serials = [1,2,3]
        player_seats = [2,5,7]
        player_money = [100000,1000,50000]
        players = {}

        self.game.setMaxPlayers(3)
        for (serial,seat,money) in zip(player_serials,player_seats,player_money):
            players[serial] = self.AddPlayerAndSit(serial,seat)
            players[serial].money = money
            self.game.autoBlindAnte(serial)

        self.game.beginTurn(1)
        self.failUnless(self.game.isFirstRound())

        self.game.callNraise(1, 90000)
        self.game.call(2)
        self.game.call(3)

        for (serial,player) in players.items():
            self.assertTrue(player.money>=0,"player %d has less than 0 money: %d" % (serial,player.money))

    # ---------------------------------------------------------
    def testRake2(self):
        self.game.variant = 'holdem'

        class PokerRakeMock:
            def __init__(self, game):
                pass
            def getRake(self, pot, uncalled, is_tournament):
                return int((pot - uncalled) * .1)

        self.game.rake = PokerRakeMock(self.game)
#        deck info
        cards_to_player = (
            (145,('6d','As')),
            (148,('Qc','2s')),
            (147,('4s','Qh')),
            (150,('3h','4c')),
        )
        cards_board = ('9c','8h','9h','9d','4d')
#        build deck
        cards = []
        for i in range(2):
            for (player,card_strings) in cards_to_player:
                cards.append(self.game.eval.string2card(card_strings[i]))
        cards.extend(self.game.eval.string2card(cards_board))

        cards.reverse()

        self.game.deck = self.game.eval.card2string(cards)
        self.game.shuffler = PokerPredefinedDecks([cards])

        PlayerMock = namedtuple('PlayerMock', ('serial','seat','money'))
        players_simple = [
            PlayerMock(145, 1, 640000),
            PlayerMock(148, 3, 10000),
            PlayerMock(147, 6, 620000),
            PlayerMock(150, 8, 10000),
        ]
        players = {}

        self.game.setMaxPlayers(4)
        self.game.forced_dealer_seat = 6

        for p in players_simple:
            players[p.serial] = self.AddPlayerAndSit(p.serial, p.seat)
            players[p.serial].money = p.money
            players[p.serial].missed_blind = None
            self.game.autoBlindAnte(p.serial)

        self.game.beginTurn(1)
        self.failUnless(self.game.isFirstRound())

        self.game.callNraise(148, 800000)
        self.game.call(147)
        self.game.callNraise(150, 900000)
        self.game.call(145)

        self.game.callNraise(145,200000)
        self.game.call(147)

        self.game.callNraise(145,200000)
        self.game.callNraise(147,400000)

        self.game.callNraise(145,220000)
        self.game.fold(147)

        for (serial,player) in players.items():
            self.assertTrue(player.money>=0,"player %d has less than 0 money: %d" % (serial,player.money))

    # ---------------------------------------------------------

    def testShortStackAtBigBlind(self):

        # Include a min_bet in the betting structure
        game = self.game
        self.ModifyXMLFile(self.ConfigTempFile, '/bet/variants/round', None, {'min': str(game.bigBlind())})
        game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        game.setMaxPlayers(4)

        players_info = [
            (1, 1, 2000),
            (2, 3, 2000),
            (3, 6, 947),
            (4, 8, 2000),
        ]

        players = {}
        for (serial,seat,money) in players_info:
            players[serial] = game.addPlayer(serial, seat)
            game.payBuyIn(serial, 2000)
            game.sit(serial)
            players[serial] = self.GetPlayer(serial)
            players[serial].money = money
            game.autoBlindAnte(serial)

        game.beginTurn(1)
        self.assertEqual(players[3].bet, 947)
        game.call(4)
        self.failUnlessEqual(players[4].bet, game.bigBlind())

    def testFlushes(self):
        g = pokergame.PokerGame('poker.%s.xml', True, [path.join(TESTS_PATH, '../conf'), PokerGameTestCase.TestConfDirectory])
        g.setVariant('holdem')
        g.setBettingStructure('5-10_100-1000_no-limit')

        players = [1,2]

        for s in players:
            g.addPlayer(s, s)
            g.payBuyIn(s, g.buy_in)
            g.sit(s)

        # define a deck in which 2 players have flushes

        cards = [17, 16, 9, 8, 5, 4, 2, 1, 0]
        g.deck = g.eval.card2string(cards)
        g.shuffler = PokerPredefinedDecks([cards])

        g.beginTurn(1)
        g.bet(1, g.buy_in)
        g.bet(2, g.buy_in)

        self.failUnlessEqual(g.winners, [2])

    def testDisconnected(self):
        """Test Poker Game: Diconnected"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player are initially connected
        self.failIf(player1.remove_next_turn)
        self.failIf(player2.remove_next_turn)
        self.failUnlessEqual(self.game.disconnectedCount(), 0)
        self.failUnlessEqual(self.game.connectedCount(), 2)
        self.failUnlessEqual(self.game.serialsDisconnected(), [])
        self.failUnlessEqual(self.game.serialsConnected(), [1, 2])
        self.failUnlessEqual(self.game.playersDisconnected(), [])
        self.failUnlessEqual(self.game.playersConnected(), [player1, player2])

        # Remove the player 1
        self.failIf(self.game.removePlayer(1))
        self.failUnless(player1.remove_next_turn)

        # The player 1 is now disconnected
        self.failUnlessEqual(self.game.disconnectedCount(), 1)
        self.failUnlessEqual(self.game.connectedCount(), 1)
        self.failUnlessEqual(self.game.serialsDisconnected(), [1])
        self.failUnlessEqual(self.game.serialsConnected(), [2])
        self.failUnlessEqual(self.game.playersDisconnected(), [player1])
        self.failUnlessEqual(self.game.playersConnected(), [player2])

    # ---------------------------------------------------------
    def testReturnBlindAnte(self):
        """Test Poker Game: Return blind ante"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 1 blind
        self.game.setPlayerBlind(1, 'big')
        self.game.blind(1)
        self.failUnlessEqual(player1.bet, 1000)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 600)

        # The player 2 sit out so the game is canceled
        self.game.sitOut(2)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)

        # The game is finished, there is no winners
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)
        self.failUnlessEqual(len(self.game.winners), 0)

        # No winner, the end information are not valid
        self.failIf(self.game.isGameEndInformationValid())

    # ---------------------------------------------------------
    def testCanceled(self):
        """Test Poker Game: Canceled"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 1 blind
        self.game.autoBlindAnte(1)
        self.failUnlessEqual(player1.bet, 500)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)

        # There is more than one player sit, cancel is not available
        self.failIfEqual(self.game.sitCount(), 1)
        self.game.canceled(1, 500)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)

        # The player 2 sit out
        self.failUnless(self.game.sitOut(2))
        self.failUnlessEqual(self.game.sitCount(), 1)

        # Cancel is not available in the current state
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)
        self.game.canceled(1, 500)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)

        # Change the game round to blind and ante
        self.game.resetRound()
        self.failUnless(self.game.isBlindAnteRound())

        # The pot value does not correspond to the player bet
        self.game.pot = 100
        self.game.canceled(1, 500)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)

        # Change the game round to blind and ante
        self.game.resetRound()
        self.failUnless(self.game.isBlindAnteRound())

        # The game is explicitely canceled
        self.game.pot = 500
        self.game.canceled(1, 500)
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)

        # The game is finished, there is no winners
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)
        self.failUnlessEqual(len(self.game.winners), 0)

        # No winner, the end information are not valid
        self.failIf(self.game.isGameEndInformationValid())

    # ---------------------------------------------------------
    def testNoAutoPlayer(self):
        """Test Poker Game: No auto player"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The player 1 is an automatic player
        player1.auto = True

        # The player 1 is not an automatic player
        self.failUnless(self.game.noAutoPlayer(1))
        self.failIf(player1.auto)

        # Invalid player
        self.failIf(self.game.noAutoPlayer(3))

    # ---------------------------------------------------------
    def testAutoPlayer(self):
        """Test Poker Game: Auto player"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # The player 1 is set an automatic player
        self.game.autoPlayer(1)
        self.failUnless(player1.auto)

        # The player 1 sit out because he is not a bot
        self.game.interactivePlayer(1)
        self.game.autoPlayer(1)

        # The blind is automatically payed because the player 2 is a bot
        self.game.botPlayer(2)
        self.game.autoPlayer(2)
        self.failUnlessEqual(player2.blind, True)

        # Client game
        self.game.is_directing = False

        # AutoPlayer has no effect
        self.game.botPlayer(3)
        self.game.autoPlayer(3)
        self.failIfEqual(player3.blind, True)

    # ---------------------------------------------------------
    def testPlayersPlaying(self):
        """Test Poker Game: Players playing"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The game is not running so there is no playing players
        self.failUnlessEqual(self.game.playingCount(), 0)
        self.failUnlessEqual(self.game.serialsPlaying(), [])
        self.failUnlessEqual(self.game.playersPlaying(), [])
        self.failUnlessEqual(self.game.notPlayingCount(), 2)
        self.failUnlessEqual(self.game.serialsNotPlaying(), [1, 2])
        self.failUnlessEqual(self.game.playersNotPlaying(), [player1, player2])

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # All the players are now playing
        self.failUnlessEqual(self.game.playingCount(), 2)
        self.failUnlessEqual(self.game.serialsPlaying(), [1, 2])
        self.failUnlessEqual(self.game.playersPlaying(), [player1, player2])
        self.failUnlessEqual(self.game.notPlayingCount(), 0)
        self.failUnlessEqual(self.game.serialsNotPlaying(), [])
        self.failUnlessEqual(self.game.playersNotPlaying(), [])

    # ---------------------------------------------------------
    def testMuckStateSitOut(self):
        """Test Poker Game: Muck state sit out"""
        player1 = self.AddPlayerAndSit(1, 2)
        self.game.state = pokergame.GAME_STATE_MUCK
        self.game.player_list = [ 1 ]
        self.failIf(self.game.sitOutNextTurn(1))
        self.failUnlessEqual(True, self.game.getPlayer(1).sit_out_next_turn)

    # ---------------------------------------------------------
    def testMuckStateWonFold(self):
        """Test Poker Game: Muck state won fold"""

        self.game.setVariant('holdem')

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # Buy in amount
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1600)

        # The players raise
        self.failUnless(self.game.callNraise(1, 100))
        self.failUnless(self.game.callNraise(2, 200))

        self.failUnlessEqual(player1.bet, 100)
        self.failUnlessEqual(player2.bet, 200)

        # The player 1 fold
        self.failUnless(self.game.fold(1))

        # The winner is the player 2
        self.failUnlessEqual(self.game.winners, [2])
        self.failUnlessEqual(self.game.playersWinner(), [player2])
        self.failUnless(self.game.isWinnerBecauseFold())

        # Money amounts after
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1500)
        rake = self.game.getRakedAmount()
        self.failUnlessEqual(10, rake)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1700 - rake)

    # ---------------------------------------------------------
    def testMuckStateWonAllIn(self):
        """Test Poker Game: Muck state won all in"""

        self.game.setVariant('holdem')

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # Buy in amount
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1600)

        # The players raise
        self.failUnless(self.game.callNraise(1, 100))
        self.failUnless(self.game.callNraise(2, 1600))

        self.failUnless(player1.bet, 100)
        self.failUnless(player2.bet, 1600)

        # The player 2 is all in
        self.failUnlessEqual(self.game.getPlayerMoney(2), 0)
        self.failUnless(player2.isAllIn())

        # The player 1 is also all in
        self.failUnless(self.game.callNraise(1, self.game.getPlayerMoney(1)))
        self.failUnless(player1.isAllIn())

        # All the players are now all in
        # All the cards must be dealt
        # Each player has 2 cards, and there are 5 cards in the board
        hand1 = pokercards.PokerCards(['8s', 'As'])
        hand2 = pokercards.PokerCards(['3h', '6d'])
        board = pokercards.PokerCards(['4s', 'Qs', '6s', '6h', 'Ah'])

        self.failUnlessEqual(player1.hand, hand1)
        self.failUnlessEqual(player2.hand, hand2)
        self.failUnlessEqual(self.game.board, board)

        # The player 1 wins with a flush
        self.failUnlessEqual(self.game.winners, [1])
        self.failUnlessEqual(self.game.playersWinner(), [player1])

        # Money amounts after
        self.failUnlessEqual(self.game.getPotAmount(), 3200)
        self.failUnlessEqual(self.game.getRakedAmount(), 160)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 3040)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 0)

    def testMuckStateWonRegular(self):
        """Test Poker Game: Muck state won regular"""

        self.game.setVariant('holdem')

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Deal cards
        self.game.dealCards()

        # Buy in amount
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1600)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1600)

        # Round 1
        self.failUnless(self.game.callNraise(1, 100))
        self.failUnless(self.game.callNraise(2, 200))
        self.failUnless(self.game.call(1))

        # Round 2
        self.failUnless(self.game.callNraise(2, 100))
        self.failUnless(self.game.call(1))

        # Round 3
        self.failUnless(self.game.callNraise(2, 100))
        self.failUnless(self.game.callNraise(1, 300))
        self.failUnless(self.game.call(2))

        # Round 4
        self.failUnless(self.game.isLastRound())
        self.failUnless(self.game.check(2))
        self.failUnless(self.game.check(1))

        # The turn is finished
        # Each player has 2 cards, and there is 5 cards in the board
        hand1 = pokercards.PokerCards(['8s', 'As'])
        hand2 = pokercards.PokerCards(['3h', '6d'])
        board = pokercards.PokerCards(['4s', 'Qs', '6s', '6h', 'Ah'])

        self.failUnlessEqual(player1.hand, hand1)
        self.failUnlessEqual(player2.hand, hand2)
        self.failUnlessEqual(self.game.board, board)

        # The player 1 wins with a flush
        self.failUnlessEqual(self.game.winners, [1])
        self.failUnlessEqual(self.game.playersWinner(), [player1])

        # Money amounts after
        self.failUnlessEqual(self.game.getPotAmount(), 1200)
        self.failUnlessEqual(self.game.getRakedAmount(), 60)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 2140) # 2200 - 60
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1000)

        # The money has been already distributed
        self.failUnless(self.game.moneyDistributed())

        # The distribution has no effect
        self.game.distributeMoney()

        # Money amounts after
        self.failUnlessEqual(self.game.getPlayerMoney(1), 2140)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1000)

    # ---------------------------------------------------------
    def testHighLowWinners(self):
        """Test Poker Game: high low winners"""

        # Modify wins properties
        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/wins', None, { 'ways': '2'}):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        winner_properties = {'id': '2', 'type': 'hand', 'order': 'low8'}

        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/wins', 'winner', winner_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)
        self.game.variant = 'holdem8'

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # High low game
        self.failUnless(self.game.isHighLow())

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Auto pay blind
        for serial in self.game.serialsAll():
            self.game.autoBlindAnte(serial)

        # Deal all the cards
        while not self.game.isLastRound():
            self.game.nextRound()
            self.game.dealCards()

        # Check players money and bet
        self.failUnlessEqual(player1.bet, 0)
        self.failUnlessEqual(player2.bet, 500)
        self.failUnlessEqual(player3.bet, 1000)

        self.failUnlessEqual(player1.money, 1600)
        self.failUnlessEqual(player2.money, 1100)
        self.failUnlessEqual(player3.money, 600)

        self.game.initRound()

        self.failUnless(self.game.callNraise(2,501))
        self.failUnless(self.game.call(3))
        self.failUnless(self.game.call(1))

        # 2 winners
        self.failUnlessEqual(self.game.winners, [2, 3])

        # Check money distribution
        self.failUnlessEqual(self.game.getRakedAmount(), 150)
        self.failUnlessEqual(player1.money, 599)
        #
        # Each player gives his share to the rake, i.e. 150/2
        #
        self.failUnlessEqual(player2.money, 2026) # 2101 - (150/2)
        self.failUnlessEqual(player3.money, 2025) # 2100 - (150/2)

    # ---------------------------------------------------------
    def testRemovePlayer(self):
        """Test Poker Game: Remove player"""

        # The number max of player is 2 so there are 2 seats left
        self.failUnlessEqual(self.game.seatsLeftCount(), 2)
        self.failUnlessEqual(self.game.seats_left, [2, 7])

        # Add a new player on the seat 7
        player1 = self.AddPlayerAndSit(1, 7)
        self.failUnlessEqual(player1.seat, 7)

        # 1 seat is still left
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)
        self.failUnlessEqual(self.game.seats_left, [2])

        # Remove the player
        self.failUnless(self.game.removePlayer(1))

        # The Player has been delete
        self.failUnlessEqual(self.game.getPlayer(1), None)

        # The player seat is now left
        self.failUnlessEqual(self.game.seatsLeftCount(), 2)
        self.failUnlessEqual(self.game.seats_left, [2, 7])

        # Add two players on the same seat
        player1 = self.AddPlayerAndSit(1)
        player2 = self.AddPlayerAndSit(2)
        player2.seat = player1.seat
        self.failUnlessEqual(self.game.seatsLeftCount(), 0)

        # Remove the player
        self.failUnless(self.game.removePlayer(1))
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

        # Remove the second player
        self.failUnless(self.game.removePlayer(2))

        # The number of seat left is still the same
        self.failUnlessEqual(self.game.seatsLeftCount(), 1)

    # ---------------------------------------------------------
    def testCardsDealtThisRoundCount(self):
        """Test Poker Game: Card dealt this round"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The game is not running
        self.failUnlessEqual(self.game.cardsDealtThisRoundCount(), -1)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.failUnlessEqual(self.game.cardsDealtThisRoundCount(), 0)

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # First round 2 cards down
        round_info = self.game.roundInfo()
        self.failUnlessEqual(round_info["cards"], ['down', 'down'])
        self.failUnlessEqual(self.game.cardsDealtThisRoundCount(), 2)
        self.failUnlessEqual(self.game.downCardsDealtThisRoundCount(), 2)
        self.failUnlessEqual(self.game.upCardsDealtThisRoundCount(), 0)

        # Set a card to up
        round_info["cards"] = ['down', 'up']
        self.failUnlessEqual(self.game.downCardsDealtThisRoundCount(), 1)
        self.failUnlessEqual(self.game.upCardsDealtThisRoundCount(), 1)

    # ---------------------------------------------------------
    def testUpdateStats(self):
        """Test Poker Game: Update stats"""

        self.game.setMaxPlayers(3)

        # Initial pots
        pots = {
            'contributions': { 'total': {} },
            'pots': [[0, 0]],
            'last_round': -1,
            'building': 0,
        }

        # Initial stats
        stats = {
            'flops': [],
            'flops_count': 20,
            'percent_flop': 0,
            'pots': [],
            'pots_count': 20,
            'average_pot': 0,
            'hands_per_hour': 0,
            'time': -1,
            'hands_count': 0,
            'frequency': 180 # seconds
        }

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Check stats
        for attribute, value in stats.items():
            self.failUnlessEqual(self.game.stats[attribute], value)

        # Update stats flop
        self.game.updateStatsFlop(True)

        # Check stats
        self.failUnlessEqual(self.game.stats['flops'], [0])
        self.failUnlessEqual(self.game.stats['percent_flop'], 0)

        # Init stats
        self.game.stats = stats.copy()

        # Update stats
        self.game.updateStatsFlop(False)

        # Check stats
        self.failUnlessEqual(self.game.stats['flops'], [100])
        self.failUnlessEqual(self.game.stats['percent_flop'], 100)

        # Update stats end turn
        self.failUnlessEqual(self.game.stats['time'], -1)
        self.game.updateStatsEndTurn()
        self.failIfEqual(self.game.stats['time'], -1)
        self.failUnlessEqual(self.game.stats['hands_count'], 0)

        # Set the frequency to 1 hour
        self.game.stats['frequency'] = 3600

        # Modification fo the time
        self.game.setTime(4000)

        # Modification of the pots
        self.game.side_pots['pots'] = [[500, 300]]

        # Modification of the hand count
        self.game.hands_count = 1

        # Update stats end turn
        self.game.updateStatsEndTurn()

        # Check stats
        self.failUnlessEqual(self.game.stats['average_pot'], 300)
        self.failUnlessEqual(self.game.stats['hands_per_hour'], 1)
        self.failUnlessEqual(self.game.stats['hands_count'], 1)

    # ---------------------------------------------------------
    def testSidePots(self):
        """Test Poker Game: Side pots"""

        # Initial pots
        pots = {
            'contributions': { 'total': {} },
            'pots': [[0, 0]],
            'last_round': -1,
            'building': 0,
        }

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # The side pots is initally empty
        self.failUnlessEqual(self.game.getPots(), {})

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failUnlessEqual(self.game.playersInPotCount(self.game.getPots()), 0)
        self.failIf(self.game.isSingleUncalledBet(self.game.getPots()))

        # The blind contribution has been added to the pots
        current_round = self.game.current_round
        pots['contributions'][current_round] = {}
        self.failUnlessEqual(self.game.getPots(), pots)

        # The player 1 pay the blind
        self.game.autoBlindAnte(1)
        self.failUnlessEqual(player1.bet, 500)
        self.failUnlessEqual(self.game.playersInPotCount(self.game.getPots()), 1)
        self.failUnless(self.game.isSingleUncalledBet(self.game.getPots()))

        # The pots has been updated
        pots['building'] += 500
        pots['contributions']['total'][1] = 500
        pots['contributions'][current_round][len(pots['pots']) -1] = {}
        pots['contributions'][current_round][len(pots['pots']) -1][1] = 500
        self.failUnlessEqual(self.game.getPots(), pots)

        # The player 2 pay also the blind
        self.game.autoBlindAnte(2)
        self.failUnlessEqual(player2.bet, 1000)
        self.failUnlessEqual(self.game.playersInPotCount(self.game.getPots()), 2)
        self.failIf(self.game.isSingleUncalledBet(self.game.getPots()))

        # First round
        self.failUnless(self.game.isFirstRound())

        # The pots has been updated
        pots['building'] += 1000
        pots['contributions']['total'][2] = 1000

        # The blind turn will be finished so its contribution infos will be copy in the first round infos and deleted
        pots['contributions'][current_round][len(pots['pots']) -1][2] = 1000
        pots['contributions'][current_round + 1] = pots['contributions'][-1]
        del pots['contributions'][current_round]
        pots['last_round'] = 0
        current_round += 1

        # Check pots
        self.failUnlessEqual(self.game.getPots(), pots)

        # The player 1 raises and is allin
        self.failUnless(self.game.callNraise(1, 700))
        self.failUnlessEqual(player1.bet, 1200)

        # The pots has been updated
        pots['building'] += 700
        pots['contributions']['total'][1] += 700
        pots['contributions'][current_round][len(pots['pots']) -1][1] += 700
        self.failUnlessEqual(self.game.getPots(), pots)
        self.failUnlessEqual(self.game.getLatestPotContributions(), {0: {1: 1200, 2: 1000}})

        # The player 2 call
        self.failUnless(self.game.call(2))

        # Second round
        self.failUnless(self.game.isSecondRound())
        self.failUnlessEqual(self.game.playersInPotCount(self.game.getPots()), 0)

        # The round is finished, the post has been updated
        pots['building'] = 0
        pots['pots'][0] = [1200 + 1200, 1200 + 1200]
        pots['contributions']['total'][2] += 200
        pots['contributions'][current_round][len(pots['pots']) -1][2] += 200

        current_round += 1
        pots['last_round'] = 1
        pots['contributions'][current_round] = {}

        # Check pots
        self.failUnlessEqual(self.game.getPots(), pots)
        self.failUnlessEqual(self.game.getSidePotTotal(), 2400)

        # The player 2 raise 100
        self.failUnless(self.game.callNraise(2, 100))
        self.failUnlessEqual(self.game.getLatestPotContributions(), {0: {2: 100}})

        # The player 1 call
        self.failUnless(self.game.call(1))

        # Round 3
        self.failUnlessEqual(self.game.current_round, 2)
        self.failUnlessEqual(self.game.playersInPotCount(self.game.getPots()), 0)

        # The pots has been updated
        pots['last_round'] = 2
        pots['pots'][0] = [1200 + 1200 + 100 + 100, 1200 + 1200 + 100 + 100]
        pots['contributions']['total'][1] += 100
        pots['contributions']['total'][2] += 100
        pots['contributions'][current_round][len(pots['pots']) -1] = {}
        pots['contributions'][current_round][len(pots['pots']) -1][1] = 100
        pots['contributions'][current_round][len(pots['pots']) -1][2] = 100

        current_round += 1
        pots['contributions'][current_round] = {}

        # Check pots
        self.failUnlessEqual(self.game.getPots(), pots)
        self.failUnlessEqual(self.game.getSidePotTotal(), 2600)
        self.failUnlessEqual(self.game.playersInPotCount(self.game.getPots()), 0)


    # ---------------------------------------------------------
    def testEndTurn(self):
        """Test Poker Game: End turn"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Pay the blind
        self.game.autoBlindAnte(1)
        self.game.autoBlindAnte(2)

        # Check the players money and bet
        self.failUnlessEqual(player1.bet, 500)
        self.failUnlessEqual(player2.bet, 1000)
        self.failUnlessEqual(self.game.getPlayerMoney(1), 1100)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 600)

        # Set a rebuy amount for each player
        self.failIf(self.game.rebuy(1, 400))
        self.failIf(self.game.rebuy(2, 600))


        # The rebuy is credited to the player
        wascalled = {"p1": False, "p2": False}
        def P1rebuy400(game_id,game_type,*args):
            if game_type == "end":
                self.assertEqual(self.game.id, game_id)
                self.failUnless(self.game.rebuy(1, 400))
                wascalled["p1"] = True

        def P2rebuy600(game_id,game_type,*args):
            if game_type == "end":
                self.assertEqual(self.game.id, game_id)
                self.failUnless(self.game.rebuy(2, 600))
                wascalled["p2"] = True

        self.game.state = pokergame.GAME_STATE_MUCK
        self.game.registerCallback(P1rebuy400)
        self.game.registerCallback(P2rebuy600)
        self.game.endState()
        self.assertTrue(wascalled["p1"])
        self.assertTrue(wascalled["p2"])
        self.game.unregisterCallback(P1rebuy400)
        self.game.unregisterCallback(P2rebuy600)

        self.failUnlessEqual(self.game.getPlayerMoney(1), 1500)
        self.failUnlessEqual(self.game.getPlayerMoney(2), 1200)

        # The hand count is incremented
        self.failUnlessEqual(self.game.hands_count, 1)

        # self.game.sit(1)
        # self.game.sit(2)

        self.game.beginTurn(2)



        # The player 1 is broke
        player1.money = 0
        self.failUnless(self.game.isBroke(1))

        # Remove the player 2
        self.game.removePlayer(2)
        # This fails because of the Error #8737
        self.failUnless(player2.remove_next_turn)

        # Make the player remove needed
        self.game.endTurn()

        # The player 1 sit out
        self.failIfEqual(self.game.getPlayer(1), None)
        self.failUnless(self.game.getSitOut(1))

        # The player 2 has been removed
        self.failUnlessEqual(len(self.game.seats_left), 1)
        self.failUnlessEqual(self.game.allCount(), 1)
        self.failUnlessEqual(self.game.getPlayer(2), None)

    # ---------------------------------------------------------
    def testBeginTurn(self):
        """Test Poker Game: Begin turn"""

        hand_serial = 1

        # Create player 1
        player1 = self.AddPlayerAndSit(1, 2)

        # There is not enough player to start
        self.failIf(self.game.buildPlayerList(True))
        self.game.beginTurn(hand_serial)
        self.failUnlessEqual(self.game.player_list, [])
        self.failUnlessEqual(self.game.current_round, -2)

        # Create player 2
        player2 = self.AddPlayerAndSit(2, 7)

        # Warning the muckable list is not empty
        self.game.setMuckableSerials([1])

        # Begin turn
        self.game.beginTurn(hand_serial)

        # The muckable serials have been reset
        self.game.setMuckableSerials([])

        # Init player infos
        player_infos = {
            'bet': 0,
            'dead': 0,
            'fold': False,
            'hand': pokercards.PokerCards(),
            'side_pot_index': 0,
            'all_in': False,
            'ante': False
        }

        # Init side pots infos
        side_pots_infos ={
            'contributions': { 'total': {} },
            'pots': [[0, 0]],
            'last_round': -1,
            'building': 0,
        }

        # Current round initialisation
        side_pots_infos['contributions'][self.game.current_round] = {}

        # Init game infos
        game_infos = {
            'hand_serial': hand_serial,
            'pot': 0,
            'board': pokercards.PokerCards(),
            'winners': [],
            'muckable_serials': [],
            'win_condition': pokergame.WON_NULL,
            'serial2best': {},
            'showdown_stack': [],
            'side_pots': side_pots_infos
        }

        # Check game initialisation
        for attribute, value in game_infos.items():
            self.failUnlessEqual(getattr(self.game, attribute), value)

        # Check players initialisation
        for player in (player1, player2):
            for attribute, value in player_infos.items():
                self.failUnlessEqual(getattr(player, attribute), value)

        # Check history, first event of type game
        self.failIfEqual(len(self.game.historyGet()), 0)
        self.failUnlessEqual(self.game.historyGet()[0][0], 'game')

        # Check player list
        self.failUnlessEqual(self.game.player_list, [1, 2])

        # Blind and ante turn
        self.failUnless(self.game.isBlindAnteRound())

        # Call again begin turn has no effect
        self.game.beginTurn(3)
        self.failIfEqual(self.game.hand_serial, 3)

    # ---------------------------------------------------------
    def testInitRound(self):
        """Test Poker Game: Init round"""

        round_infos = {
            0: {
                'name': 'pre-flop',
                'position': 'under-the-gun'
            },
            1: {
                'name': 'flop',
                'position': 'next-to-dealer'
            },
            2: {
                'name': 'turn',
                'position': 'high'
            },
            3: {
                'name': 'river',
                'position': 'invalid'
            }
        }

        # Change the round turn properties
        round_turn_properties = {'type': 'high'}

        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/round[@name="turn"]/position', None, round_turn_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Change the round river properties
        round_river_properties = {'type': 'invalid'}

        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/round[@name="river"]/position', None, round_river_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the variant structure
        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Check the round infos
        round_info = self.game.roundInfo()
        self.failUnlessEqual(round_info['name'], round_infos[self.game.current_round]['name'])
        self.failUnlessEqual(round_info['position'], round_infos[self.game.current_round]['position'])

        # Check game init
        self.failUnlessEqual(self.game.last_bet, 0)
        self.failUnless(self.game.first_betting_pass)
        self.failUnlessEqual(self.game.getSerialInPosition(), 1)
        self.failUnlessEqual(self.game.getPlayerLastToTalk(), player2)

        # Check players init
        for player in (player1, player2):
            self.failIf(player.talked_once)

        # Second round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isSecondRound())

        # Check the round infos
        round_info = self.game.roundInfo()
        self.failUnlessEqual(round_info['name'], round_infos[self.game.current_round]['name'])
        self.failUnlessEqual(round_info['position'], round_infos[self.game.current_round]['position'])
        self.failUnlessEqual(self.game.getSerialInPosition(), 2)
        self.failUnlessEqual(self.game.getPlayerLastToTalk(), player1)

        # Round 3
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.current_round, 2)

        # Check the round infos
        round_info = self.game.roundInfo()
        self.failUnlessEqual(round_info['name'], round_infos[self.game.current_round]['name'])
        self.failUnlessEqual(round_info['position'], round_infos[self.game.current_round]['position'])
        self.failUnlessEqual(self.game.getSerialInPosition(), 1)
        self.failUnlessEqual(self.game.getPlayerLastToTalk(), player2)

        # Round 4
        self.game.nextRound()
        self.failUnlessRaises(UserWarning,self.game.initRound)

    # ---------------------------------------------------------
    def testInitRoundClientGame(self):
        """Test Poker Game: Init round client game"""

        # Create a client game
        self.CreateGameClient()
        self.InitGame()

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        round_infos = {
            0: {
                'name': 'pre-flop',
                'position': 'under-the-gun'
            },
            1: {
                'name': 'flop',
                'position': 'low'
            },
            2: {
                'name': 'turn',
                'position': 'under-the-gun'
            }
        }

        # Change the round flop properties
        round_flop_properties = { 'type': 'low' }

        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/round[@name="flop"]/position', None, round_flop_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Change the round turn properties
        round_flop_properties = { 'type': 'under-the-gun' }

        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/round[@name="turn"]/position', None, round_flop_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the variant structure
        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failUnlessEqual(self.game.player_list, [1, 2, 3])

        # Player 2 is waiting big blind
        player2.wait_for = 'big'

        # First round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isFirstRound())

        # Check the round infos
        round_info = self.game.roundInfo()
        self.failUnlessEqual(round_info['name'], round_infos[self.game.current_round]['name'])
        self.failUnlessEqual(round_info['position'], round_infos[self.game.current_round]['position'])
        self.failUnlessEqual(self.game.player_list, [1, 3])

        # Check game init
        self.failUnlessEqual(self.game.last_bet, 0)
        self.failUnless(self.game.first_betting_pass)
        self.failUnlessEqual(self.game.getSerialInPosition(), 3)
        self.failUnlessEqual(self.game.getPlayerLastToTalk(), player1)

        # Check players init
        for player in (player1, player2):
            self.failIf(player.talked_once)

        # Second round
        self.game.nextRound()
        self.game.initRound()
        self.failUnless(self.game.isSecondRound())

        # Check the round infos
        round_info = self.game.roundInfo()
        self.failUnlessEqual(round_info['name'], round_infos[self.game.current_round]['name'])
        self.failUnlessEqual(round_info['position'], round_infos[self.game.current_round]['position'])
        self.failUnlessEqual(self.game.getSerialInPosition(), 1)
        self.failUnlessEqual(self.game.getPlayerLastToTalk(), player3)

        # The player 1 and 2 are fold
        player1.fold = True
        player2.fold = True
        self.failIf(player1.isInGame())
        self.failIf(player2.isInGame())

        # Next round
        self.game.nextRound()

        # Not enough player in game to init the round
        self.failUnless(self.game.inGameCount, 1)
        self.failUnlessRaises(UserWarning, self.game.initRound)

    # ---------------------------------------------------------
    def testInitRoundBlindAllIn(self):
        """Test Poker Game: Init round blinds are all-in"""

        # Create a client game
        self.CreateGameClient()
        self.InitGame()

        self.game.setMaxPlayers(4)

        # Create players
        player1 = self.AddPlayerAndSit(1, 1)
        player2 = self.AddPlayerAndSit(2, 3)
        player3 = self.AddPlayerAndSit(3, 6)
        player4 = self.AddPlayerAndSit(4, 8)

        # Change the round flop properties
        round_flop_properties = { 'type': 'low' }

        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant/round[@name="flop"]/position', None, round_flop_properties):
            self.fail('Error during modification of configuration file ' + self.ConfigTempFile)

        # Reload the variant structure
        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())
        self.failUnlessEqual(self.game.player_list, [1, 2, 3, 4])

        # Player 2 & 4 are all_in
        player2.all_in = True
        player4.all_in = True
        self.failUnless("small", player2.blind)
        self.failUnless("big", player3.blind)

        # First round
        self.game.nextRound()
        self.game.initRound()
        #
        #         idx
        # players: 0 | 1 dealer        -        first to talk
        #          1 | 2 small blind   all in
        #          2 | 3 big blind     -        last to talk
        #          3 | 4               all in
        #
        self.assertEqual(0, self.game.position)
        self.assertEqual(2, self.game.last_to_talk)

    # ---------------------------------------------------------
    def testMuck(self):
        """Test Poker Game: Muck"""

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Init the muckable serials
        self.game.setMuckableSerials([10,20])
        self.failUnlessEqual(self.game.muckable_serials, [10,20])

        # Init the muckable serials
        self.game.setMuckableSerials((1,2))
        self.failUnlessEqual(list, type(self.game.muckable_serials));
        self.failUnlessEqual(self.game.muckable_serials, [1,2])

        # Muck not available
        self.game.muck(1, True)
        self.failUnlessEqual(self.game.muckable_serials, [1,2])

        # Muck state
        self.game.changeState(pokergame.GAME_STATE_MUCK)
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_MUCK)

        # Player 1 muck
        self.game.muck(1, False)
        self.failUnlessEqual(self.game.muckable_serials, [2])
        self.failUnless(player1.hand.areVisible())

        # The muck serial list is not empty
        # The state is still MUCK STATE
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_MUCK)

        # Unknown player, muck has no effect
        self.game.muck(3, True)
        self.failUnlessEqual(self.game.muckable_serials, [2])

        # Client game
        self.game.is_directing = False

        # Muck state has no effect
        self.game.muckState(pokergame.WON_NULL)

        # Muck has no effect
        self.game.muck(2, False)
        self.failUnlessEqual(self.game.muckable_serials, [2])
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_MUCK)
        self.game.is_directing = True

        # Player 2 muck
        self.game.muck(2, False)
        self.failUnlessEqual(self.game.muckable_serials, [])
        self.failUnless(player2.hand.areVisible())

        # The game is finished
        self.failUnlessEqual(self.game.state, pokergame.GAME_STATE_END)

    # ---------------------------------------------------------
    def testGetMaxBoardSize(self):
        """Test Poker Game: Get max board size"""

        # The max board size is initially set to 5
        self.failUnlessEqual(self.game.getMaxBoardSize(), 5)

        # Change the variant type
        if not self.ModifyXMLFile(self.VariantTempFile, '/poker/variant', None, {'type': 'NotCommunity'}):
            self.fail('Error during modification of variant file ' + self.VariantTempFile)

        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)

        # Not a community variant, max board size set 0
        self.failUnlessEqual(self.game.getMaxBoardSize(), 0)

    # ---------------------------------------------------------
    def testGetParamList(self):
        """Test Poker Game: Get param list"""

        self.failUnlessEqual(len(self.game.getParamList('/bet/variants/round')), 4)
        self.failUnlessEqual(len(self.game.getParamList('/poker/variant/community/position')), 5)

    # ---------------------------------------------------------
    def testGetParam(self):
        """Test Poker Game: Get param"""

        self.failUnlessEqual(self.game.getParam('/bet/@buy-in'), '50')
        self.failUnlessEqual(self.game.getParam('/poker/variant/@type'), 'community')

    # ---------------------------------------------------------
    def testGetParamProperties(self):
        """Test Poker Game: Get param properties"""

        bet_properties = {
            'buy-in': '50',
            'max-buy-in': '10000',
            'best-buy-in': '1600',
            'unit': '300'
        }

        properties = self.game.getParamProperties('/bet')[0]
        for attribute, value in bet_properties.items():
            self.failUnlessEqual(properties[attribute], value)

        variant_properties = {
            'type': 'community',
            'name': 'VariantName',
            'id': 'VariantTest'
        }

        properties = self.game.getParamProperties('/poker/variant')[0]
        for attribute, value in variant_properties.items():
            self.failUnlessEqual(properties[attribute], value)

    # ---------------------------------------------------------
    def testIsGameEndInformationValid(self):
        """Test Poker Game: Is game end information are valid"""

        # The game state is not GAME_STATE_END
        self.failIfEqual(self.game.state,pokergame.GAME_STATE_END)
        self.failIf(self.game.isGameEndInformationValid())

        # Change the game state
        self.game.changeState(pokergame.GAME_STATE_END)
        self.failUnlessEqual(self.game.state,pokergame.GAME_STATE_END)

        # there is no winner
        self.failUnlessEqual(len(self.game.winners),0)
        self.failIf(self.game.isGameEndInformationValid())

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 7)

        # Set the winners
        self.game.winners = [1]

        # The end information are valid
        self.failUnless(self.game.isGameEndInformationValid())

        # Remove the winner from the player list
        del self.game.serial2player[1]

        # The end information are now invalid
        self.failIf(self.game.isGameEndInformationValid())

    # ---------------------------------------------------------
    def testDispatchMuck(self):
        """Test Poker Game: Dispatch Muck"""

        self.game.setVariant('holdem')

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Deal all the cards
        while not self.game.isLastRound():
            self.game.nextRound()
            self.game.dealCards()

        # Init winners
        self.game.setWinners([1])

        # Init winners per side
        self.game.side2winners = { 'hi': [], 'low': [] }

        # Winner because fold
        self.game.win_condition = pokergame.WON_FOLD
        self.failUnlessEqual(self.game.dispatchMuck(), ((), (1,)))
        self.game.win_condition = pokergame.WON_REGULAR

        # Dealer is the player 2
        self.failUnlessEqual(self.game.dealer, 0)

        # The player 2 and 3 muck, the winner show his cards
        self.failUnlessEqual(self.game.dispatchMuck(), ((1,), (2,3)))

        # Init winners per side
        self.game.side2winners = { 'hi': [2], 'low': [] }

        # The player 2 show also his cards
        self.failUnlessEqual(self.game.dispatchMuck(), ((2, 3, 1), ()))

        # Init winners per side
        self.game.side2winners = { 'hi': [], 'low': [3] }

        # All the player show their cards
        self.failUnlessEqual(self.game.dispatchMuck(), ((2,1), (3,)))

        # Client game
        self.game.is_directing = False
        self.failUnlessEqual(self.game.dispatchMuck(), None)

    # ---------------------------------------------------------
    def testAutoMuckNever(self):
        """Test Poker Game: Auto muck never"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Auto pay blind
        for serial in self.game.serialsAll():
            self.game.autoBlindAnte(serial)

        # Set auto muck state
        self.game.autoMuck(1, pokergame.AUTO_MUCK_NEVER)
        self.game.autoMuck(2, pokergame.AUTO_MUCK_NEVER)
        self.game.autoMuck(3, pokergame.AUTO_MUCK_NEVER)

        # Players 1 and 2 fold
        self.failUnless(self.game.fold(1))
        self.failUnless(self.game.fold(2))

        # Player 3 is the winner and muckable
        self.failUnlessEqual(self.game.winners, [3])
        self.failUnlessEqual(self.game.muckable_serials, [3])

    # ---------------------------------------------------------
    def testAutoMuckAlways(self):
        """Test Poker Game: Auto muck always"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Auto pay blind
        for serial in self.game.serialsAll():
            self.game.autoBlindAnte(serial)

        # Set auto muck state
        self.game.autoMuck(1, pokergame.AUTO_MUCK_ALWAYS)
        self.game.autoMuck(2, pokergame.AUTO_MUCK_ALWAYS)
        self.game.autoMuck(3, pokergame.AUTO_MUCK_ALWAYS)

        # Players 1 and 2 fold
        self.failUnless(self.game.fold(1))
        self.failUnless(self.game.fold(2))

        # No muckable players
        self.failUnlessEqual(self.game.winners, [3])
        self.failUnlessEqual(self.game.muckable_serials, [])

    # ---------------------------------------------------------
    def testAutoMuckWin(self):
        """Test Poker Game: Auto muck win"""

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Auto pay blind
        for serial in self.game.serialsAll():
            self.game.autoBlindAnte(serial)

        # Set auto muck state
        self.game.autoMuck(1, pokergame.AUTO_MUCK_WIN)
        self.game.autoMuck(2, pokergame.AUTO_MUCK_WIN)
        self.game.autoMuck(3, pokergame.AUTO_MUCK_WIN)

        # Players 1 and 2 fold
        self.failUnless(self.game.fold(1))
        self.failUnless(self.game.fold(2))

        # Player 3 is the winner but not muckable
        self.failUnless(self.game.isWinnerBecauseFold())
        self.failUnlessEqual(self.game.winners, [3])
        self.failUnlessEqual(self.game.muckable_serials, [])

    # ---------------------------------------------------------
    def testAutoMuckLose(self):
        """Test Poker Game: Auto muck lose"""

        self.game.variant = 'holdem'

        self.game.setMaxPlayers(3)

        # Create players
        player1 = self.AddPlayerAndSit(1, 2)
        player2 = self.AddPlayerAndSit(2, 5)
        player3 = self.AddPlayerAndSit(3, 7)

        # Blind and ante turn
        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        # Auto pay blind
        for serial in self.game.serialsAll():
            self.game.autoBlindAnte(serial)

        # Set auto muck state
        self.game.autoMuck(1, pokergame.AUTO_MUCK_LOSE)
        self.game.autoMuck(2, pokergame.AUTO_MUCK_LOSE)
        self.game.autoMuck(3, pokergame.AUTO_MUCK_LOSE)

        # Deal all the cards
        while not self.game.isLastRound():
            self.game.nextRound()
            self.game.dealCards()

        self.game.initRound()

        self.failUnless(self.game.callNraise(2,100))
        self.failUnless(self.game.call(3))
        self.failUnless(self.game.call(1))

        # Player 3 is the winner but not muckable
        self.failIf(self.game.isWinnerBecauseFold())
        self.failUnlessEqual(self.game.winners, [3])
        self.failUnlessEqual(self.game.muckable_serials, [])

    # ---------------------------------------------------------
    def testUpdateBlinds(self):
        """Test Poker Game: Update blinds"""

        self.game.setMaxPlayers(4)

        # Create 1 player
        player1 = self.AddPlayerAndSit(1, 1)

        # Not enough player sit
        # The wait_for attribute is reset if not equal to first round
        player1.wait_for = 'first_round'
        self.game.updateBlinds()
        self.failUnlessEqual(player1.wait_for, 'first_round')

        player1.wait_for = 'big'
        self.game.updateBlinds()
        self.failUnlessEqual(player1.wait_for, False)

        # Create players
        player2 = self.AddPlayerAndSit(2, 3)
        player3 = self.AddPlayerAndSit(3, 6)
        player4 = self.AddPlayerAndSit(4, 8)

        # Init players infos
        self.game.playersBeginTurn()

        # Update blinds
        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': 'small', 'missed_blind': None, 'wait_for': False},
            3: { 'blind': 'big', 'missed_blind': None, 'wait_for': False},
            4: { 'blind': False, 'missed_blind': None, 'wait_for': False}
        }

        self.game.updateBlinds()

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

        # Move the dealer
        self.game.moveDealerLeft()

        # Update blinds
        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            3: { 'blind': 'small', 'missed_blind': None, 'wait_for': False},
            4: { 'blind': 'big', 'missed_blind': None, 'wait_for': False}
        }

        self.game.updateBlinds()

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

        # Move the dealer
        self.game.moveDealerLeft()

        # Update blinds
        blinds = {
            1: { 'blind': 'big', 'missed_blind': None, 'wait_for': False},
            2: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            3: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            4: { 'blind': 'small', 'missed_blind': None, 'wait_for': False}
        }

        self.game.updateBlinds()

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

        # Forbid missed blinds
        player1.missed_blind = 'small'
        player1.wait_for = 'late'

        player2.missed_blind = 'small'
        player3.missed_blind = 'small'

        self.game.updateBlinds()

        blinds = {
            1: { 'blind': 'big', 'missed_blind': None, 'wait_for': False},
            2: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            3: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            4: { 'blind': 'small', 'missed_blind': None, 'wait_for': False}
        }

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

    # ---------------------------------------------------------
    def testUpdateSmallBlinds(self):
        """Test Poker Game: Update small blinds"""

        self.game.setMaxPlayers(4)

        # Create players
        player1 = self.AddPlayerAndSit(1, 1)
        player2 = self.AddPlayerAndSit(2, 3)
        player3 = self.AddPlayerAndSit(3, 6)
        player4 = self.AddPlayerAndSit(4, 8)

        # Update blinds
        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': 'small', 'missed_blind': None, 'wait_for': False},
            3: { 'blind': 'big', 'missed_blind': None, 'wait_for': False},
            4: { 'blind': False, 'missed_blind': None, 'wait_for': False}
        }

        self.game.updateBlinds()

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

        # Init players infos
        self.game.playersBeginTurn()

        # Player 2 has already payed the blind =>
        # Nothing is done
        player2.blind = True
        self.game.updateBlinds()

        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': True, 'missed_blind': None, 'wait_for': False},
            3: { 'blind': 'big', 'missed_blind': None, 'wait_for': False},
            4: { 'blind': False, 'missed_blind': None, 'wait_for': False}
        }

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

        # Init players infos
        self.game.playersBeginTurn()

        # Player 2 has missed a blind
        player2.missed_blind = 'small'
        self.game.updateBlinds()

        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': False, 'missed_blind': 'small', 'wait_for': 'late'},
            3: { 'blind': 'small', 'missed_blind': None, 'wait_for': False},
            4: { 'blind': 'big', 'missed_blind': None, 'wait_for': False}
        }

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

    # ---------------------------------------------------------
    def testUpdateBigBlinds(self):
        """Test Poker Game: Update big blinds"""

        self.game.setMaxPlayers(4)

        # Create players
        player1 = self.AddPlayerAndSit(1, 1)
        player2 = self.AddPlayerAndSit(2, 3)
        player3 = self.AddPlayerAndSit(3, 6)
        player4 = self.AddPlayerAndSit(4, 8)

        # Update blinds
        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': 'small', 'missed_blind': None, 'wait_for': False},
            3: { 'blind': 'big', 'missed_blind': None, 'wait_for': False},
            4: { 'blind': False, 'missed_blind': None, 'wait_for': False}
        }

        self.game.updateBlinds()

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

        # Init players infos
        self.game.playersBeginTurn()

        # Player 2 has already payed the blind =>
        # Nothing is done
        player3.blind = True
        player3.wait_for = 'small'
        self.game.updateBlinds()

        blinds = {
            1: { 'blind': False, 'missed_blind': None, 'wait_for': False},
            2: { 'blind': 'small', 'missed_blind': None, 'wait_for': False},
            3: { 'blind': True, 'missed_blind': None, 'wait_for': False},
            4: { 'blind': False, 'missed_blind': None, 'wait_for': False}
        }

        # Check blinds
        for player in blinds.keys():
            for attribute, value in blinds[player].items():
                self.failUnlessEqual(getattr(self.game.getPlayer(player), attribute), value)

    # ---------------------------------------------------------
    def testUpdateErrorSmallAndBigBlinds(self):
        """Test Poker Game: Update error small and big blinds"""

        self.game.setMaxPlayers(pokergame.ABSOLUTE_MAX_PLAYERS)

        # Create players
        for num in range(pokergame.ABSOLUTE_MAX_PLAYERS):
            player = self.AddPlayerAndSit(num + 1)
            player.wait_for = 'big'
        self.game.getPlayer(1).wait_for = 'first_round'

        # Error small blind can not be assigned
        self.game.updateBlinds()

        # Check player 1 blinds
        blinds1 = {'blind': 'late', 'missed_blind': None, 'wait_for': 'first_round'}

        # Check blinds
        for attribute, value in blinds1.items():
            self.failUnlessEqual(getattr(self.game.getPlayer(1), attribute), value)

        blinds = {'blind': 'late', 'missed_blind': None, 'wait_for': 'big'}

        # Check players blinds
        for num in range(1, pokergame.ABSOLUTE_MAX_PLAYERS):
            for attribute, value in blinds.items():
                self.failUnlessEqual(getattr(self.game.getPlayer(num + 1), attribute), value)

    def testShowdownstack(self):
        game = pokergame.PokerGameServer("poker.%s.xml", [path.join(TESTS_PATH, '../conf'), PokerGameTestCase.TestConfDirectory])
        game.setVariant("holdem")
        game.setBettingStructure("100-200_2000-20000_no-limit")

        player = {}

        money = {
            66: 300,
            76: 100,
            77: 200,
        }

        for serial in (66, 76, 77):
            self.assert_(game.addPlayer(serial))
            player[serial] = game.serial2player[serial]
            player[serial].money = 20000
            player[serial].buy_in_payed = True
            self.assert_(game.sit(serial))
            player[serial].auto_blind_ante = True
            player[serial].money = money[serial]
            game.autoMuck(serial, pokergame.AUTO_MUCK_ALWAYS)

        game.dealer_seat = 0

        game.beginTurn(1)

        player[66].blind = 'small'
        player[76].blind = 'big'
        player[77].blind = None

        game.deck = ['7c', 'Qs', '6c', 'Qc', '2h', '8c', '4h', 'Jh', '4c', '9s', '3h' ]

        game.setPosition(0)

        game.callNraise(66, 200)
        self.assertEqual("end", game.state)
        game_state = game.showdown_stack[0]
        self.assertEqual(game_state["type"], "game_state")

        for s, p in player.items():
            self.assertEqual(p.money, game_state["serial2money"][s])

    def testAllInWithDead(self):
        """ Test Poker Game: Allin with dead blind and lost to the winner although the winner has less money """

        game = pokergame.PokerGameServer("poker.%s.xml", [path.join(TESTS_PATH, '../conf'), PokerGameTestCase.TestConfDirectory])
        game.setVariant("holdem")
        game.setBettingStructure("100-200_2000-20000_no-limit")

        player = {}

        money = {}
        money[66] = 300
        money[76] = 100
        money[77] = 200

        for serial in (66, 76, 77):
            self.assert_(game.addPlayer(serial))
            player[serial] = game.serial2player[serial]
            player[serial].money = 20000
            player[serial].buy_in_payed = True
            self.assert_(game.sit(serial))
            #player[serial].auto_blind_ante = True
            player[serial].money = money[serial]
            game.autoMuck(serial, pokergame.AUTO_MUCK_ALWAYS)

        game.dealer_seat = 0

        game.beginTurn(1)

        player[66].blind = 'big_and_dead'
        player[76].blind = 'small'
        player[77].blind = 'big'

        #
        # 77: 4c 8c
        # 76: 9s 4h
        # 66: 3h Jh
        #
        game.deck = ['7c', 'Qs', '6c', 'Qc', '2h', '8c', '4h', 'Jh', '4c', '9s', '3h' ]

        game.setPosition(0)
        game.blind(66, 200, 100)
        game.blind(76, 100, 0)
        game.blind(77, 200, 0)

        self.assertEqual("end", game.state)
        rake = game.getRakedAmount()
        self.failUnlessEqual(30, rake)
        self.assertEqual(400 - rake, game.showdown_stack[0]['serial2delta'][77])

    def testDeadWithUncalled(self):
        """ Test Poker Game: dead blind + a player has uncalled bet and is not the winner.
        """
        game = pokergame.PokerGameServer("poker.%s.xml", [path.join(TESTS_PATH, '../conf'), PokerGameTestCase.TestConfDirectory])
        game.setVariant("holdem")
        game.setBettingStructure("100-200_2000-20000_no-limit")

        player = {}

        money = {}
        money[66] = 20000
        money[76] = 10000
        money[77] = 10000

        for serial in (66, 76, 77):
            self.assert_(game.addPlayer(serial))
            player[serial] = game.serial2player[serial]
            player[serial].money = 2000
            player[serial].buy_in_payed = True
            self.assert_(game.sit(serial))
            #player[serial].auto_blind_ante = True
            game.autoMuck(serial, pokergame.AUTO_MUCK_ALWAYS)
            player[serial].money = money[serial]

        game.dealer_seat = 0

        game.beginTurn(1)

        player[66].blind = 'big_and_dead'
        player[76].blind = 'small'
        player[77].blind = 'big'

        #
        # 77: 4c 8c
        # 76: 9s 4h
        # 66: 3h Jh
        #
        game.deck = ['7c', 'Qs', '6c', 'Qc', '2h', '4h', 'Jh', '8c', '9s', '3h', '4c' ]

        game.setPosition(0)
        game.blind(66, 200, 100)
        game.blind(76, 100, 0)
        game.blind(77, 200, 0)

        self.assertEqual(game.state, "pre-flop")

        game.callNraise(66, 20000)
        game.call(76)
        game.fold(77)

    def testLastInGameDoesNotAct(self):
        """ Test Poker Game: player folds (although he could check) while a player is allin and
        another player is behind him. The turn ends now, the last player is not asked for his action.
        """
        game = pokergame.PokerGameServer("poker.%s.xml", [path.join(TESTS_PATH, '../conf'), PokerGameTestCase.TestConfDirectory])
        game.setVariant("holdem")
        game.setBettingStructure("100-200_2000-20000_no-limit")

        player = {}

        money = {}
        money[66] = 2000
        money[76] = 30000
        money[77] = 1000

        for serial in (66, 76, 77):
            self.assert_(game.addPlayer(serial))
            player[serial] = game.serial2player[serial]
            player[serial].money = 2000
            player[serial].buy_in_payed = True
            self.assert_(game.sit(serial))
            #player[serial].auto_blind_ante = True
            game.autoMuck(serial, pokergame.AUTO_MUCK_ALWAYS)
            game.autoBlindAnte(serial)
            player[serial].money = money[serial]

        game.dealer_seat = 0

        #
        # 77: 4c 8c
        # 76: 9s 4h
        # 66: 3h Jh
        #
        game.deck = ['7c', 'Qs', '6c', 'Qc', '2h', '4h', 'Jh', '8c', '9s', '3h', '4c' ]
        game.board = pokercards.PokerCards(['9c', '3d', '2d', 'Qd', 'Ah'])

        # player list: [66, 76, 77]
        # dealer: 66
        game.beginTurn(1)
        game.call(66)
        game.call(76)
        game.check(77)
        self.assertEqual(game.state, "flop")

        game.callNraise(76, 1500)
        game.call(77)
        game.call(66)
        self.assertEqual(game.state, "turn")

        game.fold(76)
        self.assertEqual(game.state, "end")

    def testAllInAndFoldInNewRound(self):
        """ Test Poker Game: player folds to a raise when heads up
            in a betting round. Another player was allin in the previous
            round. The winner has an uncalled amount AND wins the pot
            in which the allin player was not.
        """
        game = pokergame.PokerGameServer("poker.%s.xml", [path.join(TESTS_PATH, '../conf'), PokerGameTestCase.TestConfDirectory])
        game.setVariant("holdem")
        game.setBettingStructure("100-200_2000-20000_no-limit")

        player = {}

        money = {}
        money[66] = 2000
        money[76] = 30000
        money[77] = 1000

        for serial in (66, 76, 77):
            self.assert_(game.addPlayer(serial))
            player[serial] = game.serial2player[serial]
            player[serial].money = 2000
            player[serial].buy_in_payed = True
            self.assert_(game.sit(serial))
            #player[serial].auto_blind_ante = True
            game.autoMuck(serial, pokergame.AUTO_MUCK_ALWAYS)
            game.autoBlindAnte(serial)
            player[serial].money = money[serial]

        game.dealer_seat = 0

        #
        # 77: 4c 8c
        # 76: 9s Jd
        # 66: 3h Jh
        #
        game.deck = ['7c', 'Qs', '6c', 'Qc', '2h', 'Jd', 'Jh', '8c', '9s', '3h', '4c' ]
        game.board = pokercards.PokerCards(['9c', '3d', '2d', 'Qd', 'Ah'])

        # player list: [66, 76, 77]
        # dealer: 66
        game.beginTurn(1)
        game.call(66)
        game.call(76)
        game.check(77)
        self.assertEqual(game.state, "flop")

        game.callNraise(76, 1500)
        game.call(77)
        game.call(66)
        self.assertEqual(game.state, "turn")

        game.callNraise(76, 1500)
        game.fold(66)
        self.assertEqual(game.state, "end")

    def testUpdateHistoryEnd(self):
        game = self.game
        game.turn_history = [("one",), ("two",), ("end",), ("three",)]
        game.updateHistoryEnd(winners = "winners", showdown_stack = "showdown_stack")
        self.assertEqual(("end", "winners", "showdown_stack"), game.turn_history[2])

    def testEmtpyShowdownStack(self):
        turn_history = [("end", [], []),]
        pokergame.history2messages(None, turn_history)

    def testPlayerListIndexAdd(self):
        game = self.game
        players = [
            (100, True),
            (101, True),
            (102, False),
            (103, False),
            (104, True),
            (105, False),
        ]
        pred = lambda x: x[1]
        game.player_list = [p[0] for p in players]
        game.serial2player = dict((p[0],p) for p in players)
        players_truey_count = len([p for p in players if pred(p)])

        # positive without skip
        self.assertEqual(1,game.playerListIndexAdd(0, 1, pred))

        # positive with skip
        self.assertEqual(4,game.playerListIndexAdd(1, 1, pred))

        # positive with skip, position is falsy
        self.assertEqual(4,game.playerListIndexAdd(2, 1, pred))
        self.assertEqual(4,game.playerListIndexAdd(3, 1, pred))

        # test loop over
        self.assertEqual(0,game.playerListIndexAdd(3, 2, pred))
        self.assertEqual(0,game.playerListIndexAdd(4, 1, pred))

        # test simple negative
        self.assertEqual(4,game.playerListIndexAdd(0, -1, pred))
        self.assertEqual(4,game.playerListIndexAdd(5, -1, pred))
        self.assertEqual(1,game.playerListIndexAdd(4, -1, pred))

        # test too big for list, position is truey
        self.assertEqual(0,game.playerListIndexAdd(4, 1+2*players_truey_count, pred))
        self.assertEqual(0,game.playerListIndexAdd(4, 1-2*players_truey_count, pred))

        # test too big for list, position is falsy
        self.assertEqual(4,game.playerListIndexAdd(3, 1+2*players_truey_count, pred))
        self.assertEqual(0,game.playerListIndexAdd(3, 1-2*players_truey_count, pred))

        # test too big for list, position is falsy, gets itself
        self.assertEqual(4,game.playerListIndexAdd(3, 4+2*players_truey_count, pred))
        self.assertEqual(0,game.playerListIndexAdd(3, 4-2*players_truey_count, pred))

    def testHistoryReduceAutoPlaySitInAndOut(self):
        histories = []
        self.game.variant = 'holdem'
        self.game.setMaxPlayers(4)
        player_serials = [100,200,300,400]
        player_seats = [1,3,6,8]
        players = {}

        for (serial,seat) in zip(player_serials,player_seats):
            players[serial] = self.AddPlayerAndSit(serial, seat)
            self.game.noAutoBlindAnte(serial)

        self.game.beginTurn(1)
        self.failUnless(self.game.isBlindAnteRound())

        self.game.blind(200)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        # . Table.playerTimeoutTimer
        self.game.sitOutNextTurn(300)
        self.game.autoPlayer(300)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        # . PACKET_POKER_TABLE_JOIN
        # .. Avatar.performPacketPokerTableJoin
        # ... PokerTable.joinPlayer
        self.game.comeBack(300)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        # . PACKET_POKER_SIT_OUT
        # .. Table.sitOutPlayer
        self.game.sitOutNextTurn(300)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        # . PACKET_POKER_SIT
        # .. Avatar.performPacketPokerSit
        # ... Table.sitPlayer
        # .... Avatar.sitPlayer
        self.game.sit(300)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        # . PACKET_POKER_SIT_OUT
        # .. Table.sitOutPlayer
        self.game.sitOut(400)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        # 3 has to pay the blind now
        self.game.blind(300)
        if self.game.historyCanBeReduced(): self.game.historyReduce()
        self.failUnless(self.game.isFirstRound())


        history_reduced_should = [
            ('game', 0, 1, 0, 0, 'holdem', 'config', [100, 200, 300], 1, {200: 1600, 300: 1600, 100: 1600}),
            ('position', 1, 200), ('blind', 200, 500, 0),
            ('position', 2, 300),
            ('position', 0, 100),
            ('position', 2, 300), ('blind', 300, 1000, 0),
            ('position', -1, None),
            ('round', 'pre-flop', pokercards.PokerCards([]), {200: pokercards.PokerCards([193, 204]), 100: pokercards.PokerCards([237, 209]), 300: pokercards.PokerCards([243, 196])}),
            ('position', 0, 100)
        ]
        history_reduced_is = self.game.historyGet()
        self.assertEquals(
            history_reduced_should, history_reduced_is,
            "error in history reduction.\nreduced:\n %s\nshould_be:\n %s" % (
                ",\n ".join(map(str,history_reduced_is)),
                ",\n ".join(map(str,history_reduced_should))
            )
        )

    def testHistoryReduceError(self):
        self.game.variant = 'holdem'
        self.game.setMaxPlayers(9)
        player_serials = [100, 200, 300, 400, 500, 600, 700]
        player_seats = [0, 1, 2, 3, 4, 5, 8]
        players = {}

        for (serial,seat) in zip(player_serials,player_seats):
            players[serial] = self.AddPlayerAndSit(serial, seat)
            self.game.noAutoBlindAnte(serial)

        self.game.forced_dealer_seat = 2
        self.game.beginTurn(1)

        players[700].blind = 'late'
        players[700].missed_blind = 'big'

        self.game.blind(400)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

        self.game.sitOutNextTurn(500)
        if self.game.historyCanBeReduced(): self.game.historyReduce()
        self.game.blind(600)
        if self.game.historyCanBeReduced(): self.game.historyReduce()
        self.game.blind(700)
        if self.game.historyCanBeReduced(): self.game.historyReduce()

    def testHistoryReduceWhenLeavingInBlind(self):
        game = self.game
        player_serials = [10,20]
        game.variant = 'holdem'
        game.setMaxPlayers(9)
        players = {}
        for serial in player_serials:
            players[serial] = self.AddPlayerAndSit(serial)
            game.noAutoBlindAnte(serial)
        game.beginTurn(1)
        game.blind(20)
        game.sitOutNextTurn(20)
        game.autoPlayer(20)
        game.removePlayer(20)
        game.blind(10)
        game.historyReduce()

    def testBlindAndAnteTogetherAllIn(self):
        game = self.game
        game.variant = 'holdem'
        game.setMaxPlayers(9)
        game.blind_info = False
        game.blind_info = {'small': 20,'big': 40,'change': False}
        game.ante_info = {'value': 1, 'bring-in': 5, 'change': False}
        game.best_buy_in = 100

        players = {}
        serials = [10, 20]
        money = [50, 100]
        for s,m in zip(serials,money):
            players[s] = self.AddPlayerAndSit(s)
            game.autoBlindAnte(s)
            players[s].money = m

        game.beginTurn(1)
        game.callNraise(20, 200)
        game.call(10)

    def testDistributeMoneyUnexpectedWinnerSerial(self):
        game = self.game
        game.variant = 'holdem'
        game.setMaxPlayers(9)
        game.blind_info = False
        game.blind_info = {'small': 20,'big': 40,'change': False}
        game.ante_info = None
        game.best_buy_in = 100

        players = {}

        construction = {
            1: {'seat':1, 'serial': 1, 'money': 18,   'blind':'big', 'missed_blind':None, 'wait_for':False},
            3: {'seat':3, 'serial': 3, 'money': 2000, 'blind':'late', 'missed_blind':'small', 'wait_for':False},
            4: {'seat':4, 'serial': 4, 'money': 2000, 'blind':False, 'missed_blind':None, 'wait_for':False},
            5: {'seat':5, 'serial': 5, 'money': 2000, 'blind':'small', 'missed_blind':None, 'wait_for':False},
        }

        for info in construction.values():
            s = info["serial"]
            players[s] = self.AddPlayerAndSit(s, info['seat'])
            players[s].money = info["money"]
            players[s].missed_blind = info["missed_blind"]

        game.dealer_seat = 3
        game.first_turn = False
        log_history.reset()

        game.beginTurn(1)
        for info in construction.values():
            _p_ = game.serial2player[info['serial']]
            self.assertEqual(_p_.blind, info['blind'], "player %s has blind %r but should have %r" % (_p_.serial, _p_.blind, info['blind']))

        # Pay the blinds
        i = 0
        while game.state == "blindAnte":
            i += 1
            self.assertTrue(i <= 3, "Too many Blinds to pay")
            player_serial = game.getSerialInPosition()
            game.blind(player_serial)
            self.assertTrue(players[player_serial].bet > 0)

        game.fold(construction[3]['serial'])
        game.fold(construction[4]['serial'])

        game_state = game.showdown_stack[0]
        self.assertEqual(game_state['type'], 'game_state')
        self.assertEqual(len(game_state['side_pots']['contributions'][0].keys()), 3)


        # the big blind wins twice his money minus the rake
        self.assertEqual(game_state['serial2rake'][construction[1]['serial']], 1)
        self.assertEqual(game_state['serial2delta'][construction[1]['serial']], 35)
        self.assertEqual(game_state['serial2delta'][construction[5]['serial']], -17)
        # the late blind only loses the small blind, because nobody called his late blind
        self.assertEqual(game_state['serial2delta'][construction[3]['serial']], -20)

    def testSitBeforeBlindAndAllSitOutAfterwards(self):
        game = self.game
        game.variant = 'holdem'
        game.setMaxPlayers(9)

        # add player 10
        player10 = self.AddPlayerAndSit(10)

        # add player 20, but don't get a seat just yet
        self.assertTrue(game.addPlayer(20))
        self.assertTrue(game.payBuyIn(20, game.bestBuyIn()))
        player20 = self.GetPlayer(20)

        # add player 30
        player30 = self.AddPlayerAndSit(30)

        # change the seat and begin the turn
        game.forced_dealer_seat = 2
        game.beginTurn(1)

        # we did not activate autoblindante, so we are still in the blind ante round
        self.assertTrue(game.isBlindAnteRound())

        # before any blinds are payed, player 20 is seated
        self.assertTrue(game.sit(20))

        # pay small and big blinds
        game.blind(10)
        game.blind(30)

        # the game should still be in the blindAnteRound, because player 20 is missing
        self.assertTrue(game.isFirstRound())

        # player 20 is set on auto, i.e. he folds, because we are still in blind/ante
        game.autoPlayer(20)

        # the game should be in its first round now
        self.assertTrue(game.isFirstRound())

        # the other players are set on autoplay and should now finish the round
        game.fold(10)
        self.assertTrue(game.isEndOrNull())

    def _autoPlayTurn(self, actions={}, default_action='fold', additional_packets=None, expect=True):
        state = self.game.state
        if additional_packets:
            for packet, args in additional_packets:
                retval = getattr(self.game, packet)(*args)
                self.game.log.debug( '%s > %s %r -> %r' % (state, packet, args, retval))

        i = 0
        while self.game.state == state:
            i += 1
            if i > 20: raise Exception('Loop')
            player = self.game.getPlayerInPosition()
            serial = player.serial
            if isinstance(actions, dict):
                action = actions.get(serial, default_action)
            else:
                action = actions[i]
            if isinstance(action, (list, tuple)):
                action, params = action
            else:
                params = ()
            if action == 'raise':
                action = 'callNraise'
            retval = getattr(self.game,action)(serial,*params)
            self.game.log.debug('%s > %s %s %r -> %s' %(state, action, serial, params, retval))
            if retval in (True, False):
                self.failUnless(retval == expect)

    def _autoPlayInit(self):
        clear_all_messages()

        game = self.game
        player_serials = [13,26]
        game.variant = 'holdem'
        game.setMaxPlayers(9)
        players = {}
        for serial in player_serials:
            players[serial] = self.AddPlayerAndSit(serial)
            players[serial].money = 2000000
            players[serial].auto = False
            game.noAutoBlindAnte(serial)

        return players

    def _autoPlay(self, additional_packets=(None, None, None, None), doitL=(None, None, None, None), expectedPlayers=2):
        game = self.game
        game.beginTurn(1)
        self._autoPlayTurn(default_action='blind', expect=None)

        doits = [
            dict(actions={26:'autoPlayer', 13:('raise', (8,))}),
            dict(actions={13:('raise', (9,)), 26:'call'}),
            dict(actions={13:('raise', (19,)), 26:'call'}),
            dict(actions={13:'check', 26:'check'}),
        ]

        states = ['pre-flop','flop','turn','river']

        for (doit,doitfallback,additional_packet,state) in zip(doitL,doits,additional_packets,states):
            if state != game.state:
                continue
            doitdict = doit if doit else doitfallback
            self._autoPlayTurn(additional_packets=additional_packet, **doitdict)

        self.failUnless(expectedPlayers == self.game.sitCount())

    def _didPlayerFold(self, player_id, allow_other_actions=True):
        hist = self.game.historyGet()
        player_folded = False
        other_actions = False
        for line in hist:
            if line[1] == player_id:
                if line[0] in ('call', 'check', 'raise'):
                    other_actions = True
                if line[0] == 'fold':
                    player_folded = True
        if player_folded:
            if not allow_other_actions and other_actions:
                return False
            return True
        return False

    def testAutoPlayPlayerShouldFoldAsDefault(self):
        self._autoPlayInit()
        self._autoPlay(additional_packets=([('sitOutNextTurn',(26,)),],None,[('sit',(26,))]),expectedPlayers=1)
        self.failIfEqual(self._didPlayerFold(26), False)
        self.failUnless(self._didPlayerFold(26))

    def testAutoPlayPlayerShouldBeAbleToGetBackToTheGameIfBotPolicyIsSet(self):
        self._autoPlayInit()
        self.game.serial2player[26].auto_policy = pokergame.AUTO_POLICY_BOT
        self._autoPlay(additional_packets=([('sitOutNextTurn',(26,))],None,[('sit',(26,))]),expectedPlayers=2)
        self.failIf(self._didPlayerFold(26))

    def testAutoPlayShouldEndAfterOneHandTournament(self):
        self._autoPlayInit()
        self._autoPlay(expectedPlayers=2)

    def testAutoPlayShouldEndAfterOneHand(self):
        self._autoPlayInit()
        self._autoPlay()

    # ---------------------------------------------------------
    def AddPlayerAndSit(self, serial, seat = -1):
        self.failUnless(self.game.addPlayer(serial, seat))
        self.failUnless(self.game.payBuyIn(serial,self.game.bestBuyIn()))
        player = self.GetPlayer(serial)
        self.failUnless(player.isBuyInPayed())
        self.failUnless(self.game.sit(serial))
        self.failUnless(self.game.isSit(serial))
        return player

    # ---------------------------------------------------------
    def ModifyXMLFile(self, xml_file, parent, child, attributes = {}):
        doc = etree.XML(open(xml_file, 'r').read())

        if parent is not None:
            parentNode = doc.xpath(parent)
            if len(parentNode) > 0:
                parentNode = parentNode[0]

        if child is not None:
            node = etree.Element(child)
        else:
            node = parentNode

        for attribute_name, attribute_value in attributes.items():
            node.attrib[attribute_name] = attribute_value

        if node != parentNode:
            parentNode.append(node)

        xmlFile = open(xml_file, 'w')
        xmlFile.write(etree.tostring(doc, pretty_print=True))
        xmlFile.close()
        return True

    # ---------------------------------------------------------
    def CopyFile(self, src_path, dst_path):
        if src_path and not path.isfile(src_path):
            return False

        shutil.copyfile(src_path,dst_path)
        if path.isfile(dst_path):
            return True

        return False

    # ---------------------------------------------------------
    def DeleteFile(self, file_path):
        if path.isfile(file_path):
            os.unlink(file_path)

    # ---------------------------------------------------------
    def GetPlayer(self, serial):
        player = self.game.getPlayer(serial)
        self.failIfEqual(player, None)
        return player

    # ---------------------------------------------------------
    def CreateGameClient(self):
        if not self.CopyFile(self.ConfigTmplFile, self.ConfigTempFile):
            self.fail('Error during creation of configuration file ' + self.ConfigTempFile)

        self.game = pokergame.PokerGameClient(PokerGameTestCase.TestUrl, [PokerGameTestCase.TestConfDirectory, tempfile.gettempdir()])

    # ---------------------------------------------------------
    def CreateGameServer(self):
        if not self.CopyFile(self.ConfigTmplFile, self.ConfigTempFile):
            self.fail('Error during creation of configuration file ' + self.ConfigTempFile)

        self.game = pokergame.PokerGameServer(PokerGameTestCase.TestUrl, [PokerGameTestCase.TestConfDirectory, tempfile.gettempdir()])

    # ---------------------------------------------------------
    def InitGame(self):
        self.game.setTime(0)

        if not self.CopyFile(self.VariantTmplFile, self.VariantTempFile):
            self.fail('Error during creation of variant file ' + self.VariantTempFile)

        self.game.setVariant(PokerGameTestCase.TestVariantTemporaryFile)

        # Reload the betting structure
        self.game.setBettingStructure(PokerGameTestCase.TestConfigTemporaryFile)
        self.game.setMaxPlayers(2)
        self.game.id = 4

        predefined_decks = string.split("8d 2h 2c 8c 4c Kc Ad 9d Ts Jd 5h Tc 4d 9h 8h 7h 9c 2s 3c Kd 5s Td 5d Th 3s Kh Js Qh 7d 2d 3d 9s Qd Ac Jh Jc Qc 6c 7s Ks 5c 4h 7c 4s Qs 6s 6h Ah 6d As 3h 8s")
        shuffler = PokerPredefinedDecks([map(lambda card: self.game.eval.string2card(card), predefined_decks)])

        self.game.deck = predefined_decks
        self.game.shuffler = shuffler

# ---------------------------------------------------------
def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerGameTestCase))
#    suite.addTest(unittest.makeSuite(PokerGameTestCase, prefix = "test2"))
    return suite

# ---------------------------------------------------------
def GetTestedModule():
    return pokergame

# ---------------------------------------------------------
def run():
    return unittest.TextTestRunner().run(GetTestSuite())

# ---------------------------------------------------------
if __name__ == '__main__':
    if run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "( cd .. ; ./config.status tests/test-game.py ) ; ( cd ../tests ; make COVERAGE_FILES='../pokerengine/pokergame.py' TESTS='coverage-reset test-game.py coverage-report' check )"
# End:


