from enum import Enum
from typing import List


class GameTypesEnum(Enum):
    TIC_TAC_TOE = "TicTacToe"
    RPC = "RPC"
    DOTBOX = "DotBox"
    MNUMBERS = "MNumbers"
    MSweeper = "MSweeper"
    FEKRBEKR = "FekrBekr"
    YATZY = "Yatzy"
    PENTAGO = "Pentago"
    FOURINROW = "FourInRow"
    SUDOKU = "Sudoku"
    BATTLESHIP = "BattleShip"
    BOXFOUR = "BoxFour"
    YINSH = "Yinsh"
    CHESS = "Chess"
    CHECKERS = "Checkers"
    OTHELLO = "Othello"
    MILL = "Mill"
    LUDO = "Ludo"
    RISK = "Risk"
    UNO = "Uno"
    BACKGAMMON = "BackGammon"

    @classmethod
    def all(cls) -> List[Enum]:
        return list(cls)

    @classmethod
    def multi_players_games(cls) -> List[Enum]:
        return [cls.LUDO, cls.RISK, cls.UNO]

    @classmethod
    def two_players_games(cls) -> List[Enum]:
        data = list(cls)
        if cls.LUDO in data:
            data.remove(cls.LUDO)
        if cls.RISK in data:
            data.remove(cls.RISK)
        if cls.UNO in data:
            data.remove(cls.UNO)
        return data

    @classmethod
    def is_in_two_players(cls, value) -> bool:
        for member in cls.two_players_games():
            if member.value == value:
                return True
        return False
