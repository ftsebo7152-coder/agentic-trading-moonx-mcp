"""Readiness inspection without creating entries or financial attestations."""
from dataclasses import asdict
from ..models import Instrument,TradingError,utc,fingerprint
from ..permissions import verify_evidence
from ..fundamentals import context_at
from ..universe import identity_error
from .engine import parse_markets,liquidity_check
from .timeframes import closed_bars,INTERVALS,confirmation


def preflight(settings,policy,bundle,now,costs):
    results=[];policy_hash=fingerprint(asdict(policy))
    universe=bundle.get('collection',{}).get('universe') or {'requested':settings.universe,'identities':{}}
    for symbol in universe.get('symbols',settings.watchlist):
        if symbol in universe.get('excluded',{}):
            results.append({'symbol':symbol,'status':'EXCLUDED','reasons':[universe['excluded'][symbol]],'qualified_strategies':[]});continue
        reasons=[];base=[];higher=[]
        try:
            base=closed_bars(parse_markets({symbol:bundle.get('markets',{}).get(symbol,[])})[symbol],now,INTERVALS[policy.base_interval],
                             continuous=policy.asset_class(symbol)=='crypto',minimum=policy.minimum_base_bars)
            if (utc(now)-base[-1].time).total_seconds()>policy.maximum_signal_age_seconds:reasons.append('BASE_TIMEFRAME_STALE')
            higher=parse_markets({symbol:bundle.get('higher_markets',{}).get(symbol,[])})[symbol]
            checks=[confirmation(higher,side,now,INTERVALS[policy.higher_interval],continuous=policy.asset_class(symbol)=='crypto',minimum=policy.minimum_higher_bars) for side in ('LONG','SHORT')]
            if not any(c.get('asof') for c in checks):reasons.append('HIGHER_TIMEFRAME_UNAVAILABLE_OR_STALE')
            spec=Instrument(symbol=symbol,**bundle.get('instruments',{})[symbol])
            if not spec.specs_verified:reasons.append('CONTRACT_SPECS_UNVERIFIED')
        except (KeyError,ValueError,TypeError) as exc:reasons.append(str(exc))
        if not liquidity_check(bundle.get('liquidity',{}).get(symbol,{}),policy.asset_class(symbol),now,settings.limits.max_data_age_seconds,costs):reasons.append('EXECUTABLE_LIQUIDITY_OR_COST_MODEL_UNQUALIFIED')
        macro=bundle.get('macro',{})
        try:
            context=context_at(macro.get('observations',[]),macro.get('events',[]),now,calendar_asof=macro.get('calendar_asof'),coverage_until=macro.get('coverage_until'),symbol=symbol)
            if context['blackout'] or context['status']!='OBSERVED':reasons.append('MACRO_CONTEXT_OR_CALENDAR_UNQUALIFIED')
        except (KeyError,ValueError,TypeError):reasons.append('MACRO_CONTEXT_INVALID')
        meta=bundle.get('market_metadata',{}).get(symbol,{})
        if not meta.get('basis') or not meta.get('source') or not meta.get('fetched_at'):reasons.append('MARKET_PROVENANCE_REQUIRED')
        else:
            try:
                if utc(meta['fetched_at'])>utc(now) or meta.get('base_interval')!=policy.base_interval or meta.get('higher_interval')!=policy.higher_interval:
                    reasons.append('MARKET_TIMEFRAME_OR_AVAILABILITY_INVALID')
            except (ValueError,TypeError,AttributeError):reasons.append('MARKET_AVAILABILITY_INVALID')
        identity=identity_error(symbol,universe,bundle.get('asset_identities',{}).get(symbol))
        if identity:reasons.append(identity)
        if settings.universe=='cmc_top100' and universe.get('status')!='CMC_TOP100_PLUS_PINNED':reasons.append('CURRENT_CMC_UNIVERSE_UNAVAILABLE')
        if settings.universe=='cmc_top100':
            try:
                if not 0<=(utc(now)-utc(universe['asof'])).total_seconds()<=3600:reasons.append('CURRENT_CMC_UNIVERSE_STALE')
            except (KeyError,ValueError,TypeError,AttributeError):reasons.append('CURRENT_CMC_UNIVERSE_TIMESTAMP_REQUIRED')
        proofs=bundle.get('validation',{}).get(symbol,{}).get('strategies',{})
        qualified=[s for s in policy.strategies if verify_evidence(proofs.get(s,{}),symbol,s,now) and proofs[s].get('policy_hash')==policy_hash and proofs[s].get('basis')==meta.get('basis')]
        if not qualified:reasons.append('NO_INDEPENDENT_STRATEGY_ATTESTATION')
        results.append({'symbol':symbol,'status':'PAPER_INPUTS_QUALIFIED' if not reasons else 'NOT_READY','reasons':reasons,
                        'qualified_strategies':qualified,'base_bars':len(base),'higher_bars':len(higher)})
    return {'mode':'PAPER','policy_hash':policy_hash,'assets':results,'universe_status':universe.get('status','STATIC_OR_CMC_UNAVAILABLE'),
            'all_requested_inputs_qualified':bool(results) and any(r['status']=='PAPER_INPUTS_QUALIFIED' for r in results) and all(r['status'] in ('PAPER_INPUTS_QUALIFIED','EXCLUDED') for r in results),
            'financial_qualification_created':False,'real_orders_enabled':False}
