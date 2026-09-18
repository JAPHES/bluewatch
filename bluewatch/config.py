"""Adjustable operational thresholds for the rule-based MVP."""
from decimal import Decimal
AUTHORIZED_SITE_REVIEW_RADIUS_KM = Decimal("0.50")
DUPLICATE_DISTANCE_KM = Decimal("0.30")
DUPLICATE_WINDOW_DAYS = 30
NEARBY_REPORT_DISTANCE_KM = Decimal("0.50")
RISK_THRESHOLDS = {"critical": 70, "high": 45, "moderate": 20}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
RATE_LIMIT_REPORTS = 5
RATE_LIMIT_WINDOW_SECONDS = 3600
