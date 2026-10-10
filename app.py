"""Bitcoin Intelligence V1 — simulated directional trading, never broker execution."""
from __future__ import annotations
import json,hashlib,time,threading,tempfile,os
from dataclasses import dataclass,asdict,replace
from datetime import datetime,timezone,timedelta
from decimal import Decimal,ROUND_DOWN
from contextlib import contextmanager
import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from sqlalchemy import create_engine,text

VERSION='btc-preset-v1-unvalidated'
SCALP_FAMILIES65=('Scalp Breakout','Scalp Retest','Scalp Rejection')
CALENDAR_URL65='https://nfs.faireconomy.media/ff_calendar_thisweek.json'
LOCK=threading.RLock()

def utcnow():return datetime.now(timezone.utc)
def stamp(v):return pd.Timestamp(v).tz_convert('UTC') if pd.Timestamp(v).tzinfo else pd.Timestamp(v).tz_localize('UTC')
def hash_of(v):return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class Config:
    capital:float=10000.
    risk_pct:float=.5
    fee_bps:float=10.
    spread_bps:float=2.
    slip_bps:float=1.
    max_spread_bps:float=10.
    funding_bps_8h:float=0.
    policy:str='REFERENCE_SIMULATION'
    max_exposure:float=1.
    max_aggregate_pct:float=2.
    daily_dd_pct:float=3.
    auto:bool=True
    kill:bool=False
    active:bool=True
    require_volume:bool=True
    allow_no_news:bool=False

class Store:
    def __init__(self,url):
        args={'connect_args':{'check_same_thread':False,'timeout':30}} if url.startswith('sqlite') else {}
        self.engine=create_engine(url,pool_pre_ping=True,**args)
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE IF NOT EXISTS btc_v1_state (key VARCHAR(180) PRIMARY KEY, payload TEXT NOT NULL)'))
    @contextmanager
    def transaction(self):
        with LOCK,self.engine.begin() as c:yield c
    def get(self,c,key,default=None):
        row=c.execute(text('SELECT payload FROM btc_v1_state WHERE key=:k'),{'k':key}).scalar()
        return json.loads(row) if row is not None else default
    def put(self,c,key,value):
        c.execute(text('INSERT INTO btc_v1_state (key,payload) VALUES (:k,:v) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload'),{'k':key,'v':json.dumps(value,default=str)})
    def state(self):
        with self.transaction() as c:return self.get(c,'ledger',{'positions':[],'events':[],'daily':{},'last_fill':None})
    def health(self):
        with self.transaction() as c:return self.get(c,'health',{'attempts':0,'successes':0,'failures':0,'status':'NOT_STARTED'})
    def audits(self):
        with self.transaction() as c:return self.get(c,'audit',{})
    def effective_config(self,cfg):
        with self.transaction() as c:
            active=self.get(c,'active',True)
        return replace(cfg,active=active)
    def set_active(self,value):
        with self.transaction() as c:self.put(c,'active',bool(value))

def api_get(path,params=None):
    # Fixed public GET-only endpoints. No user credentials, order routes or raw errors.
    for retry in range(3):
        try:
            r=requests.get('https://api.exchange.coinbase.com/products/BTC-USD/'+path,params=params,timeout=10,headers={'User-Agent':'Bitcoin-Paper-Research/1.0','Accept':'application/json'},allow_redirects=False)
            if r.status_code==429:
                wait=min(5.,max(1.,float(r.headers.get('Retry-After','1'))))
                if retry<2:time.sleep(wait);continue
                raise RuntimeError('RATE_LIMIT')
            if r.status_code!=200:raise RuntimeError('PROVIDER_UNAVAILABLE')
            return r.json()
        except Exception:
            if retry==2:raise RuntimeError('PUBLIC_DATA_UNAVAILABLE') from None
            time.sleep(.5*(retry+1))

def parse_candles(rows,seconds,now):
    if not isinstance(rows,list) or not rows:raise ValueError('EMPTY_CANDLES')
    if any(not isinstance(r,list) or len(r)!=6 for r in rows):raise ValueError('CANDLE_SCHEMA_INVALID')
    df=pd.DataFrame(rows,columns=['time','low','high','open','close','volume'])
    for col in df:df[col]=pd.to_numeric(df[col],errors='raise')
    if not np.isfinite(df.to_numpy()).all():raise ValueError('INVALID_CANDLES')
    if (df[['open','close','low','high']]<=0).any().any() or (df.volume<0).any():raise ValueError('INVALID_CANDLES')
    if ((df.low>df[['open','close']].min(axis=1))|(df.high<df[['open','close']].max(axis=1))).any():raise ValueError('INVALID_CANDLES')
    df.index=pd.to_datetime(df.pop('time'),unit='s',utc=True);df.index.name='datetime'
    df=df[~df.index.duplicated()].sort_index();return df[df.index+pd.Timedelta(seconds=seconds)<=stamp(now)]

@st.cache_data(ttl=310,show_spinner=False)
def history5(bucket):
    end=stamp(bucket);parts=[]
    for n in range(4):
        stop=end-pd.Timedelta(seconds=300*299*n);start=stop-pd.Timedelta(seconds=300*299)
        rows=api_get('candles',dict(granularity=300,start=start.isoformat(),end=stop.isoformat()))
        part=parse_candles(rows,300,end);parts.append(part.loc[start:stop]);time.sleep(.4)
    df=pd.concat(parts).sort_index();return df[~df.index.duplicated(keep='last')]

@st.cache_data(ttl=61,show_spinner=False)
def history1(bucket):return parse_candles(api_get('candles',dict(granularity=60)),60,stamp(bucket))

def parse_quote(data,received):
    try:
        price=float(data['price']);ts=stamp(data['time']);bid=float(data['bid']);ask=float(data['ask'])
        if not all(np.isfinite([price,bid,ask])) or min(price,bid,ask)<=0 or ask<bid:raise ValueError()
        return dict(price=price,bid=bid,ask=ask,time=ts.isoformat(),received=stamp(received).isoformat(),source='Coinbase BTC-USD public ticker')
    except Exception:raise ValueError('INVALID_QUOTE') from None

def fetch_market():
    now=utcnow();base=history5(stamp(now).floor('5min').isoformat());minute=history1(stamp(now).floor('min').isoformat())
    q=parse_quote(api_get('ticker'),utcnow())
    if len(base)<650 or minute.empty:raise ValueError('INSUFFICIENT_HISTORY')
    if not base.tail(650).index.to_series().diff().dropna().eq(pd.Timedelta(minutes=5)).all():raise ValueError('PRIMARY_HISTORY_GAP')
    return q,base,minute


