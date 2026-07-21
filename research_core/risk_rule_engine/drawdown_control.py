from __future__ import annotations
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field


@dataclass
class RiskAction:
    level: int
    dd: float
    max_historical_dd: float
    dd_duration: int
    action: str
    reason: str


class DrawdownTracker:
    def __init__(self, window_days: int = 365):
        self.window_days = window_days
        self.peak_nav = 0.0
        self.current_nav = 1.0
        self.daily_nav: List[Tuple[datetime, float]] = []
        self._last_date = None

    def update(self, nav: float, date: Optional[datetime] = None) -> float:
        self.current_nav = nav
        if nav > self.peak_nav:
            self.peak_nav = nav

        if date:
            self.daily_nav.append((date, nav))
            self._last_date = date
            cutoff = date - timedelta(days=self.window_days)
            self.daily_nav = [(d, n) for d, n in self.daily_nav if d >= cutoff]

        return self.drawdown

    @property
    def drawdown(self) -> float:
        if self.peak_nav <= 0:
            return 0.0
        return 1.0 - self.current_nav / self.peak_nav

    @property
    def max_historical_dd(self) -> float:
        if not self.daily_nav:
            return 0.0
        navs = np.array([n for _, n in self.daily_nav])
        peak = np.maximum.accumulate(navs)
        dd = 1.0 - navs / peak
        return float(np.max(dd))

    def drawdown_duration(self) -> int:
        if self.peak_nav <= 0 or not self.daily_nav:
            return 0
        for date, nav in reversed(self.daily_nav):
            if nav >= self.peak_nav * 0.999:
                if self._last_date:
                    return (self._last_date - date).days
        return 0


