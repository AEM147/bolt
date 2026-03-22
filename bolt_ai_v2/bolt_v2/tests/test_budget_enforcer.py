"""
Tests for the BudgetEnforcer module.
Verifies that hard stops and soft alerts fire at correct thresholds.
"""

import pytest
from unittest.mock import patch, MagicMock
from budget_enforcer import BudgetEnforcer, BudgetExceededError


class TestBudgetEnforcerDefaults:
    """Test that default limits are applied when config has no overrides."""

    def test_default_monthly_hard_stop(self, sample_config):
        enforcer = BudgetEnforcer(sample_config)
        assert enforcer._limits["monthly_budget_hard_stop"] == 20.0

    def test_default_daily_hard_stop(self, sample_config):
        enforcer = BudgetEnforcer(sample_config)
        assert enforcer._limits["daily_budget_hard_stop"] == 5.0

    def test_config_overrides_defaults(self, sample_config):
        sample_config["cost_tracking"]["monthly_budget_hard_stop"] = 50.0
        enforcer = BudgetEnforcer(sample_config)
        assert enforcer._limits["monthly_budget_hard_stop"] == 50.0


class TestBudgetEnforcerChecks:
    """Test that check_or_raise correctly blocks/allows based on spending."""

    def test_under_budget_does_not_raise(self, sample_config):
        enforcer = BudgetEnforcer(sample_config)
        # Mock cost tracker to return low spending
        mock_tracker = MagicMock()
        mock_tracker.get_monthly_summary.return_value = {
            "total_cost": 1.0, "videos": 1
        }
        mock_tracker.get_daily_summary.return_value = {"total_cost": 0.5}
        mock_tracker.get_current_video_cost.return_value = 0.10
        mock_tracker.get_total_summary.return_value = {
            "total_spent": 1.0, "total_videos": 1, "avg_cost_per_video": 0.10
        }
        enforcer._tracker = mock_tracker

        # Should not raise
        enforcer.check_or_raise("video")

    def test_monthly_hard_stop_raises(self, sample_config):
        sample_config["cost_tracking"]["monthly_budget_hard_stop"] = 10.0
        enforcer = BudgetEnforcer(sample_config)

        mock_tracker = MagicMock()
        mock_tracker.get_monthly_summary.return_value = {
            "total_cost": 15.0, "videos": 10
        }
        mock_tracker.get_daily_summary.return_value = {"total_cost": 0.5}
        mock_tracker.get_current_video_cost.return_value = 0.10
        enforcer._tracker = mock_tracker

        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.check_or_raise("video")
        assert exc_info.value.limit_type == "monthly"
        assert exc_info.value.spent == 15.0

    def test_daily_hard_stop_raises(self, sample_config):
        sample_config["cost_tracking"]["daily_budget_hard_stop"] = 2.0
        enforcer = BudgetEnforcer(sample_config)

        mock_tracker = MagicMock()
        mock_tracker.get_monthly_summary.return_value = {
            "total_cost": 5.0, "videos": 3
        }
        mock_tracker.get_daily_summary.return_value = {"total_cost": 3.0}
        mock_tracker.get_current_video_cost.return_value = 0.10
        enforcer._tracker = mock_tracker

        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.check_or_raise("video")
        assert exc_info.value.limit_type == "daily"


class TestBudgetExceededError:
    """Test the custom exception attributes."""

    def test_error_attributes(self):
        err = BudgetExceededError(
            "Monthly budget exceeded", limit_type="monthly", spent=25.0, limit=20.0
        )
        assert err.limit_type == "monthly"
        assert err.spent == 25.0
        assert err.limit == 20.0
        assert "Monthly budget exceeded" in str(err)
