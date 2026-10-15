from __future__ import annotations

import zlib
from dataclasses import dataclass

from app.models import Player, Team

DEFAULT_HOME = "MUN"
DEFAULT_AWAY = "MCI"

ROLE_BASE: dict[str, tuple[float, float, float, float]] = {
    "goalkeeper": (0.10, 0.56, 0.30, 0.40),
    "right_back": (0.34, 0.75, 0.72, 0.78),
    "left_back": (0.34, 0.75, 0.72, 0.78),
    "centre_back": (0.28, 0.72, 0.72, 0.66),
    "defensive_midfielder": (0.42, 0.80, 0.80, 0.66),
    "central_midfielder": (0.54, 0.84, 0.68, 0.70),
    "attacking_midfielder": (0.68, 0.84, 0.60, 0.72),
    "right_midfielder": (0.60, 0.78, 0.60, 0.78),
    "left_midfielder": (0.60, 0.78, 0.60, 0.78),
    "right_winger": (0.68, 0.78, 0.58, 0.86),
    "left_winger": (0.68, 0.78, 0.58, 0.86),
    "striker": (0.78, 0.70, 0.60, 0.80),
}

STARS: dict[str, tuple[float, float, float, float]] = {
    "E. Haaland": (0.92, 0.72, 0.62, 0.82),
    "B. Saka": (0.74, 0.82, 0.60, 0.87),
    "C. Palmer": (0.80, 0.86, 0.60, 0.76),
    "A. Isak": (0.86, 0.74, 0.60, 0.85),
    "B. Fernandes": (0.78, 0.88, 0.66, 0.70),
    "F. Wirtz": (0.76, 0.88, 0.66, 0.78),
    "A. Mac Allister": (0.62, 0.88, 0.70, 0.66),
    "M. Gibbs-White": (0.74, 0.84, 0.64, 0.76),
    "A. Semenyo": (0.74, 0.76, 0.60, 0.86),
    "M. Cunha": (0.76, 0.76, 0.60, 0.82),
    "V. van Dijk": (0.32, 0.80, 0.75, 0.66),
    "D. Rice": (0.50, 0.86, 0.82, 0.72),
    "M. Ødegaard": (0.66, 0.90, 0.66, 0.70),
    "D. Raya": (0.10, 0.64, 0.30, 0.42),
    "Alisson": (0.10, 0.62, 0.30, 0.40),
    "G. Donnarumma": (0.10, 0.64, 0.30, 0.44),
}

