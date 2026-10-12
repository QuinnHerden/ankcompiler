from app.logic.drivers import deck_family, root_decks


class TestDeckHierarchy:
    @staticmethod
    def test_deck_family_matches_exact_and_subdecks_only():
        names = ["Geo", "Geo::Rivers", "Geo::Rivers::Tier 1", "Geography", "Other"]
        assert deck_family("Geo", names) == [
            "Geo",
            "Geo::Rivers",
            "Geo::Rivers::Tier 1",
        ]

    @staticmethod
    def test_deck_family_without_parent_deck():
        assert deck_family("Geo", ["Geo::A", "Geo::B"]) == ["Geo::A", "Geo::B"]

    @staticmethod
    def test_root_decks():
        names = ["Geo::A", "Geo::B::C", "Geography", "Other"]
        assert root_decks(names) == ["Geo", "Geography", "Other"]
