from dataclasses import dataclass


@dataclass
class PickemResult:
    """Represents a single pick'em result entry."""

    """Player name"""
    name: str
    """List of results: [name, points, wins, losses]"""
    results: list
    """List of picks made by the player"""
    picks: list

    def __init__(self):
        self.name = ""
        self.results = []
        self.picks = []

    def __str__(self):
        out = "PickemResult: { name: " + self.name + ", results: [ " + self.csv() + " ] }"
        return out

    def csv(self):
        cols = [self.name] + [str(x) for x in self.results]
        csv = ",".join(cols)
        return csv