ROLE_OVERRIDE: dict[str, str] = {
    "A. Isak": "striker",
    "C. Gakpo": "left_winger",
    "V. Muñoz": "right_winger",
    "O. Marmoush": "striker",
    "M. Tel": "striker",
    "Sávio": "left_winger",
    "A. Semenyo": "left_winger",
    "P. Neto": "right_winger",
    "J. Anthony": "right_winger",
    "D. Ndoye": "right_winger",
    "Y. Pino": "right_winger",
    "A. Khalaili": "left_winger",
    "E. Nketiah": "striker",
    "E. Buendía": "attacking_midfielder",
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _rate(name: str, role: str) -> tuple[float, float, float, float]:
    if name in STARS:
        return STARS[name]
    base = ROLE_BASE.get(role, (0.5, 0.6, 0.6, 0.6))
    c = zlib.crc32(name.encode("utf-8"))

    def jitter(shift: int) -> float:
        return (((c >> (shift * 5)) & 0xFF) / 255.0 * 2.0 - 1.0) * 0.07

    return (
        _clamp(base[0] + jitter(0)),
        _clamp(base[1] + jitter(1)),
        _clamp(base[2] + jitter(2)),
        _clamp(base[3] + jitter(3)),
    )


def _line_roles(line: str, count: int) -> list[str]:
    if line == "def":
        if count <= 1:
            return ["centre_back"] * max(count, 0)
        if count == 2:
            return ["centre_back", "centre_back"]
        if count >= 4:
            return ["right_back"] + ["centre_back"] * (count - 2) + ["left_back"]
        return ["centre_back"] * count
    if line == "mid":
        roles = ["central_midfielder"] * count
        if count >= 2:
            roles[0] = "defensive_midfielder"
        if count >= 3:
            roles[-1] = "attacking_midfielder"
        if count >= 4:
            roles[1] = "central_midfielder"
        if count >= 5:
            roles[-2] = "right_midfielder"
        return roles
    if count <= 0:
        return []
    if count == 1:
        return ["striker"]
    if count == 2:
        return ["striker", "striker"]
    if count == 3:
        return ["right_winger", "striker", "left_winger"]
    if count == 4:
        return ["right_winger", "striker", "striker", "left_winger"]
    return ["right_winger"] + ["striker"] * (count - 2) + ["left_winger"]


def formation_slots(formation: str) -> list[tuple[str, str, float, float]]:
    lines = [int(part) for part in formation.split("-")]
    total = len(lines)
    slots: list[tuple[str, str, float, float]] = [("GK", "goalkeeper", 5.0, 50.0)]
    span = 62.0 / (total - 1) if total > 1 else 0.0
    for li, count in enumerate(lines):
        x = 18.0 + li * span
        if li == 0:
            kind = "def"
        elif li == total - 1:
            kind = "fwd"
        else:
            kind = "mid"
        roles = _line_roles(kind, count)
        for j in range(count):
            pos = _position_code(kind, roles[j])
            y = 50.0 if count == 1 else 12.0 + j * (76.0 / (count - 1))
            slots.append((pos, roles[j], round(x, 1), round(y, 1)))
    return slots


def _position_code(kind: str, role: str) -> str:
    table = {
        "goalkeeper": "GK",
        "right_back": "RB",
        "left_back": "LB",
        "centre_back": "CB",
        "defensive_midfielder": "DM",
        "central_midfielder": "CM",
        "attacking_midfielder": "AM",
        "right_midfielder": "RM",
        "left_midfielder": "LM",
        "right_winger": "RW",
        "left_winger": "LW",
        "striker": "ST",
    }
    return table.get(role, "CM")


@dataclass(frozen=True)
class Club:
    id: str
    name: str
    short: str
    color: str
    formation: str
    players: tuple[tuple[str, int], ...]


def build_team(team_id: str, club: Club, attack_dir: int) -> Team:
    slots = formation_slots(club.formation)
    built: list[Player] = []
    for idx, (pos, role, base_x, base_y) in enumerate(slots):
        name, number = club.players[idx]
        role = ROLE_OVERRIDE.get(name, role)
        pos = _position_code("", role)
        if attack_dir > 0:
            x, y = base_x, base_y
        else:
            x, y = 100 - base_x, 100 - base_y
        finishing, passing, pressing, pace = _rate(name, role)
        built.append(
            Player(
                id=idx + 1,
                name=name,
                number=number,
                position=pos,
                role=role,
                x=round(x, 1),
                y=round(y, 1),
                finishing=finishing,
                passing=passing,
                pressing=pressing,
                pace=pace,
            )
        )
    return Team(
        id=team_id,
        name=club.name,
        short=club.short,
        color=club.color,
        formation=club.formation,
        players=built,
    )


PL_CLUBS: dict[str, Club] = {
    "ARS": Club("ARS", "Arsenal", "ARS", "#EF0107", "5-2-3", (
        ("D. Raya", 41),
        ("B. White", 4),
        ("G. Magalhães", 6),
        ("E. Konsa", 15),
        ("R. Calafiori", 33),
        ("M. Lewis-Skelly", 49),
        ("M. Ødegaard", 8),
        ("D. Rice", 41),
        ("B. Saka", 7),
        ("K. Havertz", 29),
        ("C. Tzolis", 17),
    )),
    "AVL": Club("AVL", "Aston Villa", "AVL", "#670E36", "4-4-2", (
        ("Z. Suzuki", 31),
        ("M. Cash", 2),
        ("V. Lindelöf", 3),
        ("P. Torres", 14),
        ("I. Maatsen", 22),
        ("J. McGinn", 7),
        ("B. Kamara", 6),
        ("R. Barkley", 9),
        ("E. Buendía", 10),
        ("N. Jackson", 11),
        ("G. Hemmings", 53),
    )),
    "BOU": Club("BOU", "Bournemouth", "BOU", "#DA291C", "4-3-3", (
        ("Đ. Petrović", 1),
        ("A. Smith", 15),
        ("A. Silva", 14),
        ("J. Hill", 5),
        ("A. Truffert", 3),
        ("A. Scott", 8),
        ("T. Adams", 12),
        ("M. Tavernier", 16),
        ("Rayan", 37),
        ("Evanilson", 9),
        ("J. Kluivert", 19),
    )),
    "BRE": Club("BRE", "Brentford", "BRE", "#E30613", "3-5-2", (
        ("C. Kelleher", 1),
        ("K. Ajer", 20),
        ("N. Collins", 22),
        ("M. Kayode", 33),
        ("K. Lewis-Potter", 23),
        ("V. Janelt", 27),
        ("M. Damsgaard", 24),
        ("M. Sangaré", 18),
        ("K. Schade", 7),
        ("Igor Thiago", 9),
        ("J. Anthony", 19),
    )),
    "BHA": Club("BHA", "Brighton & Hove Albion", "BHA", "#0057B8", "5-4-1", (
        ("B. Verbruggen", 1),
        ("F. Kadıoğlu", 24),
        ("L. Vušković", 44),
        ("L. Dunk", 5),
        ("O. Boscagli", 21),
        ("M. De Cuyper", 29),
        ("P. Groß", 13),
        ("D. Gómez", 25),
        ("Y. Ayari", 26),
        ("M. Yalcouyé", 35),
        ("C. Kostoulas", 19),
    )),
    "CHE": Club("CHE", "Chelsea", "CHE", "#034694", "5-3-2", (
        ("E. Martínez", 1),
        ("R. James", 24),
        ("W. Fofana", 3),
        ("L. Colwill", 6),
        ("M. Lacroix", 5),
        ("J. Hato", 21),
        ("C. Palmer", 10),
        ("M. Rogers", 17),
        ("R. Lavia", 45),
        ("João Pedro", 9),
        ("P. Neto", 7),
    )),
    "COV": Club("COV", "Coventry City", "COV", "#4AA3DF", "5-4-1", (
        ("C. Rushworth", 19),
        ("M. van Ewijk", 27),
        ("B. Thomas", 4),
        ("E. Pinnock", 2),
        ("A. Amenda", 24),
        ("J. Dasilva", 3),
        ("J. Rudoni", 5),
        ("M. Grimes", 6),
        ("F. Onyeka", 16),
        ("C. Yirenkyi", 8),
        ("E. Mason-Clark", 10),
    )),
    "CRY": Club("CRY", "Crystal Palace", "CRY", "#1B458F", "3-3-4", (
        ("D. Henderson", 1),
        ("C. Richards", 26),
        ("J. Canvot", 6),
        ("T. Mitchell", 3),
        ("D. Kamada", 18),
        ("A. Wharton", 20),
        ("Q. Timber", 23),
        ("A. Khalaili", 25),
        ("Y. Pino", 10),
        ("J. Strand Larsen", 22),
        ("E. Nketiah", 9),
    )),
    "EVE": Club("EVE", "Everton", "EVE", "#003399", "3-4-3", (
        ("J. Pickford", 1),
        ("J. Tarkowski", 6),
        ("J. Branthwaite", 4),
        ("V. Mykolenko", 16),
        ("K. Dewsbury-Hall", 8),
        ("H. Armstrong", 45),
        ("J. Garner", 37),
        ("M. Röhl", 34),
        ("T. Barry", 11),
        ("T. George", 19),
        ("B. Johnson", 22),
    )),
    "FUL": Club("FUL", "Fulham", "FUL", "#EEEEEE", "3-6-1", (
        ("B. Leno", 2),
        ("C. Bassey", 3),
        ("A. Robinson", 33),
        ("T. Castagne", 21),
        ("J. King", 24),
        ("A. Iwobi", 17),
        ("O. Bobb", 14),
        ("S. Berge", 16),
        ("S. Charles", 19),
        ("C. Palacios", 8),
        ("G. García", 7),
    )),
    "HUL": Club("HUL", "Hull City", "HUL", "#F5A623", "5-3-2", (
        ("K. Tzolakis", 19),
        ("L. Coyle", 2),
        ("J. Egan", 15),
        ("S. Ajayi", 6),
        ("N. Mendy", 32),
        ("R. Giles", 3),
        ("R. Slater", 27),
        ("E. Stroud", 21),
        ("M. Crooks", 25),
        ("O. McBurnie", 9),
        ("M. Belloumi", 10),
    )),
    "IPS": Club("IPS", "Ipswich Town", "IPS", "#3A64A3", "4-3-3", (
        ("K. Scherpen", 37),
        ("J. Greaves", 24),
        ("I. Diop", 6),
        ("D. O'Shea", 26),
        ("L. Davis", 3),
        ("J. Enciso", 10),
        ("S. Lukić", 23),
        ("E. Palacios", 25),
        ("A. Fatawu", 7),
        ("Emersonn", 19),
        ("D. Maeda", 38),
    )),
    "LEE": Club("LEE", "Leeds United", "LEE", "#DCE3FF", "6-2-2", (
        ("J. Trafford", 1),
        ("J. Bogle", 2),
        ("J. Justin", 24),
        ("T. Muharemović", 5),
        ("E. Ampadu", 4),
        ("N. Elvedi", 30),
        ("G. Gudmundsson", 3),
        ("A. Stach", 18),
        ("A. Tanaka", 22),
        ("D. Calvert-Lewin", 9),
        ("N. Okafor", 19),
    )),
    "LIV": Club("LIV", "Liverpool", "LIV", "#C8102E", "4-3-3", (
        ("Alisson", 1),
        ("R. Araújo", 33),
        ("V. van Dijk", 4),
        ("J. Jacquet", 5),
        ("M. Kerkez", 6),
        ("D. Szoboszlai", 8),
        ("F. Wirtz", 7),
        ("A. Mac Allister", 10),
        ("A. Isak", 9),
        ("C. Gakpo", 18),
        ("V. Muñoz", 23),
    )),
    "MCI": Club("MCI", "Manchester City", "MCI", "#6CABDD", "4-4-2", (
        ("G. Donnarumma", 1),
        ("A. Khusanov", 45),
        ("R. Dias", 3),
        ("M. Guéhi", 6),
        ("J. Gvardiol", 24),
        ("R. Cherki", 10),
        ("E. Anderson", 5),
        ("E. Fernández", 17),
        ("P. Foden", 47),
        ("A. Semenyo", 42),
        ("E. Haaland", 9),
    )),
    "MUN": Club("MUN", "Manchester United", "MUN", "#DA020E", "4-3-3", (
        ("S. Lammens", 1),
        ("D. Dalot", 2),
        ("H. Maguire", 5),
        ("L. Martínez", 6),
        ("L. Shaw", 23),
        ("B. Fernandes", 8),
        ("Y. Tielemans", 18),
        ("K. Mainoo", 37),
        ("B. Mbeumo", 19),
        ("M. Cunha", 10),
        ("M. Rashford", 9),
    )),
    "NEW": Club("NEW", "Newcastle United", "NEW", "#D0D3D9", "4-3-3", (
        ("L. Horníček", 21),
        ("A. Dedić", 37),
        ("M. Thiaw", 12),
        ("S. Botman", 4),
        ("L. Hall", 3),
        ("J. Willock", 28),
        ("L. Miley", 67),
        ("N. González", 6),
        ("H. Barnes", 11),
        ("Y. Wissa", 9),
        ("A. Elanga", 19),
    )),
    "NFO": Club("NFO", "Nottingham Forest", "NFO", "#DD0000", "5-3-2", (
        ("M. Sels", 26),
        ("O. Aina", 34),
        ("N. Milenković", 31),
        ("Murillo", 5),
        ("J. Cunha", 23),
        ("N. Williams", 3),
        ("M. Gibbs-White", 10),
        ("J. McAtee", 24),
        ("X. Schlager", 21),
        ("D. Ndoye", 14),
        ("L. Delap", 19),
    )),
    "SUN": Club("SUN", "Sunderland", "SUN", "#EB172B", "5-3-2", (
        ("R. Roefs", 22),
        ("T. Meunier", 12),
        ("D. Ballard", 5),
        ("K. Danso", 4),
        ("N. Mukiele", 20),
        ("R. Mandava", 17),
        ("G. Xhaka", 34),
        ("E. Le Fée", 28),
        ("N. Sadiki", 27),
        ("B. Brobbey", 9),
        ("N. Angulo", 10),
    )),
    "TOT": Club("TOT", "Tottenham Hotspur", "TOT", "#22336B", "4-3-3", (
        ("A. Kinský", 31),
        ("A. Gray", 14),
        ("J. van Hecke", 6),
        ("M. van de Ven", 37),
        ("A. Robertson", 3),
        ("S. Tonali", 16),
        ("R. Bentancur", 30),
        ("M. Fernandes", 18),
        ("O. Marmoush", 22),
        ("M. Tel", 11),
        ("Sávio", 17),
    )),
}

CLUB_ORDER = [
    "ARS", "AVL", "BOU", "BRE", "BHA", "CHE", "COV", "CRY", "EVE", "FUL",
    "HUL", "IPS", "LEE", "LIV", "MCI", "MUN", "NEW", "NFO", "SUN", "TOT",
]

VENUES: dict[str, str] = {
    "ARS": "Emirates Stadium",
    "AVL": "Villa Park",
    "BOU": "Vitality Stadium",
    "BRE": "Gtech Community Stadium",
    "BHA": "American Express Stadium",
    "CHE": "Stamford Bridge",
    "COV": "Coventry Building Society Arena",
    "CRY": "Selhurst Park",
    "EVE": "Hill Dickinson Stadium",
    "FUL": "Craven Cottage",
    "HUL": "MKM Stadium",
    "IPS": "Portman Road",
    "LEE": "Elland Road",
    "LIV": "Anfield",
    "MCI": "Etihad Stadium",
    "MUN": "Old Trafford",
    "NEW": "St James' Park",
    "NFO": "The City Ground",
    "SUN": "Stadium of Light",
    "TOT": "Tottenham Hotspur Stadium",
}


def venue_for(club_id: str | None) -> str:
    return VENUES.get((club_id or DEFAULT_HOME).upper(), "Home Stadium")


def get_club(club_id: str | None) -> Club:
    if club_id and club_id.upper() in PL_CLUBS:
        return PL_CLUBS[club_id.upper()]
    return PL_CLUBS[DEFAULT_HOME]


def list_clubs() -> list[dict]:
    return [
        {
            "id": club.id,
            "name": club.name,
            "short": club.short,
            "color": club.color,
            "formation": club.formation,
        }
        for club in (PL_CLUBS[cid] for cid in CLUB_ORDER)
    ]


def build_team_from_club(club_id: str | None, team_id: str, attack_dir: int) -> Team:
    return build_team(team_id, get_club(club_id), attack_dir)


def home_team(club_id: str | None = None) -> Team:
    return build_team_from_club(club_id or DEFAULT_HOME, "HOME", 1)


def away_team(club_id: str | None = None) -> Team:
    return build_team_from_club(club_id or DEFAULT_AWAY, "AWAY", -1)
