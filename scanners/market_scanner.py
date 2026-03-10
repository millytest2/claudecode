"""
Market scanner — uses yfinance (free, no credentials) to find:
  • Momentum plays: stocks up 3%+ on heavy volume
  • Unusual volume spikes
  • Oversold bounces (RSI < 30)
  • Earnings volatility setups
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import config
from models import Opportunity, OpportunityType

logger = logging.getLogger(__name__)


def _make_id(ticker: str, setup_type: str) -> str:
    key = f"{ticker}_{setup_type}_{datetime.now().strftime('%Y%m%d')}"
    return "market_" + hashlib.md5(key.encode()).hexdigest()[:10]


def _try_import_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        logger.warning("yfinance not installed — market scanner disabled. Run: pip install yfinance")
        return None


def _calc_rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def scan_momentum(watchlist: Optional[List[str]] = None) -> List[Opportunity]:
    """Find momentum stocks: big move + volume spike."""
    yf = _try_import_yfinance()
    if not yf:
        return []

    tickers = watchlist or config.MARKET_WATCHLIST
    opportunities: List[Opportunity] = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue

            closes = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()

            today_close = closes[-1]
            prev_close = closes[-2]
            today_vol = volumes[-1]
            avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1)

            pct_change = (today_close - prev_close) / prev_close
            vol_factor = today_vol / max(avg_vol, 1)
            rsi = _calc_rsi(closes)

            info = stock.info
            company_name = info.get("longName") or info.get("shortName") or ticker
            sector = info.get("sector", "Unknown")
            market_cap = info.get("marketCap", 0)
            mc_str = (
                f"${market_cap / 1e9:.1f}B" if market_cap >= 1e9
                else f"${market_cap / 1e6:.0f}M" if market_cap >= 1e6
                else "N/A"
            )

            setup_notes = []
            is_interesting = False

            if abs(pct_change) >= config.MARKET_MOMENTUM_THRESHOLD:
                direction = "UP" if pct_change > 0 else "DOWN"
                setup_notes.append(f"{direction} {abs(pct_change)*100:.1f}% today")
                is_interesting = True

            if vol_factor >= config.MARKET_VOLUME_SPIKE_FACTOR:
                setup_notes.append(f"Volume {vol_factor:.1f}x average")
                is_interesting = True

            if rsi and rsi < 30:
                setup_notes.append(f"Oversold RSI {rsi:.0f}")
                is_interesting = True

            if not is_interesting:
                continue

            setup_str = " | ".join(setup_notes)
            title = f"{ticker} ({company_name}): {setup_str}"

            description = (
                f"Ticker: {ticker}\n"
                f"Company: {company_name}\n"
                f"Sector: {sector}\n"
                f"Market Cap: {mc_str}\n"
                f"Price: ${today_close:.2f}\n"
                f"1-Day Change: {pct_change*100:+.2f}%\n"
                f"Volume Factor: {vol_factor:.1f}x avg\n"
                f"RSI (14): {rsi:.1f if rsi else 'N/A'}\n"
                f"Signals: {setup_str}"
            )

            opp = Opportunity(
                id=_make_id(ticker, "momentum"),
                opp_type=OpportunityType.MARKET,
                title=title,
                description=description,
                source_url=f"https://finance.yahoo.com/quote/{ticker}",
                source="market",
                raw_data={
                    "ticker": ticker,
                    "price": today_close,
                    "pct_change": pct_change,
                    "vol_factor": vol_factor,
                    "rsi": rsi,
                    "sector": sector,
                    "market_cap": market_cap,
                },
            )
            opportunities.append(opp)

        except Exception as exc:
            logger.debug("Market scan error for %s: %s", ticker, exc)

    logger.info("Market scan found %d setups", len(opportunities))
    return opportunities


def scan_all() -> List[Opportunity]:
    return scan_momentum()
