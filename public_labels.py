from __future__ import annotations

ARCHETYPE_PUBLIC_VALUES: dict[str, str] = {
    "Niewinny": "Przejrzystość",
    "Mędrzec": "Rozsądek",
    "Odkrywca": "Wolność",
    "Buntownik": "Odnowa",
    "Czarodziej": "Wizja",
    "Bohater": "Odwaga",
    "Kochanek": "Relacje",
    "Błazen": "Otwartość",
    "Towarzysz": "Współpraca",
    "Opiekun": "Troska",
    "Władca": "Porządek",
    "Twórca": "Rozwój",
}

ARCHETYPE_PUBLIC_VALUES_WITH_FEMININE: dict[str, str] = {
    **ARCHETYPE_PUBLIC_VALUES,
    "Niewinna": "Przejrzystość",
    "Mędrczyni": "Rozsądek",
    "Odkrywczyni": "Wolność",
    "Buntowniczka": "Odnowa",
    "Czarodziejka": "Wizja",
    "Bohaterka": "Odwaga",
    "Kochanka": "Relacje",
    "Komiczka": "Otwartość",
    "Towarzyszka": "Współpraca",
    "Opiekunka": "Troska",
    "Władczyni": "Porządek",
    "Twórczyni": "Rozwój",
}

FINAL_VALUES_WHEEL_CENTRAL_FIELDS: dict[str, str] = {
    "upper_left": "Bezpieczeństwo i jakość",
    "upper_right": "Jasne zasady i swoboda",
    "lower_left": "Bliskość i wspólnota",
    "lower_right": "Przełom i kierunek",
}

FINAL_VALUES_WHEEL_ARC_LABELS: dict[str, str] = {
    "upper_left": "stabilność / zarządzanie",
    "upper_right": "niezależność / samodzielność",
    "lower_left": "relacje / współdziałanie",
    "lower_right": "zmiana / przywództwo",
}

PREFERENCES_P_LABEL_ORDER: list[str] = [
    "Wolność",
    "Rozsądek",
    "Odnowa",
    "Relacje",
    "Wizja",
    "Współpraca",
    "Otwartość",
    "Porządek",
    "Przejrzystość",
    "Troska",
    "Odwaga",
    "Rozwój",
]

PREFERENCES_P_DISPLAY_BY_INTERNAL_KEY: dict[str, str] = {
    "wolnosc": "Wolność",
    "racjonalnosc": "Rozsądek",
    "odnowa": "Odnowa",
    "relacje": "Relacje",
    "wizja": "Wizja",
    "wspolpraca": "Współpraca",
    "otwartosc": "Otwartość",
    "skutecznosc": "Porządek",
    "przejrzystosc": "Przejrzystość",
    "troska": "Troska",
    "odwaga": "Odwaga",
    "rozwoj": "Rozwój",
}