def ensure_utc_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted copy with a UTC DatetimeIndex named 'datetime'."""
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError('DataFrame index must be a DatetimeIndex.')
    if out.index.tz is None:
        out.index = out.index.tz_localize('UTC')
    else:
        out.index = out.index.tz_convert('UTC')
    out.index.name = 'datetime'
    return out.sort_index()


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    result = 100 - 100 / (1 + rs)
    result = result.mask((ad == 0) & (au > 0), 100.)
    return result.mask((ad == 0) & (au == 0), 50.)


def atr(df, n=14):
    pc = df['close'].shift(1)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - pc).abs(), (df['low'] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df, n=14):
    up = df['high'].diff()
    dn = -df['low'].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    a = atr(df, n)
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False).mean() / a.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False).mean() / a.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return (dx.ewm(alpha=1 / n, adjust=False).mean(), plus_di, minus_di)


def stochastic(df, n=14):
    lo = df['low'].rolling(n).min()
    hi = df['high'].rolling(n).max()
    return 100 * (df['close'] - lo) / (hi - lo).replace(0, np.nan)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    x = ensure_utc_datetime_index(df)
    c = x['close']
    for n in [9, 20, 50, 100, 200]:
        x[f'ema{n}'] = ema(c, n)
    x['rsi14'] = rsi(c, 14)
    x['atr14'] = atr(x, 14)
    x['atr_pct'] = 100 * x['atr14'] / c
    x['roc10'] = 100 * (c / c.shift(10) - 1)
    x['macd'] = ema(c, 12) - ema(c, 26)
    x['macd_signal'] = ema(x['macd'], 9)
    x['macd_hist'] = x['macd'] - x['macd_signal']
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    x['bb_mid'] = mid
    x['bb_up'] = mid + 2 * sd
    x['bb_dn'] = mid - 2 * sd
    x['bb_width'] = (x['bb_up'] - x['bb_dn']) / mid
    x['don20_hi'] = x['high'].shift(1).rolling(20).max()
    x['don20_lo'] = x['low'].shift(1).rolling(20).min()
    x['don40_hi'] = x['high'].shift(1).rolling(40).max()
    x['don40_lo'] = x['low'].shift(1).rolling(40).min()
    x['adx14'], x['plus_di'], x['minus_di'] = adx(x, 14)
    x['stoch14'] = stochastic(x, 14)
    body = (x['close'] - x['open']).abs()
    rng = (x['high'] - x['low']).replace(0, np.nan)
    x['body_pct'] = body / rng
    x['upper_wick'] = (x['high'] - x[['open', 'close']].max(axis=1)) / rng
    x['lower_wick'] = (x[['open', 'close']].min(axis=1) - x['low']) / rng
    po = x['open'].shift(1)
    pc = x['close'].shift(1)
    x['bull_engulf'] = (x['close'] > x['open']) & (pc < po) & (x['open'] <= pc) & (x['close'] >= po)
    x['bear_engulf'] = (x['close'] < x['open']) & (pc > po) & (x['open'] >= pc) & (x['close'] <= po)
    x['bull_pin'] = (x['lower_wick'] > 0.55) & (x['body_pct'] < 0.35)
    x['bear_pin'] = (x['upper_wick'] > 0.55) & (x['body_pct'] < 0.35)
    for n in [5, 10, 20]:
        prev_hi = x['high'].shift(1).rolling(n).max()
        prev_lo = x['low'].shift(1).rolling(n).min()
        x[f'bos_up_{n}'] = x['close'] > prev_hi
        x[f'bos_dn_{n}'] = x['close'] < prev_lo
        x[f'sweep_low_{n}'] = (x['low'] < prev_lo) & (x['close'] > prev_lo)
        x[f'sweep_high_{n}'] = (x['high'] > prev_hi) & (x['close'] < prev_hi)
    ma50 = c.rolling(50).mean()
    sd50 = c.rolling(50).std()
    x['z50'] = (c - ma50) / sd50.replace(0, np.nan)
    x['vol20'] = c.pct_change().rolling(20).std() * np.sqrt(20)
    x['trend_strength'] = (x['ema20'] - x['ema100']).abs() / x['atr14'].replace(0, np.nan)
    x['hour_utc'] = x.index.hour
    x['london'] = x['hour_utc'].between(7, 15)
    x['new_york'] = x['hour_utc'].between(12, 20)
    x['overlap'] = x['hour_utc'].between(12, 15)
    for n in [1, 2, 4, 8, 16, 32]:
        x[f'ret_{n}'] = c.pct_change(n)
    return x


def resample_ohlc_strict(df: pd.DataFrame, rule: str, expected_count: int) -> pd.DataFrame:
    """
    Aggregate already-closed lower-timeframe bars and keep only complete groups.
    Timestamps remain BAR OPEN times.
    """
    z = ensure_utc_datetime_index(df)[["open","high","low","close"]].copy()
    agg = z.resample(rule, label="left", closed="left").agg(
        {"open":"first","high":"max","low":"min","close":"last"}
    )
    counts = z["close"].resample(rule, label="left", closed="left").count()
    agg = agg[counts >= int(expected_count)].dropna()
    return agg


def regime_evidence64(x):
    """Closed-bar state; no future filling. Thresholds are fixed, not audit-fit."""
    z = x.copy()
    z['ema_slope'] = (z.ema20 - z.ema20.shift(5)) / z.atr14.replace(0, np.nan)
    z['ema_separation'] = (z.ema20 - z.ema100) / z.atr14.replace(0, np.nan)
    z['atr_cut'] = z.atr_pct.shift(1).rolling(252, min_periods=100).quantile(.85)
    required = ['adx14', 'ema_slope', 'ema_separation', 'atr_cut', 'bb_width', 'vol20', 'roc10']
    ready = z[required].notna().all(axis=1)
    raw = pd.Series('UNKNOWN', index=z.index)
    raw.loc[ready] = 'RANGE'
    up = ready & (z.adx14 >= 23) & (z.ema_slope > .1) & (z.ema_separation > .3)
    down = ready & (z.adx14 >= 23) & (z.ema_slope < -.1) & (z.ema_separation < -.3)
    raw.loc[up] = 'TREND_UP'
    raw.loc[down] = 'TREND_DOWN'
    raw.loc[ready & (z.atr_pct > z.atr_cut)] = 'VOLATILE'
    z['regime_closed'] = raw
    z['completeness_pct'] = z[required].notna().mean(axis=1) * 100
    # Fixed UTC session windows are descriptive proxies, not DST-adjusted exchanges.
    h = z.index.hour
    z['asia'] = (h >= 0) & (h < 7)
    z['session64'] = np.select([z.overlap, z.new_york, z.london, z.asia],
                              ['OVERLAP', 'NEW_YORK', 'LONDON', 'ASIA'], default='OTHER')
    return z


def scalp_features65(primary,context15):
    x=add_features(primary.copy())
    y=regime_evidence64(add_features(context15))
    available=y[['regime_closed','completeness_pct']].copy()
    available.index=available.index+pd.Timedelta(minutes=15)
    available.index.name='available_at'
    decision=pd.DataFrame({'available_at':x.index+pd.Timedelta(minutes=5)},index=x.index)
    m=pd.merge_asof(decision.reset_index(drop=True).sort_values('available_at'),
                    available.reset_index().sort_values('available_at'),on='available_at',direction='backward')
    x['regime15']=m.regime_closed.fillna('UNKNOWN').to_numpy()
    x['regime_completeness']=m.completeness_pct.fillna(0).to_numpy()
    x['resistance10']=x.high.shift(1).rolling(10,min_periods=10).max()
    x['support10']=x.low.shift(1).rolling(10,min_periods=10).min()
    x['bb_width_previous']=x.bb_width.shift(1).rolling(20,min_periods=10).median()
    if 'volume' not in x:x['volume']=np.nan
    x['volume']=pd.to_numeric(x.volume,errors='coerce').where(lambda v:v>=0)
    reference=x.volume.shift(1).rolling(20,min_periods=20).mean()
    x['relative_volume']=x.volume/reference.replace(0,np.nan)
    x['volume_available']=x.volume.notna() & reference.gt(0)
    return x


def scalp_masks65(x,p,require_volume=False):
    """Three deterministic setups, disjoint regime families and explicit direction."""
    a=x.atr14
    ready=x[['rsi14','atr14','resistance10','support10','bb_width_previous']].notna().all(axis=1)&a.gt(0)
    vol=(x.volume_available & x.relative_volume.ge(1.1)) if require_volume else pd.Series(True,index=x.index)
    rsil=x.rsi14.between(p.get('rsi_buy_min',52),p.get('rsi_buy_max',75))
    rsis=x.rsi14.between(p.get('rsi_sell_min',25),p.get('rsi_sell_max',48))
    body=x.body_pct.ge(.5)
    bbexp=x.bb_width.ge(.8*x.bb_width_previous)&x.bb_width.gt(x.bb_width.shift(1))
    margin=p.get('buffer',.1)*a
    up=x.regime15.eq('TREND_UP');down=x.regime15.eq('TREND_DOWN');rang=x.regime15.eq('RANGE')
    breakout_buy=ready&vol&up&rsil&body&bbexp&x.close.gt(x.open)&x.close.gt(x.resistance10+margin)&x.close.gt(x.bb_mid)
    breakout_sell=ready&vol&down&rsis&body&bbexp&x.close.lt(x.open)&x.close.lt(x.support10-margin)&x.close.lt(x.bb_mid)
    # Previous bar break level is frozen before its breakout; current bar tests it.
    prior_hi=x.resistance10.shift(1);prior_lo=x.support10.shift(1)
    was_up=x.close.shift(1).gt(prior_hi+p.get('buffer',.1)*a.shift(1))
    was_dn=x.close.shift(1).lt(prior_lo-p.get('buffer',.1)*a.shift(1))
    retest_buy=ready&vol&up&rsil&was_up&x.low.le(prior_hi+.15*a)&x.low.ge(prior_hi-.3*a)&x.close.gt(prior_hi)&x.close.gt(x.open)
    retest_sell=ready&vol&down&rsis&was_dn&x.high.ge(prior_lo-.15*a)&x.high.le(prior_lo+.3*a)&x.close.lt(prior_lo)&x.close.lt(x.open)
    bull=x.bull_pin|x.bull_engulf
    bear=x.bear_pin|x.bear_engulf
    rejection_buy=ready&vol&rang&bull&x.rsi14.le(45)&x.low.le(x.support10+.2*a)&x.low.le(x.bb_dn)&x.close.gt(x.bb_dn)&x.close.gt(x.open)
    rejection_sell=ready&vol&rang&bear&x.rsi14.ge(55)&x.high.ge(x.resistance10-.2*a)&x.high.ge(x.bb_up)&x.close.lt(x.bb_up)&x.close.lt(x.open)
    return {'Scalp Breakout':(breakout_buy,breakout_sell),'Scalp Retest':(retest_buy,retest_sell),
            'Scalp Rejection':(rejection_buy,rejection_sell)}


def scalp_signal65(x,params,options=None):
    options=options or {}
    routes=params.get('routes',{})
    hits=[]
    row=x.iloc[-1]
    evidence={k:float(row[k]) if pd.notna(row[k]) else None for k in
              ['rsi14','atr14','adx14','stoch14','macd_hist','roc10','ema20','ema50','ema100','bb_mid','bb_up','bb_dn','bb_width','resistance10','support10','relative_volume','body_pct']}
    evidence.update(regime15=str(row.regime15),volume_status='PROVIDER_VOLUME_AVAILABLE' if row.volume_available else 'UNAVAILABLE',
                    volume_required=bool(options.get('require_volume')),session_utc=int(x.index[-1].hour))
    if row.regime15=='UNKNOWN':return dict(side=0,reason='REGIME_DATA_INCOMPLETE',evidence=evidence)
    if row.regime15=='VOLATILE':return dict(side=0,reason='VOLATILE_REGIME_BLOCK',evidence=evidence)
    if options.get('require_volume') and not row.volume_available:
        return dict(side=0,reason='VOLUME_REQUIRED_BUT_UNAVAILABLE',evidence=evidence)
    session=options.get('session','ALL')
    hour=(x.index[-1]+pd.Timedelta(minutes=5)).hour
    if session!='ALL' and not {'LONDON':7<=hour<=15,'NEW_YORK':12<=hour<=20,'OVERLAP':12<=hour<=15}.get(session,False):
        return dict(side=0,reason='SESSION_FILTER_BLOCK',evidence=evidence)
    masks=[]
    for key,config in routes.items():
        reg,side=key.split('|')
        if reg!=row.regime15:continue
        for family in SCALP_FAMILIES65:
            buys,sells=scalp_masks65(x,config['params'],options.get('require_volume',False))[family]
            eligible=family in config['setups']
            passed=bool((buys if side=='BUY' else sells).iloc[-1]) and eligible
            masks.append(dict(family=family,side=side,eligible=eligible,passed=passed))
            if passed:hits.append((1 if side=='BUY' else -1,family,config['params']))
    evidence['setup_checks']=masks
    evidence['rule_checks']=dict(bullish_pattern=bool(row.bull_pin or row.bull_engulf),bearish_pattern=bool(row.bear_pin or row.bear_engulf),
        body_ge_50pct=bool(row.body_pct>=.5),close_above_bb_mid=bool(row.close>row.bb_mid),close_below_bb_mid=bool(row.close<row.bb_mid),
        buy_rsi_52_to_75=bool(52<=row.rsi14<=75),sell_rsi_25_to_48=bool(25<=row.rsi14<=48),
        close_above_prior_resistance=bool(row.close>row.resistance10),close_below_prior_support=bool(row.close<row.support10),
        range_buy_rsi_le45=bool(row.rsi14<=45),range_sell_rsi_ge55=bool(row.rsi14>=55),
        lower_band_touched=bool(row.low<=row.bb_dn),upper_band_touched=bool(row.high>=row.bb_up))
    if not hits:return dict(side=0,reason='NO_CONFIRMED_5M_SETUP',evidence=evidence)
    if len({h[0] for h in hits})>1:return dict(side=0,reason='CONFLICTING_DIRECTIONS',evidence=evidence)
    # Prefer a successful retest when both same-direction rules coincide. No voting.
    hits.sort(key=lambda h:SCALP_FAMILIES65.index(h[1]) if h[1]!='Scalp Retest' else -1)
    side,family,p=hits[0]
    return dict(side=side,family=family,params=dict(p),reason='CONFIRMED_'+family.replace(' ','_').upper(),evidence=evidence)


def diagnostic_rules66(x,params,options=None):
    """Explain exactly the predicates used by scalp_masks65, without changing signals."""
    opts=options or {};r=x.iloc[-1];prior=x.iloc[-2] if len(x)>1 else r;rows=[]
    ready=bool(r[['rsi14','atr14','resistance10','support10','bb_width_previous']].notna().all() and r.atr14>0)
    hour=(x.index[-1]+pd.Timedelta(minutes=5)).hour
    session=opts.get('session','ALL');sess=session=='ALL' or {'LONDON':7<=hour<=15,'NEW_YORK':12<=hour<=20,'OVERLAP':12<=hour<=15}.get(session,False)
    for key,cfg in params.get('routes',{}).items():
        reg,side=key.split('|');p=cfg['params'];buy=side=='BUY';a=r.atr14
        masks=scalp_masks65(x,p,opts.get('require_volume',False))
        for family in SCALP_FAMILIES65:
            if family not in cfg.get('setups',[]):continue
            checks=[('Eligible regime',r.regime15,reg,r.regime15==reg),('Data readiness',ready,True,ready),('UTC session',hour,session,sess)]
            if opts.get('require_volume'):
                checks.append(('Relative volume',r.relative_volume,'>= 1.1 with valid volume',bool(r.volume_available and r.relative_volume>=1.1)))
            checks.append(('Candle direction',r.close-r.open,'Positive' if buy else 'Negative',r.close>r.open if buy else r.close<r.open))
            if family=='Scalp Rejection':
                checks.extend([('Reversal pattern',bool(r.bull_pin or r.bull_engulf) if buy else bool(r.bear_pin or r.bear_engulf),True,bool(r.bull_pin or r.bull_engulf) if buy else bool(r.bear_pin or r.bear_engulf)),
                  ('RSI',r.rsi14,'≤45' if buy else '≥55',r.rsi14<=45 if buy else r.rsi14>=55),
                  ('Prior support / resistance touch',r.low if buy else r.high,r.support10+.2*a if buy else r.resistance10-.2*a,r.low<=r.support10+.2*a if buy else r.high>=r.resistance10-.2*a),
                  ('Bollinger band touch',r.low if buy else r.high,r.bb_dn if buy else r.bb_up,r.low<=r.bb_dn if buy else r.high>=r.bb_up),
                  ('Close back inside band',r.close,r.bb_dn if buy else r.bb_up,r.close>r.bb_dn if buy else r.close<r.bb_up)])
            else:
                lo=p.get('rsi_buy_min',52) if buy else p.get('rsi_sell_min',25);hi=p.get('rsi_buy_max',75) if buy else p.get('rsi_sell_max',48)
                checks.append(('RSI',r.rsi14,f'{lo} to {hi}',lo<=r.rsi14<=hi))
                if family=='Scalp Breakout':
                    level=r.resistance10+p.get('buffer',.1)*a if buy else r.support10-p.get('buffer',.1)*a
                    checks.extend([('Body / candle range',r.body_pct,'≥0.5',r.body_pct>=.5),
                     ('Band expansion',r.bb_width,f'≥ {0.8*r.bb_width_previous:.6g} and > {prior.bb_width:.6g}',r.bb_width>=.8*r.bb_width_previous and r.bb_width>prior.bb_width),
                     ('Close beyond prior level + buffer',r.close,level,r.close>level if buy else r.close<level),
                     ('Close versus Bollinger midpoint',r.close,r.bb_mid,r.close>r.bb_mid if buy else r.close<r.bb_mid)])
                else:
                    level=prior.resistance10 if buy else prior.support10
                    was=prior.close>level+p.get('buffer',.1)*prior.atr14 if buy else prior.close<level-p.get('buffer',.1)*prior.atr14
                    touch=(level-.3*a<=r.low<=level+.15*a) if buy else (level-.15*a<=r.high<=level+.3*a)
                    checks.extend([('Previous candle breakout',prior.close,level,was),('Retest tolerance',r.low if buy else r.high,f'{level-.3*a:.4f} to {level+.15*a:.4f}' if buy else f'{level-.15*a:.4f} to {level+.3*a:.4f}',touch),('Close holds the broken level',r.close,level,r.close>level if buy else r.close<level)])
            passed=bool((masks[family][0 if buy else 1]).iloc[-1]) and sess and r.regime15==reg
            for name,value,required,ok in checks:
                rows.append(dict(route=key,family=family,condition=name,value=str(value),required=str(required),passed=bool(ok),route_passed=passed))
    return pd.DataFrame(rows)


def parse_calendar65(rows,now=None):
    """Only explicit-offset timestamps; provider forecast/actual never drives trades."""
    now=pd.Timestamp(now or utcnow()).tz_convert('UTC')
    if not isinstance(rows,list) or not rows or len(rows)>5000:raise ValueError('CALENDAR_SCHEMA_INVALID')
    parsed=[]
    for r in rows:
        if not isinstance(r,dict):raise ValueError('CALENDAR_SCHEMA_INVALID')
        if not all(k in r for k in ('title','country','date','impact')):raise ValueError('CALENDAR_SCHEMA_INVALID')
        ts=pd.Timestamp(r['date'])
        if pd.isna(ts) or ts.tzinfo is None:raise ValueError('CALENDAR_TIMEZONE_UNKNOWN')
        parsed.append(dict(title=str(r['title'])[:250],currency=str(r['country']).upper(),
                           time_utc=ts.tz_convert('UTC'),impact=str(r['impact']).upper()))
    events=pd.DataFrame(parsed).sort_values('time_utc')
    # Export week is Sunday-to-Saturday in New York time, not computer locale.
    local=now.tz_convert('America/New_York')
    start=local.normalize()-pd.Timedelta(days=(local.weekday()+1)%7)
    end=start+pd.DateOffset(days=7)
    if not events.time_utc.between(start.tz_convert('UTC'),end.tz_convert('UTC'),inclusive='left').any():
        raise ValueError('CALENDAR_WEEK_STALE')
    return dict(events=events,coverage_start=start.tz_convert('UTC'),coverage_end=end.tz_convert('UTC'),
                fetched_at=now,status='OK',source='Forex Factory weekly JSON export')


@st.cache_data(ttl=600,show_spinner=False)
def fetch_calendar65(week_key):
    try:
        response=requests.get(CALENDAR_URL65,timeout=10,headers={'Accept':'application/json'},allow_redirects=False)
        if response.status_code!=200 or len(response.content)>2_000_000:raise ValueError('CALENDAR_UNAVAILABLE')
        return parse_calendar65(response.json())
    except Exception:
        return dict(status='UNAVAILABLE',events=pd.DataFrame(),fetched_at=pd.Timestamp.now(tz='UTC'),
                    source='Forex Factory weekly export',error='Calendar unavailable, invalid or stale; no raw provider errors shown')


def news_gate65(calendar,now=None,allow_unknown=False):
    now=pd.Timestamp(now or utcnow()).tz_convert('UTC')
    known=calendar.get('status')=='OK'
    if known:
        age=(now-calendar['fetched_at']).total_seconds()
        known=0<=age<=1200 and calendar['coverage_start']<=now<calendar['coverage_end']
    if not known:
        return dict(allowed=bool(allow_unknown),status='UNPROTECTED_OPT_IN' if allow_unknown else 'NEWS_DATA_UNKNOWN',
                    reasons=['Calendar unavailable; no news protection' if allow_unknown else 'Entry blocked: calendar unavailable or stale'],events=[])
    events=calendar['events']
    relevant=events[events.currency.isin(['USD','ALL']) & events.impact.isin(['HIGH','MEDIUM'])]
    # +/-20 minutes for scheduled HIGH/MEDIUM USD/ALL events.
    nearby=relevant[(relevant.time_utc>=now-pd.Timedelta(minutes=20)) & (relevant.time_utc<=now+pd.Timedelta(minutes=20))]
    return dict(allowed=nearby.empty,status='CLEAR' if nearby.empty else 'NEWS_BLACKOUT',
                reasons=['Important release window: new entries blocked'] if len(nearby) else ['Outside scheduled news blackout'],
                events=nearby.to_dict('records'))

def preset():
    routes={}
    for reg,side in [('TREND_UP','BUY'),('TREND_DOWN','SELL'),('RANGE','BUY'),('RANGE','SELL')]:
        p=dict(buffer=.10 if side=='BUY' else .15,rsi_buy_min=52,rsi_buy_max=75,rsi_sell_min=25,rsi_sell_max=48,sl=1.3 if side=='BUY' else 1.5,rr=1.2 if side=='BUY' else 1.3)
        routes[reg+'|'+side]=dict(params=p,setups=['Scalp Rejection'] if reg=='RANGE' else ['Scalp Breakout','Scalp Retest'],validated=False)
    return dict(routes=routes,parameter_version=VERSION,validated=False)

def fill_price(q,side,cfg,exit=False):
    direction=-side if exit else side
    if cfg.policy=='STRICT_EXECUTABLE':
        if q.get('bid') is None or q.get('ask') is None:raise ValueError('BID_ASK_REQUIRED')
        raw=q['ask'] if direction==1 else q['bid']
    else:raw=q['price']*(1+direction*cfg.spread_bps/20000)
    return raw*(1+direction*cfg.slip_bps/10000)

def quote_valid(q,now):
    return all(0<=(stamp(now)-stamp(q[k])).total_seconds()<=30 for k in ['time','received'])

def estimate_loss(qty,entry,stop,cfg):
    direction=1 if stop<entry else -1
    stop_fill=stop*(1-direction*(cfg.spread_bps/2+cfg.slip_bps)/10000)
    return qty*(abs(entry-stop_fill)+(entry+stop_fill)*cfg.fee_bps/10000)

def build_plan(sig,x,q,cfg,equity):
    side=int(sig['side']);r=x.iloc[-1];a=float(r.atr14);ref=q['price'];p=sig['params']
    if not np.isfinite(a) or a<=0:return None,'INVALID_ATR'
    stop=float(r.low)-.15*a if side==1 else float(r.high)+.15*a
    distance=max(a*p['sl'],side*(ref-stop));stop=ref-side*distance
    if abs(ref-r.close)>.4*a:return None,'PRICE_MOVED_AFTER_SIGNAL'
    if distance>3*a:return None,'STOP_TOO_WIDE'
    entry=fill_price(q,side,cfg);risk=abs(entry-stop)
    roundtrip=(cfg.spread_bps+2*cfg.slip_bps+2*cfg.fee_bps)/10000*entry
    if risk<2.5*roundtrip or risk*.4*p['rr']<1.5*roundtrip:return None,'COSTS_TOO_HIGH_FOR_SETUP'
    unit_loss=estimate_loss(1,entry,stop,cfg)
    qty=min(equity*cfg.risk_pct/100/unit_loss,equity*cfg.max_exposure/(entry*(1+cfg.max_exposure*cfg.fee_bps/10000)))
    # Even number of satoshis allows exact half of original quantity at TP3.
    qty=float((Decimal(str(qty))/Decimal('.00000002')).to_integral_value(rounding=ROUND_DOWN)*Decimal('.00000002'))
    if qty<=0:return None,'SIZE_TOO_SMALL'
    at=x.index[-1]+pd.Timedelta(minutes=5)
    ident=hash_of(dict(time=str(at),side=side,family=sig['family'],version=VERSION,costs=[cfg.fee_bps,cfg.spread_bps,cfg.slip_bps]))
    plan=dict(id=ident,side=side,entry=entry,stop=stop,qty=qty,risk_usd=estimate_loss(qty,entry,stop,cfg),notional=qty*entry,
       targets=[entry+side*risk*m*p['rr'] for m in [.4,.7,1.,1.3,1.7]],family=sig['family'],regime=str(r.regime15),signal_at=at.isoformat(),version=VERSION,reason=sig['reason'],costs=asdict(cfg))
    plan['evidence']=sig.get('evidence',{});plan['hash']=hash_of(plan);return plan,None

class RiskEngine:
    @staticmethod
    def assess(state,plan,q,cfg,now,minute_close,news):
        reasons=[];opens=[p for p in state['positions'] if p['status']=='OPEN'];equity=cfg.capital+sum(p['pnl'] for p in state['positions'])
        if not cfg.active:reasons.append('NO_ACTIVE_PRESET')
        if not cfg.auto:reasons.append('AUTO_DISABLED')
        if cfg.kill:reasons.append('KILL_SWITCH')
        if not news:reasons.append('NEWS_BLOCK')
        if not quote_valid(q,now):reasons.append('STALE_QUOTE')
        if not 0<=(stamp(now)-stamp(minute_close)).total_seconds()<=180:reasons.append('STALE_1M')
        if cfg.policy=='STRICT_EXECUTABLE' and (q.get('bid') is None or q.get('ask') is None):reasons.append('BID_ASK_REQUIRED')
        spread=(q['ask']-q['bid'])/q['price']*10000 if q.get('ask') and q.get('bid') else cfg.spread_bps
        if spread>cfg.max_spread_bps or cfg.spread_bps>cfg.max_spread_bps:reasons.append('SPREAD_LIMIT')
        if len(opens)>=2:reasons.append('GLOBAL_POSITION_LIMIT')
        if len(opens)>=1:reasons.append('OWN_POSITION_LIMIT')
        if any(p['side']==plan['side'] for p in opens):reasons.append('SAME_DIRECTION_OPEN')
        if any(p['candidate']==plan['id'] for p in state['positions']):reasons.append('DUPLICATE_CANDIDATE')
        if any(p.get('gap') for p in opens):reasons.append('MANAGEMENT_GAP_RECONCILE')
        if state.get('last_fill') and (stamp(now)-stamp(state['last_fill'])).total_seconds()<300:reasons.append('ROLLING_FILL_LIMIT')
        if equity<=0:reasons.append('EQUITY_INVALID')
        if plan['risk_usd']>max(0,equity)*cfg.risk_pct/100+1e-8:reasons.append('PER_TRADE_RISK')
        if plan['risk_usd']+sum(p['initial_risk'] for p in opens)>max(0,equity)*cfg.max_aggregate_pct/100:reasons.append('AGGREGATE_RISK')
        if plan['notional']+sum(p['remaining']*q['price'] for p in opens)>max(0,equity-plan['notional']*cfg.fee_bps/10000)*cfg.max_exposure+1e-7:reasons.append('NOTIONAL_CAP')
        marked=equity+sum(p['side']*(q['price']-p['entry'])*p['remaining']-p['remaining']*q['price']*p['costs']['fee_bps']/10000 for p in opens)
        day=stamp(now).strftime('%Y-%m-%d');daily=state['daily'].get(day,{'start':marked,'peak':marked,'blocked':False})
        daily['peak']=max(daily['peak'],marked)
        if marked<=daily['peak']*(1-cfg.daily_dd_pct/100):daily['blocked']=True
        state['daily'][day]=daily
        if daily['blocked']:reasons.append('DAILY_DRAWDOWN')
        return dict(approved=not reasons,reasons=reasons,plan_hash=plan['hash'],expires=(stamp(now)+pd.Timedelta(seconds=15)).isoformat())

class ExecutionEngine:
    def __init__(self,store):self.store=store
    @staticmethod
    def event(state,p,kind,at,price=None,qty=0,pnl=0,**details):
        state['events'].append(dict(position=p['id'],event=kind,time=str(at),price=price,quantity=qty,pnl=pnl,details=details))
    def open(self,plan,decision,q,cfg,now,minute_close,news):
        with self.store.transaction() as c:
            state=self.store.get(c,'ledger',{'positions':[],'events':[],'daily':{},'last_fill':None})
            if not decision['approved'] or decision['plan_hash']!=plan['hash'] or hash_of({k:v for k,v in plan.items() if k!='hash'})!=plan['hash'] or stamp(now)>stamp(decision['expires']):raise ValueError('INVALID_RISK_APPROVAL')
            # Recheck persistent activation and all admission conditions under the transaction.
            cfg=replace(cfg,active=self.store.get(c,'active',True))
            latest=RiskEngine.assess(state,plan,q,cfg,now,minute_close,news)
            if not latest['approved']:raise ValueError('EXECUTION_RISK_RECHECK_BLOCK')
            if any(plan['costs'][k]!=getattr(cfg,k) for k in ['fee_bps','spread_bps','slip_bps','policy','funding_bps_8h']):raise ValueError('COSTS_CHANGED_REPLAN')
            if abs(fill_price(q,plan['side'],cfg)-plan['entry'])>1e-8:raise ValueError('QUOTE_CHANGED_REPLAN')
            p=dict(id=len(state['positions'])+1,candidate=plan['id'],side=plan['side'],entry=plan['entry'],sl_initial=plan['stop'],sl=plan['stop'],targets=plan['targets'],original=plan['qty'],remaining=plan['qty'],initial_risk=plan['risk_usd'],status='OPEN',opened=stamp(now).isoformat(),closed=None,last_bar=None,pending=None,hits=[False]*5,pnl=-plan['qty']*plan['entry']*cfg.fee_bps/10000,costs=asdict(cfg),family=plan['family'],version=VERSION,regime=plan['regime'],regime_changed=False,gap=False,last_funding=stamp(now).isoformat())
            state['positions'].append(p);state['last_fill']=str(now)
            self.event(state,p,'OPEN',now,p['entry'],p['original'],p['pnl'],simulated=True,signal_reason=plan['reason'],regime=p['regime'],version=VERSION,costs=p['costs'],news_status=plan.get('news_status','REPLAY_OR_LAB_EXCLUDED'),evidence=plan.get('evidence',{}))
            self.store.put(c,'ledger',state);return p
    @staticmethod
    def close_part(state,p,qty,raw,at,reason):
        cfg=Config(**p['costs']);price=raw*(1-p['side']*(cfg.spread_bps/2+cfg.slip_bps)/10000)
        qty=min(qty,p['remaining']);pnl=p['side']*(price-p['entry'])*qty-price*qty*cfg.fee_bps/10000
        p['pnl']+=pnl;p['remaining']=float(Decimal(str(p['remaining']))-Decimal(str(qty)))
        if p['remaining']<1e-12:p['remaining']=0.;p['status']='CLOSED';p['closed']=str(at)
        ExecutionEngine.event(state,p,reason,at,price,qty,pnl,regime_at_exit=p.get('latest_regime',p['regime']),regime_changed=p['regime_changed'],net_r_multiple=p['pnl']/p['initial_risk'] if p['initial_risk'] else None)
    def protect(self,bars,regime,now,step_minutes=1):
        with self.store.transaction() as c:
            state=self.store.get(c,'ledger',{'positions':[],'events':[],'daily':{},'last_fill':None})
            for p in state['positions']:
                if p['status']!='OPEN':continue
                p['latest_regime']=regime;p['regime_changed']|=regime!=p['regime'] and regime!='UNKNOWN'
                eligible=bars[bars.index>=stamp(p['opened']).ceil(f'{step_minutes}min')]
                if p['last_bar']:eligible=eligible[eligible.index>stamp(p['last_bar'])]
                expected=stamp(p['last_bar'])+pd.Timedelta(minutes=step_minutes) if p['last_bar'] else stamp(p['opened']).ceil(f'{step_minutes}min')
                if len(eligible) and eligible.index[0]>expected:p['gap']=True
                previous=expected-pd.Timedelta(minutes=step_minutes)
                for at,r in eligible.iterrows():
                    if p['status']!='OPEN':break
                    if at>previous+pd.Timedelta(minutes=step_minutes):p['gap']=True
                    previous=at;end=at+pd.Timedelta(minutes=step_minutes)
                    if p['pending'] and at>=stamp(p['pending']['effective']):
                        p['sl']=p['pending']['price'];p['pending']=None;self.event(state,p,'SL_EFFECTIVE',at,p['sl'])
                    hours=(end-stamp(p['last_funding'])).total_seconds()/3600
                    if hours>=8 and p['costs']['funding_bps_8h']:
                        periods=int(hours//8);charge=p['remaining']*float(r.close)*p['costs']['funding_bps_8h']/10000*periods;p['pnl']-=charge
                        p['last_funding']=(stamp(p['last_funding'])+pd.Timedelta(hours=8*periods)).isoformat();self.event(state,p,'ASSUMED_FINANCING',end,pnl=-charge)
                    stop_hit=float(r.low)<=p['sl'] if p['side']==1 else float(r.high)>=p['sl']
                    if stop_hit:
                        raw=min(p['sl'],float(r.open)) if p['side']==1 else max(p['sl'],float(r.open))
                        self.close_part(state,p,p['remaining'],raw,end,'SL')
                    else:
                        for i,target in enumerate(p['targets']):
                            if p['hits'][i]:continue
                            hit=float(r.high)>=target if p['side']==1 else float(r.low)<=target
                            if not hit:break
                            p['hits'][i]=True;self.event(state,p,'TP'+str(i+1),end,target)
                            if i in [0,3]:p['pending']=dict(price=p['targets'][0 if i==0 else 2],effective=end.isoformat())
                            if i==2:self.close_part(state,p,float(Decimal(str(p['original']))/2),target,end,'TP3_HALF')
                            if i==4:self.close_part(state,p,p['remaining'],target,end,'TP5_CLOSE')
                    p['last_bar']=at.isoformat()
            self.store.put(c,'ledger',state)
    def manual_close(self,id,q,now):
        if not quote_valid(q,now):raise ValueError('STALE_QUOTE')
        with self.store.transaction() as c:
            state=self.store.get(c,'ledger')
            for p in state['positions']:
                if p['id']==id and p['status']=='OPEN':self.close_part(state,p,p['remaining'],q['price'],now,'MANUAL_REFERENCE_CLOSE')
            self.store.put(c,'ledger',state)

def run_cycle(store,cfg,q,base,minute,calendar,now=None):
    now=now or utcnow();cfg=store.effective_config(cfg);engine=ExecutionEngine(store)
    x=scalp_features65(base,resample_ohlc_strict(base,'15min',3));regime=str(x.regime15.iloc[-1])
    engine.protect(minute,regime,now) # Must precede every new-entry filter.
    if quote_valid(q,now):
        with store.transaction() as c:
            state=store.get(c,'ledger',{'positions':[],'events':[],'daily':{},'last_fill':None})
            marked=cfg.capital+sum(p['pnl'] for p in state['positions'])+sum(p['side']*(q['price']-p['entry'])*p['remaining']-p['remaining']*q['price']*p['costs']['fee_bps']/10000 for p in state['positions'] if p['status']=='OPEN')
            day=stamp(now).strftime('%Y-%m-%d');daily=state['daily'].get(day,{'start':marked,'peak':marked,'blocked':False})
            daily['peak']=max(daily['peak'],marked)
            if marked<=daily['peak']*(1-cfg.daily_dd_pct/100):daily['blocked']=True
            state['daily'][day]=daily;store.put(c,'ledger',state)
    sig=scalp_signal65(x,preset(),dict(require_volume=cfg.require_volume,session='ALL'))
    news=news_gate65(calendar,now=now,allow_unknown=cfg.allow_no_news)
    result=dict(features=x,quote=q,signal=sig,news=news,regime=regime,plan=None,risk=None,position=None,calendar=calendar)
    reason=sig['reason']
    five_close=base.index[-1]+pd.Timedelta(minutes=5);one_close=minute.index[-1]+pd.Timedelta(minutes=1)
    if not cfg.active:reason='NO_ACTIVE_PRESET'
    elif not 0<=(stamp(now)-five_close).total_seconds()<=360:reason='STALE_5M'
    elif not quote_valid(q,now):reason='STALE_QUOTE'
    elif sig['side']:
        state=store.state();equity=cfg.capital+sum(p['pnl'] for p in state['positions'])
        plan,block=build_plan(sig,x,q,cfg,equity);result['plan']=plan
        if plan:
            plan['news_status']=news['status'];plan['hash']=hash_of({k:v for k,v in plan.items() if k!='hash'})
        if block:reason=block
        else:
            with store.transaction() as c:
                state=store.get(c,'ledger',{'positions':[],'events':[],'daily':{},'last_fill':None})
                risk=RiskEngine.assess(state,plan,q,cfg,now,one_close,news['allowed']);store.put(c,'ledger',state)
            result['risk']=risk
            if risk['approved']:
                # Refresh time/news for the execution recheck in live cycles only.
                execution_now=utcnow() if abs((stamp(utcnow())-stamp(now)).total_seconds())<60 else now
                clear=news_gate65(calendar,now=execution_now,allow_unknown=cfg.allow_no_news)['allowed']
                result['position']=engine.open(plan,risk,q,cfg,execution_now,one_close,clear);reason='PAPER_POSITION_OPENED'
            else:reason='RISK_BLOCK: '+','.join(risk['reasons'])
    result['reason']=reason
    with store.transaction() as c:
        audit=store.get(c,'audit',{});key=f'{five_close.isoformat()}:{VERSION}'
        rec=audit.get(key,dict(time=five_close.isoformat(),attempts=0,signal_seen=False,news_block=False,risk_block=False,filled=False))
        rec['attempts']+=1;rec['reason']=reason;rec['regime']=regime;rec['signal_seen']|=bool(sig['side']);rec['news_block']|=bool(sig['side']) and not news['allowed'];rec['risk_block']|=reason.startswith('RISK_BLOCK');rec['filled']|=result['position'] is not None
        audit[key]=rec;store.put(c,'audit',dict(list(audit.items())[-10000:]))
    return result

def live_cycle(store,cfg):
    with store.transaction() as c:
        h=store.get(c,'health',dict(attempts=0,successes=0,failures=0));h['attempts']+=1;h['status']='RUNNING';h['started']=str(utcnow());store.put(c,'health',h)
    try:
        q,b,m=fetch_market();cal=fetch_calendar65(pd.Timestamp.now(tz='America/New_York').strftime('%Y-%U'));out=run_cycle(store,cfg,q,b,m,cal)
        with store.transaction() as c:
            h=store.get(c,'health');h['successes']+=1;h.update(status='OK',last_success=str(utcnow()),reason=out['reason'],regime=out['regime'],quote_time=q['time'],closed_5m=str(b.index[-1]+pd.Timedelta(minutes=5)),closed_1m=str(m.index[-1]+pd.Timedelta(minutes=1)));store.put(c,'health',h)
        return out
    except Exception:
        with store.transaction() as c:
            h=store.get(c,'health');h['failures']+=1;h.update(status='ERROR',reason='DATA_OR_CYCLE_ERROR');store.put(c,'health',h)
        raise RuntimeError('CYCLE_FAILED: see Health; no raw provider errors are exposed') from None

def chart(x,positions=None):
    from plotly.subplots import make_subplots
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[.6,.25,.15],vertical_spacing=.04)
    fig.add_trace(go.Candlestick(x=x.index,open=x.open,high=x.high,low=x.low,close=x.close,name='Coinbase BTC/USD 5m'),row=1,col=1)
    for k in ['bb_up','bb_mid','bb_dn','ema20','support10','resistance10']:fig.add_trace(go.Scatter(x=x.index,y=x[k],name=k),row=1,col=1)
    fig.add_trace(go.Scatter(x=x.index,y=x.rsi14,name='RSI14'),row=2,col=1)
    fig.add_hline(y=30,row=2,col=1);fig.add_hline(y=70,row=2,col=1)
    fig.add_trace(go.Bar(x=x.index,y=x.volume,name='Coinbase venue volume'),row=3,col=1)
    for p in (positions or [])[-5:]:
        end=stamp(p['closed']) if p['closed'] else max(stamp(utcnow()),x.index[-1])
        if end<x.index[0]:continue
        for name,val in [('Entry',p['entry']),('SL current',p['sl'])]+[(f'TP{i+1}',v) for i,v in enumerate(p['targets'])]:
            fig.add_trace(go.Scatter(x=[max(stamp(p['opened']),x.index[0]),end],y=[val,val],mode='lines',line=dict(dash='dot'),name=f'#{p["id"]} {name}'),row=1,col=1)
    return fig.update_layout(height=480,xaxis_rangeslider_visible=False,margin=dict(l=10,r=10,t=20,b=10))

@st.cache_resource
def db(url):return Store(url)

def synthetic_lab():
    with tempfile.TemporaryDirectory() as tmp:
        store=Store('sqlite:///'+tmp+'/lab.db');cfg=Config(allow_no_news=True,require_volume=False)
        try:
            now=utcnow();q=dict(price=100000.,bid=99999.,ask=100001.,time=str(now),received=str(now))
            # Actual risk -> execution; manufactured setup values, never market data.
            idx=pd.date_range(end=stamp(now).floor('5min')-pd.Timedelta(minutes=5),periods=1200,freq='5min',name='datetime')
            v=100000+np.sin(np.arange(1200)/10)*100
            raw=pd.DataFrame(dict(open=v,high=v+100,low=v-100,close=v+20,volume=10.),index=idx)
            x=scalp_features65(raw,resample_ohlc_strict(raw,'15min',3));at=x.index[-1]
            for k,v in dict(regime15='TREND_UP',rsi14=60.,atr14=600.,resistance10=99700.,support10=99000.,bb_mid=99000.,bb_width=.02,bb_width_previous=.01,body_pct=.7,open=99500.,high=100100.,low=99400.,close=100000.).items():x.loc[at,k]=v
            sig=scalp_signal65(x,preset(),dict(require_volume=False));assert sig['side']==1
            plan,reason=build_plan(sig,x,q,cfg,10000.);assert plan is not None,reason
            state=store.state();risk=RiskEngine.assess(state,plan,q,cfg,now,now,True);assert risk['approved'],risk
            engine=ExecutionEngine(store);p=engine.open(plan,risk,q,cfg,now,now,True)
            start=stamp(now).ceil('min');bars=pd.DataFrame([dict(open=p['entry'],high=p['targets'][2],low=p['entry'],close=p['targets'][2])],index=pd.DatetimeIndex([start]))
            engine.protect(bars,'TREND_UP',start+pd.Timedelta(minutes=1));p=store.state()['positions'][0];assert abs(p['remaining']-p['original']/2)<1e-12
            nextbar=bars.copy();nextbar.index+=pd.Timedelta(minutes=1);nextbar.loc[:,['open','low']]=p['targets'][2];nextbar.loc[:,['high','close']]=p['targets'][4]
            engine.protect(nextbar,'TREND_UP',start+pd.Timedelta(minutes=2));p=store.state()['positions'][0];assert p['status']=='CLOSED'
            return dict(result='PASSED',original_btc=p['original'],tp3_closed_btc=p['original']/2,status=p['status'],events=store.state()['events'])
        finally:store.engine.dispose()

def replay(raw,cfg):
    """Frozen diagnostic only: no historical news; independent simulated ledger."""
    with tempfile.TemporaryDirectory() as tmp:
        store=Store('sqlite:///'+tmp+'/replay.db');engine=ExecutionEngine(store);features=scalp_features65(raw,resample_ohlc_strict(raw,'15min',3));curve=[]
        try:
            cfg=replace(cfg,auto=True,kill=False,active=True,policy='REFERENCE_SIMULATION')
            for i in range(650,len(raw)-1):
                at=raw.index[i];now=at+pd.Timedelta(minutes=5);engine.protect(raw.iloc[i:i+1].set_axis(pd.DatetimeIndex([at])),str(features.regime15.iloc[i]),now,step_minutes=5)
                # This replay uses coarse five-minute bars, not one-minute forward precision.
                if store.state()['positions'] and any(p['status']=='OPEN' for p in store.state()['positions']):
                    curve.append((now,cfg.capital+sum(p['pnl'] for p in store.state()['positions'])));continue
                sig=scalp_signal65(features.iloc[:i+1],preset(),dict(require_volume=cfg.require_volume))
                if sig['side']:
                    price=float(raw.open.iloc[i+1]);q=dict(price=price,bid=None,ask=None,time=str(now),received=str(now))
                    eq=cfg.capital+sum(p['pnl'] for p in store.state()['positions']);plan,block=build_plan(sig,features.iloc[:i+1],q,cfg,eq)
                    if plan:
                        state=store.state();risk=RiskEngine.assess(state,plan,q,cfg,now,now,True)
                        if risk['approved']:engine.open(plan,risk,q,cfg,now,now,True)
                curve.append((now,cfg.capital+sum(p['pnl'] for p in store.state()['positions'])))
            final=raw.iloc[-1];now=raw.index[-1]+pd.Timedelta(minutes=5)
            for p in store.state()['positions']:
                if p['status']=='OPEN':engine.manual_close(p['id'],dict(price=float(final.close),time=str(now),received=str(now)),now)
            state=store.state();return dict(positions=state['positions'],events=state['events'],curve=pd.Series([v for t,v in curve],index=[t for t,v in curve]),pnl=sum(p['pnl'] for p in state['positions']))
        finally:store.engine.dispose()

def ui():
    st.set_page_config(page_title='Bitcoin Intelligence PAPER',page_icon='₿',layout='wide',initial_sidebar_state='collapsed')
    st.title('₿ Bitcoin Intelligence V1 — LONG / SHORT PAPER')
    st.caption('Coinbase BTC/USD reference market · 5m entries / closed 15m regime · UNVALIDATED experimental preset')
    with st.sidebar:
        capital=st.number_input('Starting PAPER equity ($)',100.,1000000.,10000.,100.)
        risk=st.slider('Per-trade risk (%)',.1,2.,.5,.1)
        auto=st.toggle('Auto PAPER',True);kill=st.toggle('Kill switch',False);monitor=st.toggle('Active-session monitoring',True)
        fee=st.number_input('Assumed fee each side (bps)',0.,100.,10.,1.)
        spread=st.number_input('Simulated spread (bps)',0.,100.,2.,1.)
        slip=st.number_input('Slippage each side (bps)',0.,100.,1.,1.)
        policy=st.selectbox('Quote policy',['REFERENCE_SIMULATION','STRICT_EXECUTABLE'])
        vol=st.checkbox('Require Coinbase volume',True)
        newsopt=st.checkbox('Allow PAPER without valid calendar (unprotected)',False)
        funding=st.number_input('Assumed financing cost / 8h (bps; 0 = unmodeled)',0.,100.,0.,1.)
    cfg=Config(capital=capital,risk_pct=risk,fee_bps=fee,spread_bps=spread,slip_bps=slip,policy=policy,auto=auto,kill=kill,require_volume=vol,allow_no_news=newsopt,funding_bps_8h=funding)
    try:
        url=str(st.secrets.get('DATABASE_URL','sqlite:///bitcoin_intelligence_v1.db')) if len(st.secrets) else 'sqlite:///bitcoin_intelligence_v1.db'
    except Exception:url='sqlite:///bitcoin_intelligence_v1.db'
    try:store=db(url)
    except Exception:st.error('Database unavailable. Check DATABASE_URL privately.');st.stop()
    st.warning('SIMULATION ONLY. Spot quotes support a virtual LONG/SHORT ledger; no real short sale, exchange order, margin or liquidation model. No exchange credentials needed.')
    if url.startswith('sqlite'):st.caption('SQLite may be lost on Cloud restart. Export journals; PostgreSQL is preferred. Single-process operation only.')
    tabs=st.tabs(['Live Dashboard','Analysis & Patterns','Regime Engine','Paper Positions','Journal','Performance','Risk Control','News Calendar','Cycle Health','Replay & Lab','Setup'])
    with tabs[0]:
        @st.fragment(run_every='30s' if monitor else None)
        def cycle():
            manual=st.button('Refresh / protective management')
            if monitor or manual:
                try:st.session_state['btc_result']=live_cycle(store,replace(cfg,auto=auto and monitor))
                except Exception:st.error('Cycle failed. See Cycle Health; no new entry was confirmed.')
            h=store.health();a,b,c=st.columns(3);a.metric('Successful cycles',h['successes']);b.metric('Failed cycles',h['failures']);c.metric('Cycle status',h['status'])
            if h.get('last_success'):st.caption('Last success Istanbul: '+str(stamp(h['last_success']).tz_convert('Europe/Istanbul')))
            out=st.session_state.get('btc_result')
            if out:
                st.write('Reason:',out['reason']);st.metric('Reference BTC/USD',f'${out["quote"]["price"]:,.2f}');st.write('Regime:',out['regime'],'Signal:','LONG' if out['signal']['side']==1 else 'SHORT' if out['signal']['side']==-1 else 'NONE')
                if out['plan']:st.json(out['plan'])
                if not out['news']['allowed']:st.warning('News guard blocks new entries; protection still runs with fresh data.')
            if not monitor:st.info('Monitoring stopped. No background execution or protection.')
        cycle()
        with st.expander('TradingView — visual only'):
            import streamlit.components.v1 as components
            components.html('<div id="btc_tv"></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({container_id:"btc_tv",symbol:"COINBASE:BTCUSD",interval:"5",width:"100%",height:450,theme:"light"});</script>',height=460)
    out=st.session_state.get('btc_result');state=store.state();positions=state['positions'];audit=pd.DataFrame(list(store.audits().values()))
    with tabs[1]:
        if out:
            st.plotly_chart(chart(out['features'].tail(160),positions),width='stretch',key='btc_chart')
            rules=diagnostic_rules66(out['features'],preset(),dict(require_volume=cfg.require_volume));st.dataframe(rules,hide_index=True)
            st.download_button('Export current rules',rules.to_csv(index=False),'btc_rules.csv')
        else:st.info('A successful market cycle is required.')
    with tabs[2]:
        if out:st.metric('Current closed-15m regime',out['regime']);st.json(preset()['routes']);st.dataframe(out['features'][['regime15','regime_completeness','adx14','atr14','rsi14']].tail(10))
        st.caption('Feature completeness is not a probability. BTC thresholds are illustrative and not historically validated.')
    with tabs[3]:
        st.dataframe(pd.DataFrame(positions),hide_index=True)
        for p in positions:
            if p['status']=='OPEN' and st.button(f'Manual simulated reference close #{p["id"]}'):
                try:q=parse_quote(api_get('ticker'),utcnow());ExecutionEngine(store).manual_close(p['id'],q,utcnow());st.rerun()
                except Exception:st.error('Manual close not confirmed; fresh provider quote required.')
    with tabs[4]:
        journal=pd.DataFrame(state['events']);st.dataframe(journal,hide_index=True);st.download_button('Export Journal',journal.to_csv(index=False),'btc_forward_journal.csv')
    with tabs[5]:
        pnl=sum(p['pnl'] for p in positions);st.metric('Realized net P/L (includes entry fees)',f'${pnl:,.2f}');st.metric('Closed trades',sum(p['status']=='CLOSED' for p in positions))
        if out:
            exposure=sum(p['remaining']*out['quote']['price'] for p in positions if p['status']=='OPEN');st.metric('Open notional / realized equity',f'{exposure/max(1,cfg.capital+pnl):.2f}x')
        st.caption('Open P/L is not included in realized P/L. No guaranteed target return. Changing starting capital distorts return comparisons.')
    with tabs[6]:
        st.write('Risk-based BTC quantity; at most 1x total notional. Max 2 global / 1 own open positions, 5-minute fill spacing, 2% aggregate risk, 3% daily marked drawdown, duplicates, spread/freshness and kill switch.')
        st.write('TP1 → SL=TP1 next bar; TP2 hold; TP3 close exactly half original BTC; TP4 → SL=TP3 next bar; TP5 close remainder. Stop-first within a candle.')
        active=store.effective_config(cfg).active
        if st.button('Deactivate experimental preset' if active else 'Reactivate UNVALIDATED PAPER preset'):store.set_active(not active);st.rerun()
        st.caption('Deactivation stops new entries, not protective management. No gold 0.03 lot assumption. BTC quantities use even satoshi counts for exact halves.')
    with tabs[7]:
        if out:st.write(out['news']['status']);st.dataframe(out['calendar'].get('events',pd.DataFrame()),hide_index=True)
        st.caption('Scheduled USD/ALL HIGH/MEDIUM releases ±20 minutes. No breaking-news, crypto sentiment, funding-rate or liquidation-feed integration. Missing calendar blocks by default.')
    with tabs[8]:
        h=store.health();st.json(h)
        if h.get('last_success') and (stamp(utcnow())-stamp(h['last_success'])).total_seconds()>120:st.warning('Heartbeat stale; a previous success does not confirm current operation.')
        if len(audit):
            st.dataframe(pd.DataFrame([{'stage':k,'count':int(audit[k].sum())} for k in ['signal_seen','news_block','risk_block','filled']]),hide_index=True);st.write('Unique candle/version checks:',len(audit));st.dataframe(audit.tail(100),hide_index=True);st.download_button('Export decision audit',audit.to_csv(index=False),'btc_decisions.csv')
    with tabs[9]:
        st.caption('Independent lab uses manufactured data in a temporary database. Replay freezes preset rules, uses 5m OHLC and excludes historical news. Neither authorizes a validated model.')
        if st.button('Run independent synthetic lab'):
            try:st.session_state['btc_lab']=synthetic_lab()
            except Exception:st.error('Synthetic lab failed; main positions were untouched.')
        if 'btc_lab' in st.session_state:st.json(st.session_state['btc_lab'])
        if out and st.button('Replay cached BTC bars — base / stress'):
            with st.spinner('Replaying frozen rules...'):
                try:st.session_state['btc_replay']={'base':replay(out['features'][['open','high','low','close','volume']],replace(cfg,fee_bps=10,spread_bps=2,slip_bps=1)),'stress':replay(out['features'][['open','high','low','close','volume']],replace(cfg,fee_bps=20,spread_bps=4,slip_bps=2))}
                except Exception:st.error('Replay incomplete. No main ledger changes.')
        for label,res in st.session_state.get('btc_replay',{}).items():
            st.write(label,'Net P/L:',res['pnl']);st.dataframe(pd.DataFrame(res['positions']),hide_index=True);st.download_button('Export replay '+label,pd.DataFrame(res['positions']).to_csv(index=False),'btc_replay_'+label+'.csv')
    with tabs[10]:
        st.write('Entrypoint: app.py. Coinbase public BTC-USD data needs no API key. Optional DATABASE_URL in Streamlit Secrets. Telegram / cTrader / live execution DISABLED.')
        st.caption('No nested BTC optimization or ML approval is implemented in this first crypto edition. Cloud must remain awake with an active session; this is not a 24/7 daemon.')

if __name__=='__main__':ui()
