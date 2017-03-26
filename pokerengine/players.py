class BasePokerPlayer(object):
  """Abstract Poker player

     Used as a base implementation to handle play from the poker game
  """

  def __init__(self):
    pass

  def eval(self, game):
    err_msg = self.__build_err_msg("declare_action")
    raise NotImplementedError(err_msg)

  def __build_err_msg(self, msg):
    return "Your client does not implement [ {0} ] method".format(msg)
