from __future__ import annotations

from app.models import Insight

LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "pt": "Português",
    "ar": "العربية",
    "zu": "isiZulu",
}

_GOAL_LINE = {
    "en": "{player} scores for {team} in the {minute}' minute. The move carried {xg} expected goals across {passes} passes; the decisive factor was {top_factor}.",
    "es": "{player} marca para {team} en el minuto {minute}. La jugada valía {xg} de goles esperados con {passes} pases; el factor decisivo fue {top_factor}.",
    "fr": "{player} marque pour {team} à la {minute}e minute. L'action valait {xg} buts attendus avec {passes} passes ; le facteur décisif était {top_factor}.",
    "pt": "{player} marca para {team} aos {minute} minutos. A jogada valeu {xg} golos esperados com {passes} passes; o fator decisivo foi {top_factor}.",
    "ar": "يسجل {player} لصالح {team} في الدقيقة {minute}. بلغت الهجمة {xg} من الأهداف المتوقعة عبر {passes} تمريرة، وكان العامل الحاسم {top_factor}.",
    "zu": "U-{player} ushaya igoli elenzelwe i-{team} ngomzuzu wama-{minute}. Ithuba elenzelwe lalilingana no-{xg} ngemiphumela engu-{passes}; isizathu esibalulekile kwakungu-{top_factor}.",
}

_CHANCE_LINE = {
    "en": "{player} ({team}) creates a {xg} expected-goals chance in the {minute}' minute, built from {passes} passes; {top_factor} was key.",
    "es": "{player} ({team}) genera una ocasión de {xg} goles esperados en el minuto {minute}, tras {passes} pases; {top_factor} fue clave.",
    "fr": "{player} ({team}) se crée une occasion de {xg} buts attendus à la {minute}e minute, après {passes} passes ; {top_factor} fut déterminant.",
    "pt": "{player} ({team}) cria uma ocasião de {xg} golos esperados aos {minute} minutos, após {passes} passes; {top_factor} foi decisivo.",
    "ar": "يصنع {player} ({team}) فرصة بقيمة {xg} أهداف متوقعة في الدقيقة {minute} عبر {passes} تمريرة، وكان {top_factor} أساسياً.",
    "zu": "U-{player} ({team}) udala ithuba elingu-{xg} lokushaya igoli ngomzuzu {minute}, ngemuva kwe-{passes} yamaphasé; u-{top_factor} ubalulekile.",
}

_GOAL_WORD = {"en": "Goal", "es": "Gol", "fr": "But", "pt": "Golo", "ar": "هدف", "zu": "Igoli"}
_CHANCE_WORD = {"en": "Big chance", "es": "Gran ocasión", "fr": "Grande occasion", "pt": "Grande ocasião", "ar": "فرصة كبيرة", "zu": "Ithuba elikhulu"}

_PATTERN_PHRASE = {
    "high_press": {
        "en": "pressing high and forcing turnovers",
        "es": "presionando arriba y forzando pérdidas",
        "fr": "pressing haut et récupérations forcées",
        "pt": "pressão alta e recuperações forçadas",
        "ar": "الضغط العالي وإجبار الخصم على فقدان الكرة",
        "zu": "ukucindezela phezulu nokuphuca ibhola",
    },
    "low_block": {
        "en": "defending in a deep low block",
        "es": "defendiendo en un bloque bajo",
        "fr": "défense en bloc bas",
        "pt": "a defender num bloco baixo",
        "ar": "الدفاع في كتلة منخفضة",
        "zu": "ukuvikela ngendlela ephansi",
    },
    "sustained_pressure": {
        "en": "building sustained pressure",
        "es": "generando presión sostenida",
        "fr": "installant une pression durable",
        "pt": "a construir pressão sustentada",
        "ar": "بناء ضغط متواصل",
        "zu": "ukwakha ingcindezi eqhubekayo",
    },
    "set_piece_threat": {
        "en": "threatening from set pieces",
        "es": "siendo peligroso a balón parado",
        "fr": "dangereux sur coups de pied arrêtés",
        "pt": "a ameaçar de bola parada",
        "ar": "تشكيل خطورة من الكرات الثابتة",
        "zu": "ukusongela ngamabhola amile",
    },
    "counter_attack": {
        "en": "threatening in transition",
        "es": "siendo peligroso en transición",
        "fr": "dangereux en transition",
        "pt": "a ameaçar em transição",
        "ar": "تشكيل خطورة في التحولات",
        "zu": "ukusongela ngesikhathi sokushintsha",
    },
    "left_overload": {
        "en": "overloading the left flank",
        "es": "sobrecargando el carril izquierdo",
        "fr": "surchargeant le couloir gauche",
        "pt": "sobrecarregando o corredor esquerdo",
        "ar": "التحميل الزائد على الجهة اليسرى",
        "zu": "ukugcwala kwesokunxele",
    },
    "right_overload": {
        "en": "overloading the right flank",
        "es": "sobrecargando el carril derecho",
        "fr": "surchargeant le couloir droit",
        "pt": "sobrecarregando o corredor direito",
        "ar": "التحميل الزائد على الجهة اليمنى",
        "zu": "ukugcwala kwesokudla",
    },
}

