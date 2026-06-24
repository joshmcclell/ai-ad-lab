"""
risk.py
=======
Money management: position sizing and the daily-loss circuit breaker.

LOT SIZING - how it works and how it stays <= 0.05
--------------------------------------------------
1. Money at risk  = balance * (risk_per_trade_pct / 100).
       e.g. $1,000 balance @ 1%  ->  risk $10 per trade.

2. Loss per 1.00 lot if the stop is hit:
       loss_per_lot = (sl_distance_in_price / tick_size) * tick_value
   where tick_size and tick_value come straight from the broker's symbol
   spec at runtime (so the maths is correct for IC Markets XAUUSD). For the
   offline backtester we fall back to contract_size: for XAUUSD a 1.00 lot is
   100 oz, so a $1.00 move = $100, i.e. loss_per_lot = sl_distance * 100.

3. Raw lot   = money_at_risk / loss_per_lot.

4. Round DOWN to the broker volume step (0.01) so we never risk *more* than
   the target percentage.

5. Clamp into [min_lot, max_lot]. max_lot is the hard 0.05 ceiling:
       lot = min(lot, 0.05)
   No balance, however large, can push the size past 0.05.

6. If the risk-correct lot is below the broker minimum (0.01), the trade is
   skipped rather than silently over-risking - UNLESS you opt into trading the
   minimum lot (see `allow_min_lot_when_undersized`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class SizingResult:
    lot: float                 # final lot size (0 means "do not trade")
    money_at_risk: float       # intended risk in account currency
    loss_per_lot: float        # modelled loss for 1.00 lot at this stop
    capped_by_max_lot: bool    # True if the 0.05 ceiling bound the size
    skipped_reason: Optional[str] = None


def _round_down_to_step(value: float, step: float) -> float:
    """Floor `value` to the nearest multiple of `step` (avoids over-risking)."""
    if step <= 0:
        return value
    return math.floor(value / step + 1e-9) * step


def calculate_lot_size(
    balance: float,
    sl_distance_price: float,
    risk_cfg,
    *,
    tick_size: Optional[float] = None,
    tick_value: Optional[float] = None,
    contract_size: float = 100.0,
    allow_min_lot_when_undersized: bool = False,
) -> SizingResult:
    """
    Compute a risk-based lot size that respects risk %, the stop distance and
    the hard 0.05 lot ceiling.

    Pass `tick_size`/`tick_value` from mt5.symbol_info() for live trading; omit
    them to use the contract_size approximation (backtesting).
    """
    if balance <= 0:
        return SizingResult(0.0, 0.0, 0.0, False, "non-positive balance")
    if sl_distance_price <= 0:
        return SizingResult(0.0, 0.0, 0.0, False, "non-positive stop distance")

    money_at_risk = balance * (risk_cfg.risk_per_trade_pct / 100.0)

    # Loss incurred by 1.00 lot if price moves `sl_distance_price` against us.
    if tick_size and tick_value and tick_size > 0:
        loss_per_lot = (sl_distance_price / tick_size) * tick_value
    else:
        # Fallback: XAUUSD 1.00 lot = 100 oz -> $1 move = $100.
        loss_per_lot = sl_distance_price * contract_size

    if loss_per_lot <= 0:
        return SizingResult(0.0, money_at_risk, 0.0, False, "invalid loss-per-lot")

    raw_lot = money_at_risk / loss_per_lot

    # Floor to the broker step so realised risk <= target risk.
    lot = _round_down_to_step(raw_lot, risk_cfg.lot_step)

    # Hard ceiling - the 0.05 rule. This is applied unconditionally.
    capped = False
    if lot > risk_cfg.max_lot:
        lot = risk_cfg.max_lot
        capped = True

    # Below the broker minimum?
    if lot < risk_cfg.min_lot:
        if allow_min_lot_when_undersized:
            # Trade the minimum, accepting that realised risk slightly exceeds
            # the target percentage. Opt-in only.
            return SizingResult(
                lot=risk_cfg.min_lot,
                money_at_risk=money_at_risk,
                loss_per_lot=loss_per_lot,
                capped_by_max_lot=False,
                skipped_reason=None,
            )
        return SizingResult(
            lot=0.0,
            money_at_risk=money_at_risk,
            loss_per_lot=loss_per_lot,
            capped_by_max_lot=False,
            skipped_reason=(f"risk-correct lot {raw_lot:.4f} below min "
                            f"{risk_cfg.min_lot}; skipping to avoid over-risk"),
        )

    return SizingResult(
        lot=round(lot, 2),
        money_at_risk=money_at_risk,
        loss_per_lot=loss_per_lot,
        capped_by_max_lot=capped,
        skipped_reason=None,
    )


def fixed_lot_size(
    fixed_lot: float,
    sl_distance_price: float,
    *,
    tick_size: Optional[float] = None,
    tick_value: Optional[float] = None,
    contract_size: float = 100.0,
    volume_min: float = 0.01,
    volume_max: float = 100.0,
    lot_step: float = 0.01,
) -> SizingResult:
    """
    Trade an exact fixed lot every time, ignoring risk-based sizing and the
    0.05 soft cap. The value is still floored to the broker volume step and
    clamped to the broker's own min/max volume so the order is always valid.
    money_at_risk is reported as the ACTUAL risk for transparency/logging.
    """
    lot = _round_down_to_step(fixed_lot, lot_step)
    lot = max(volume_min, min(lot, volume_max))

    if tick_size and tick_value and tick_size > 0:
        loss_per_lot = (sl_distance_price / tick_size) * tick_value
    else:
        loss_per_lot = sl_distance_price * contract_size

    return SizingResult(
        lot=round(lot, 2),
        money_at_risk=lot * loss_per_lot,   # the real risk, not a target
        loss_per_lot=loss_per_lot,
        capped_by_max_lot=False,
        skipped_reason=None,
    )


# --------------------------------------------------------------------------- #
# Daily-loss circuit breaker                                                   #
# --------------------------------------------------------------------------- #
class DailyLossGuard:
    """
    Tracks realised P/L for the current day and blocks new trades once the
    max daily loss (% of the day's starting balance) is breached.

    `start_balance` should be set to the account balance at the first trade of
    the day; call `reset()` at session start / rollover.
    """

    def __init__(self, risk_cfg):
        self._cfg = risk_cfg
        self._day: Optional[date] = None
        self._start_balance: float = 0.0
        self._realised_pnl: float = 0.0

    def reset(self, start_balance: float, today: Optional[date] = None) -> None:
        self._day = today or date.today()
        self._start_balance = start_balance
        self._realised_pnl = 0.0

    def _roll_if_new_day(self, balance: float, today: date) -> None:
        if self._day != today:
            self.reset(balance, today)

    def register_closed_trade(self, pnl: float) -> None:
        """Record the realised P/L (account currency) of a closed trade."""
        self._realised_pnl += pnl

    @property
    def realised_pnl(self) -> float:
        return self._realised_pnl

    def loss_limit(self) -> float:
        return self._start_balance * (self._cfg.max_daily_loss_pct / 100.0)

    def is_blocked(self, balance: float, today: Optional[date] = None) -> bool:
        """True if today's losses have hit/exceeded the max daily loss."""
        today = today or date.today()
        self._roll_if_new_day(balance, today)
        if self._start_balance <= 0:
            self._start_balance = balance
        return self._realised_pnl <= -self.loss_limit()
