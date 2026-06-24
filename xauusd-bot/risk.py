"""Risk management: position sizing, broker limits, margin checks, daily loss cap.

The golden rule enforced here: never risk more than RISK_PER_TRADE (default 1%)
of the account balance on a single trade. Lot size is derived from the *actual*
distance to the stop, using IC Markets' per-symbol tick value so the maths is
correct regardless of contract size or account currency.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from config import CONFIG
from logger import get_logger

log = get_logger()


@dataclass
class LotResult:
    volume: float
    ok: bool
    reason: str


def calculate_lot(balance: float, entry: float, stop_loss: float, symbol_info) -> LotResult:
    """Return the lot size that risks RISK_PER_TRADE of `balance`, clamped to broker limits."""
    sl_distance = abs(entry - stop_loss)
    if sl_distance <= 0:
        return LotResult(0.0, False, "stop distance is zero")

    tick_value = symbol_info.trade_tick_value   # account-currency value of one tick per 1.0 lot
    tick_size = symbol_info.trade_tick_size      # price increment of one tick
    if tick_value <= 0 or tick_size <= 0:
        return LotResult(0.0, False, "invalid tick value/size from broker")

    money_per_price_per_lot = tick_value / tick_size
    risk_amount = balance * CONFIG.risk_per_trade

    raw_lots = risk_amount / (sl_distance * money_per_price_per_lot)

    # Clamp to the broker's min/max and snap DOWN to the volume step.
    vmin = symbol_info.volume_min
    vmax = symbol_info.volume_max
    vstep = symbol_info.volume_step or 0.01

    stepped = (int(raw_lots / vstep)) * vstep
    stepped = round(stepped, 8)

    if stepped < vmin:
        # The 1% risk can't even cover one minimum lot — refuse rather than over-risk.
        min_risk = vmin * sl_distance * money_per_price_per_lot
        return LotResult(
            0.0, False,
            f"min lot {vmin} would risk {min_risk:.2f} > allowed {risk_amount:.2f} "
            f"(1% of {balance:.2f}). Skipping trade.",
        )

    volume = min(stepped, vmax)
    actual_risk = volume * sl_distance * money_per_price_per_lot
    log.info(
        "Lot sizing: risk_amount=%.2f sl_dist=%.3f -> %.2f lots (actual risk %.2f)",
        risk_amount, sl_distance, volume, actual_risk,
    )
    return LotResult(volume, True, "ok")


def fixed_lot(volume: float, symbol_info) -> LotResult:
    """Clamp a user-specified fixed lot size to the broker's min/step/max."""
    vmin = symbol_info.volume_min
    vmax = symbol_info.volume_max
    vstep = symbol_info.volume_step or 0.01

    stepped = round((round(volume / vstep)) * vstep, 8)
    clamped = max(vmin, min(vmax, stepped))
    if clamped != volume:
        log.info("Fixed lot %.2f adjusted to broker limits -> %.2f", volume, clamped)
    return LotResult(clamped, True, f"fixed lot {clamped}")


def margin_ok(side: str, volume: float, entry: float, symbol: str, free_margin: float) -> bool:
    """Confirm the account has enough free margin for the order (respects leverage)."""
    import MetaTrader5 as mt5  # lazy: offline backtesting needs no MT5 install

    order_type = mt5.ORDER_TYPE_BUY if side == "long" else mt5.ORDER_TYPE_SELL
    required = mt5.order_calc_margin(order_type, symbol, volume, entry)
    if required is None:
        log.warning("order_calc_margin returned None; allowing order but watch margin.")
        return True
    if required > free_margin:
        log.warning("Insufficient margin: need %.2f, free %.2f. Skipping.", required, free_margin)
        return False
    return True


class DailyLossGuard:
    """Tracks realised P&L for the day and trips once the loss limit is reached.

    Loss is measured against the account balance recorded at the first check of
    each calendar day (server/local date). Once tripped, no new trades open until
    the date rolls over.
    """

    def __init__(self) -> None:
        self._day: date | None = None
        self._day_start_balance: float = 0.0
        self._tripped = False

    def update(self, balance: float) -> None:
        today = date.today()
        if self._day != today:
            self._day = today
            self._day_start_balance = balance
            self._tripped = False
            log.info("New trading day. Start balance = %.2f. Loss limit = %.1f%%.",
                     balance, CONFIG.daily_loss_limit * 100)

    def check(self, balance: float) -> bool:
        """Return True if trading is allowed, False if the daily loss limit is hit."""
        self.update(balance)
        if self._tripped:
            return False
        loss = self._day_start_balance - balance
        limit = self._day_start_balance * CONFIG.daily_loss_limit
        if loss >= limit > 0:
            self._tripped = True
            log.warning(
                "DAILY LOSS LIMIT HIT: down %.2f (limit %.2f). Pausing new trades until tomorrow.",
                loss, limit,
            )
            return False
        return True

    @property
    def tripped(self) -> bool:
        return self._tripped
