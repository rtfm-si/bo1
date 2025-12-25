"""Tests for pagination utility functions."""

from backend.api.utils.pagination import make_page_pagination_fields, make_pagination_fields


class TestMakePaginationFields:
    """Tests for make_pagination_fields()."""

    def test_has_more_true_when_more_items_exist(self):
        """When offset + limit < total, has_more should be True."""
        result = make_pagination_fields(total=100, limit=10, offset=0)

        assert result["has_more"] is True
        assert result["next_offset"] == 10
        assert result["total"] == 100
        assert result["limit"] == 10
        assert result["offset"] == 0

    def test_has_more_false_when_on_last_page(self):
        """When offset + limit >= total, has_more should be False."""
        result = make_pagination_fields(total=100, limit=10, offset=90)

        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_has_more_false_when_exact_boundary(self):
        """When offset + limit == total exactly, has_more should be False."""
        result = make_pagination_fields(total=100, limit=10, offset=90)

        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_next_offset_calculation(self):
        """next_offset should be offset + limit when has_more is True."""
        result = make_pagination_fields(total=50, limit=10, offset=20)

        assert result["has_more"] is True
        assert result["next_offset"] == 30

    def test_next_offset_none_when_no_more_pages(self):
        """next_offset should be None when has_more is False."""
        result = make_pagination_fields(total=25, limit=10, offset=20)

        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_empty_results(self):
        """When total is 0, has_more should be False."""
        result = make_pagination_fields(total=0, limit=10, offset=0)

        assert result["has_more"] is False
        assert result["next_offset"] is None
        assert result["total"] == 0

    def test_single_page(self):
        """When all items fit on one page, has_more should be False."""
        result = make_pagination_fields(total=5, limit=10, offset=0)

        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_middle_of_large_dataset(self):
        """Test pagination in the middle of a large dataset."""
        result = make_pagination_fields(total=1000, limit=25, offset=500)

        assert result["has_more"] is True
        assert result["next_offset"] == 525
        assert result["total"] == 1000
        assert result["limit"] == 25
        assert result["offset"] == 500


class TestMakePagePaginationFields:
    """Tests for make_page_pagination_fields() which converts page/per_page to offset-based."""

    def test_converts_page_1_to_offset_0(self):
        """Page 1 should map to offset 0."""
        result = make_page_pagination_fields(total=100, page=1, per_page=10)

        assert result["offset"] == 0
        assert result["limit"] == 10
        assert result["has_more"] is True
        assert result["next_offset"] == 10

    def test_converts_page_2_to_offset(self):
        """Page 2 with per_page=10 should map to offset 10."""
        result = make_page_pagination_fields(total=100, page=2, per_page=10)

        assert result["offset"] == 10
        assert result["limit"] == 10
        assert result["has_more"] is True
        assert result["next_offset"] == 20

    def test_last_page(self):
        """Last page should have has_more=False."""
        result = make_page_pagination_fields(total=25, page=3, per_page=10)

        assert result["offset"] == 20
        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_custom_per_page(self):
        """Test with custom per_page value."""
        result = make_page_pagination_fields(total=50, page=1, per_page=25)

        assert result["limit"] == 25
        assert result["offset"] == 0
        assert result["has_more"] is True
        assert result["next_offset"] == 25

    def test_page_beyond_total(self):
        """Page beyond available data should have has_more=False."""
        result = make_page_pagination_fields(total=10, page=5, per_page=10)

        assert result["offset"] == 40
        assert result["has_more"] is False
        assert result["next_offset"] is None