_GENERIC_LINE = {
    "en": "{team} are {phrase} (strength {strength}).",
    "es": "{team} está {phrase} (intensidad {strength}).",
    "fr": "{team} est {phrase} (intensité {strength}).",
    "pt": "{team} está {phrase} (intensidade {strength}).",
    "ar": "{team} {phrase} (القوة {strength}).",
    "zu": "{team} {phrase} (amandla {strength}).",
}

_FACTOR_LABELS = {
    "Build-up": {"es": "Construcción", "fr": "Construction", "pt": "Construção", "ar": "البناء الهجومي", "zu": "Ukwakha"},
    "Ball recovery": {"es": "Recuperación", "fr": "Récupération", "pt": "Recuperação", "ar": "استعادة الكرة", "zu": "Ukuthola ibhola"},
    "Shot quality": {"es": "Calidad del remate", "fr": "Qualité de frappe", "pt": "Qualidade do remate", "ar": "جودة التسديدة", "zu": "Ikhwalithi yokushaya"},
    "Momentum": {"es": "Momento", "fr": "Dynamique", "pt": "Momento", "ar": "الزخم", "zu": "Umfutho"},
    "Set piece": {"es": "Balón parado", "fr": "Coup de pied arrêté", "pt": "Bola parada", "ar": "كرة ثابتة", "zu": "Ibhola elimile"},
    "Opponent under pressure": {"es": "Rival bajo presión", "fr": "Adversaire sous pression", "pt": "Adversário sob pressão", "ar": "الخصم تحت الضغط", "zu": "Iqembu eliphikisayo licindezelwe"},
    "Individual finish": {"es": "Definición individual", "fr": "Finition individuelle", "pt": "Finalização individual", "ar": "اللمسة الفردية", "zu": "Ukuqeda komdlali"},
    "High turnovers": {"es": "Pérdidas arriba", "fr": "Récupérations hautes", "pt": "Recuperações altas", "ar": "استرجاعات عالية", "zu": "Ukuthola phezulu"},
    "Pressing volume": {"es": "Volumen de presión", "fr": "Volume de pressing", "pt": "Volume de pressão", "ar": "حجم الضغط", "zu": "Umthamo wokucindezela"},
}


def factor_label(name: str, lang: str) -> str:
    if lang == "en":
        return name
    return _FACTOR_LABELS.get(name, {}).get(lang, name)


def render_title(insight: Insight, lang: str) -> str:
    if insight.kind == "goal_explanation":
        word = _GOAL_WORD.get(lang, "Goal")
        return f"{word} — {insight.facts.get('team', '')} ({insight.facts.get('minute', insight.minute)}')"
    if insight.kind == "chance_explanation":
        word = _CHANCE_WORD.get(lang, "Big chance")
        return f"{word} — {insight.facts.get('team', '')} ({insight.facts.get('minute', insight.minute)}')"
    key = str(insight.facts.get("pattern_key", ""))
    phrase = _PATTERN_PHRASE.get(key, {}).get(lang)
    team = insight.facts.get("team", "")
    if phrase:
        return f"{team}: {phrase}"
    return insight.title


def render_narrative(insight: Insight, lang: str) -> str:
    if insight.kind in ("goal_explanation", "chance_explanation"):
        table = _GOAL_LINE if insight.kind == "goal_explanation" else _CHANCE_LINE
        template = table.get(lang, table["en"])
        facts = dict(insight.facts)
        facts["top_factor"] = factor_label(str(facts.get("top_factor", "")), lang)
        return template.format(**facts)
    key = str(insight.facts.get("pattern_key", ""))
    phrase = _PATTERN_PHRASE.get(key, {}).get(lang)
    if phrase:
        template = _GENERIC_LINE.get(lang, _GENERIC_LINE["en"])
        return template.format(
            team=insight.facts.get("team", ""),
            phrase=phrase,
            strength=insight.facts.get("strength", ""),
        )
    return insight.claim


def render(insight: Insight) -> dict[str, str]:
    out: dict[str, str] = {}
    for code in LANGUAGES:
        out[code] = render_narrative(insight, code)
    return out


