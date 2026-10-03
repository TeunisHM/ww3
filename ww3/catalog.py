"""Original faction values preserved by the authoritative DESIGN.md.

Money is measured in trillions of USD. Percentages use fractions internally.
Values missing from the design live in rules.py, not in this source table.
"""

FACTIONS = ("EU", "US", "China", "Russia")
FRONTS = ("Eastern Europe", "Pacific & South China Sea", "Arctic", "South America")
GOVERNMENTS = ("Democratic/pluralistic", "Democratic/oligarchic", "Authoritarian/one-party", "Authoritarian/dictator")
COLORS = {"EU": "#69adff", "US": "#6ed7c1", "China": "#f5b45c", "Russia": "#dc8099"}

SCENARIO = {
    "EU": {
        "name": "European Union", "government": GOVERNMENTS[0],
        "gdp": 20.0, "tax_rate": 0.40, "debt": 16.3, "domestic_share": 0.8,
        "creditor_weight": 0.30, "military": 120.0, "capital": 60.0,
        "relations": {"US": 4.0, "China": 3.0, "Russia": 2.0},
        "traits": ("Home of the chip machine", "Luxury goods"),
        "brief": "Balance internal interests, industrial dependence, and security on the eastern flank.",
    },
    "US": {
        "name": "United States", "government": GOVERNMENTS[1],
        "gdp": 27.2, "tax_rate": 0.25, "debt": 38.0, "domestic_share": 0.8,
        "creditor_weight": 0.41, "military": 400.0,
        "relations": {"EU": 4.0, "China": 2.0, "Russia": 3.0},
        "traits": ("Home of the hyperscalers", "Media dominance"),
        "brief": "Manage substantial debt and political division while maintaining global military reach.",
    },
    "China": {
        "name": "China", "government": GOVERNMENTS[2],
        "gdp": 17.1, "tax_rate": 0.204, "debt": 16.2, "domestic_share": 0.9,
        "creditor_weight": 0.24, "military": 200.0,
        "relations": {"EU": 3.0, "US": 2.0, "Russia": 4.0},
        "traits": ("Factory of the world", "AI superpower"),
        "brief": "Keep citizens content and turn manufacturing capacity into lasting trading relationships.",
    },
    "Russia": {
        "name": "Russia", "government": GOVERNMENTS[3],
        "gdp": 2.0, "tax_rate": 0.26, "debt": 0.45, "domestic_share": 0.9,
        "creditor_weight": 0.05, "military": 200.0,
        "relations": {"EU": 2.0, "US": 3.0, "China": 4.0},
        "traits": ("Resource rich", "Battle hardened"),
        "brief": "Support a large military with a small economy and use resource production to fund recovery.",
    },
}

TRAITS = {
    "EU": (
        "+10% innovation gain. Data-center construction costs −25%.",
        "A trade agreement can share the data-center discount. Luxury exports earn currency from partners’ GDP.",
    ),
    "US": (
        "Compute consumption −20%; this benefit can be offered in trade agreements.",
        "Positive diplomatic actions are 10% stronger; citizen discontent is reduced by 10%.",
    ),
    "China": (
        "+20% productivity; this benefit can be offered in trade agreements.",
        "+10% innovation gain.",
    ),
    "Russia": (
        "+20% energy and mineral production.",
        "Opposing forces are 10% less effective in combat.",
    ),
}