class DrawdownController:
    def __init__(self,
                 max_dd: float = 0.15,
                 warn_dd: float = 0.10,
                 cooldown_days: int = 5,
                 position_sizing_limit: float = 0.30,
                 sector_exposure_limit: float = 0.50):

        self.max_dd = max_dd
        self.warn_dd = warn_dd
        self.cooldown_days = cooldown_days
        self.position_sizing_limit = position_sizing_limit
        self.sector_exposure_limit = sector_exposure_limit

        self.tracker = DrawdownTracker()
        self.was_cleared = False
        self.clear_date = None
        self.total_trades_blocked = 0
        self.total_force_closes = 0

    def check(self, nav: float, date: Optional[datetime] = None) -> RiskAction:
        dd = self.tracker.update(nav, date)
        max_hist_dd = self.tracker.max_historical_dd
        dd_dur = self.tracker.drawdown_duration()

        result = RiskAction(
            level=0,
            dd=round(dd, 4),
            max_historical_dd=round(max_hist_dd, 4),
            dd_duration=dd_dur,
            action='none',
            reason='',
        )

        if self.was_cleared and self.clear_date and date:
            days_since = (date - self.clear_date).days
            if days_since < self.cooldown_days:
                result.level = 1
                result.action = 'no_new_positions'
                result.reason = f'清仓冷却期 ({days_since}/{self.cooldown_days}天)'
                return result

        if dd >= self.max_dd:
            result.level = 3
            result.action = 'clear_all'
            result.reason = f'回撤 {dd:.1%} >= {self.max_dd:.0%} 上限，强制清仓'
            return result

        if dd >= self.max_dd * 0.8:
            result.level = 2
            result.action = 'reduce_50'
            result.reason = f'回撤 {dd:.1%} >= {self.max_dd*0.8:.0%} (上限的80%)，减仓50%'
            return result

        if dd >= self.warn_dd:
            result.level = 1
            result.action = 'no_new_positions'
            result.reason = f'回撤 {dd:.1%} >= {self.warn_dd:.0%} 预警线，禁止新开仓'
            return result

        return result

    def execute(self, action: RiskAction, positions: pd.DataFrame = None):
        level = action.level

        if level == 3:
            self.was_cleared = True
            self.clear_date = datetime.now() if action.level >= 3 else None
            self.total_force_closes += 1

        elif level == 2:
            pass

        elif level == 1:
            pass

        if level >= 2:
            log_msg = f"[风控] LEVEL {level}: {action['reason']}"
            print(log_msg)

    def can_open_new(self, nav: float, date: Optional[datetime] = None) -> Tuple[bool, str]:
        dd = self.tracker.update(nav, date)

        if dd >= self.warn_dd:
            return False, f'回撤 {dd:.1%} >= 预警线 {self.warn_dd:.0%}'

        if self.was_cleared and self.clear_date and date:
            days_since = (date - self.clear_date).days
            if days_since < self.cooldown_days:
                return False, f'清仓冷却期剩余 {self.cooldown_days - days_since} 天'

        return True, 'OK'

    def position_size_check(self, target_value: float, total_nav: float) -> Tuple[bool, str]:
        if total_nav <= 0:
            return False, '总净值为零或负数'
        ratio = target_value / total_nav
        if ratio > self.position_sizing_limit:
            return False, f'单票仓位 {ratio:.1%} > {self.position_sizing_limit:.0%} 限制'
        return True, 'OK'

    def sector_exposure_check(self, positions: pd.DataFrame, sector_col: str = 'sector') -> Tuple[bool, str]:
        if sector_col not in positions.columns:
            return True, '无行业数据，跳过行业检查'
        sector_exposure = positions.groupby(sector_col)['value'].sum() / positions['value'].sum()
        max_sector = sector_exposure.max()
        if max_sector > self.sector_exposure_limit:
            over_sector = sector_exposure[sector_exposure > self.sector_exposure_limit].index.tolist()
            return False, f'行业暴露 {over_sector} > {self.sector_exposure_limit:.0%} 限制'
        return True, 'OK'

    def get_stats(self, date: Optional[datetime] = None) -> Dict:
        return {
            'max_historical_dd': round(self.tracker.max_historical_dd, 4),
            'current_dd': round(self.tracker.drawdown, 4),
            'dd_duration_days': self.tracker.drawdown_duration(),
            'times_force_closed': self.total_force_closes,
            'trades_blocked': self.total_trades_blocked,
            'in_cooldown': self.was_cleared and self.clear_date and date and
                          (date - self.clear_date).days < self.cooldown_days,
        }

    def simulate(self, nav_series: pd.Series) -> pd.DataFrame:
        results = []
        for date, nav in nav_series.items():
            action = self.check(nav, date)
            results.append({
                'date': date,
                'nav': nav,
                'drawdown': action.dd,
                'level': action.level,
                'action': action.action,
                'reason': action.reason,
            })
        return pd.DataFrame(results)


class PositionSizingController:
    def __init__(self, max_position: float = 0.30, min_position: float = 0.01,
                 max_sector: float = 0.50, max_concentration: int = 10):
        self.max_position = max_position
        self.min_position = min_position
        self.max_sector = max_sector
        self.max_concentration = max_concentration

    def calculate_position(self, factor_rank: float, total_nav: float,
                           n_stocks: int = 50) -> float:
        if factor_rank >= 0.9:
            return total_nav * self.max_position
        elif factor_rank >= 0.7:
            return total_nav * self.max_position * 0.6
        elif factor_rank >= 0.5:
            return total_nav * self.max_position * 0.3
        else:
            return 0

    def validate_positions(self, positions: pd.DataFrame) -> Dict:
        issues = []

        if len(positions) > self.max_concentration:
            issues.append(f'持仓数量 {len(positions)} > {self.max_concentration} 限制')

        positions['ratio'] = positions['value'] / positions['value'].sum()
        over_limit = positions[positions['ratio'] > self.max_position]
        if not over_limit.empty:
            issues.append(f'{len(over_limit)} 只股票仓位超限')

        if 'sector' in positions.columns:
            sector_total = positions.groupby('sector')['value'].sum() / positions['value'].sum()
            over_sector = sector_total[sector_total > self.max_sector]
            if not over_sector.empty:
                issues.append(f'行业 {over_sector.index.tolist()} 暴露超限')

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'n_positions': len(positions),
            'max_position_ratio': positions['ratio'].max() if len(positions) > 0 else 0,
        }