_RECAP_PHRASES = {
    "en": {
        "win": "{winner} win {wg}-{lg}",
        "draw": "{home} and {away} draw {hg}-{ag}",
        "full_time": "Full-time: {result} at {venue}.",
        "goals": "Goals: {scorers}.",
        "tactical": "Tactical story: {patterns}.",
        "closing": "All key moments carry an evidence-backed explanation with weighted factors and a counterfactual, generated in real time.",
    },
    "es": {
        "win": "{winner} gana {wg}-{lg}",
        "draw": "{home} y {away} empatan {hg}-{ag}",
        "full_time": "Final: {result} en {venue}.",
        "goals": "Goles: {scorers}.",
        "tactical": "Historia táctica: {patterns}.",
        "closing": "Cada momento clave incluye una explicación respaldada por evidencia, con factores ponderados y un contrafactual, generados en tiempo real.",
    },
    "fr": {
        "win": "{winner} s'impose {wg}-{lg}",
        "draw": "{home} et {away} font match nul {hg}-{ag}",
        "full_time": "Score final : {result} à {venue}.",
        "goals": "Buts : {scorers}.",
        "tactical": "Lecture tactique : {patterns}.",
        "closing": "Chaque moment clé s'accompagne d'une explication fondée sur des preuves, avec des facteurs pondérés et un contrefactuel, générés en temps réel.",
    },
    "pt": {
        "win": "{winner} vence {wg}-{lg}",
        "draw": "{home} e {away} empatam {hg}-{ag}",
        "full_time": "Resultado final: {result} em {venue}.",
        "goals": "Golos: {scorers}.",
        "tactical": "Leitura tática: {patterns}.",
        "closing": "Todos os momentos-chave têm uma explicação baseada em evidências, com fatores ponderados e um contrafactual, gerados em tempo real.",
    },
    "ar": {
        "win": "{winner} يفوز {wg}-{lg}",
        "draw": "{home} و{away} يتعادلان {hg}-{ag}",
        "full_time": "النتيجة النهائية: {result} على ملعب {venue}.",
        "goals": "الأهداف: {scorers}.",
        "tactical": "القصة التكتيكية: {patterns}.",
        "closing": "كل لحظة رئيسية مرفقة بشرح قائم على الأدلة مع عوامل مرجّحة وسيناريو مضاد، ويُولَّد في الوقت الحقيقي.",
    },
    "zu": {
        "win": "{winner} iyanqoba {wg}-{lg}",
        "draw": "{home} ne-{away} bayalingana {hg}-{ag}",
        "full_time": "Isiphetho: {result} e-{venue}.",
        "goals": "Amagoli: {scorers}.",
        "tactical": "Indaba yethekhi: {patterns}.",
        "closing": "Zonke izikhathi ezibalulekile zinechaza elisekelwe ebufakazini, elinama-factor alinganiselwe kanye ne-counterfactual, ezikhiqizwa ngesikhathi sangempela.",
    },
}


def match_recap(
    meta,
    home,
    away,
    goal_insights: list[dict],
    patterns: list[dict],
    lang: str = "en",
) -> str:
    phrases = _RECAP_PHRASES.get(lang, _RECAP_PHRASES["en"])
    hg = home.get("goals", 0) if isinstance(home, dict) else home.goals
    ag = away.get("goals", 0) if isinstance(away, dict) else away.goals
    hname = meta.home.name if hasattr(meta, "home") else meta["home"]["name"]
    aname = meta.away.name if hasattr(meta, "away") else meta["away"]["name"]
    venue = getattr(meta, "venue", "the stadium")

    if hg > ag:
        result = phrases["win"].format(winner=hname, wg=hg, lg=ag)
    elif ag > hg:
        result = phrases["win"].format(winner=aname, wg=ag, lg=hg)
    else:
        result = phrases["draw"].format(home=hname, away=aname, hg=hg, ag=ag)

    scorers = []
    for g in goal_insights:
        f = g.get("facts", {})
        scorers.append(f"{f.get('player', 'a forward')} ({f.get('minute', '?')}', {f.get('team', '')})")

    lines = [phrases["full_time"].format(result=result, venue=venue)]
    if scorers:
        lines.append(phrases["goals"].format(scorers="; ".join(scorers)))
    if patterns:
        labels = []
        for p in patterns[:4]:
            label = p.get("title") if isinstance(p, dict) else p.title
            if label not in labels:
                labels.append(label)
        lines.append(phrases["tactical"].format(patterns="; ".join(labels)))
    lines.append(phrases["closing"])
    return " ".join(lines)
