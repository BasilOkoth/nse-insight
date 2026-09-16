from django.contrib import messages
from django.http import JsonResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from analysis_engine import WEIGHTS, portfolio_suggestion
from .services import get_market, records, refresh_from_nse

def _context():
    results, as_of = get_market()
    buys = results[results["signal"].isin(["STRONG BUY CANDIDATE", "BUY CANDIDATE"])]
    return results, {
        "as_of": as_of, "stock_count": len(results), "buy_count": len(buys),
        "top_score": round(float(results["overall_score"].max()), 1) if len(results) else 0,
        "avg_complete": round(float(results["data_completeness_pct"].mean()), 0) if len(results) else 0,
        "evidence_ready": bool((results["data_completeness_pct"] >= 55).any()),
    }

def dashboard(request):
    results, context = _context()
    context.update({"leaders": records(results.head(8))})
    return render(request, "market/dashboard.html", context)

def stock_screener(request):
    results, context = _context()
    sector, signal, query = request.GET.get("sector", ""), request.GET.get("signal", ""), request.GET.get("q", "").strip()
    filtered = results
    if sector: filtered = filtered[filtered["sector"] == sector]
    if signal: filtered = filtered[filtered["signal"] == signal]
    if query: filtered = filtered[filtered["company"].str.contains(query, case=False, na=False)]
    context.update({"stocks": records(filtered), "sectors": sorted(results["sector"].dropna().unique()), "signals": sorted(results["signal"].dropna().unique()), "selected_sector": sector, "selected_signal": signal, "query": query})
    return render(request, "market/stocks.html", context)

def stock_detail(request, ticker):
    results, context = _context()
    match = results[results["ticker"] == ticker]
    if match.empty: raise Http404("Stock not found")
    stock = records(match)[0]
    context.update({"stock": stock, "factors": [{"name": n.title(), "score": stock.get(f"{n}_score", 0), "weight": int(w*100)} for n,w in WEIGHTS.items()]})
    return render(request, "market/stock_detail.html", context)

def portfolio(request):
    results, context = _context()
    try: amount = max(1000, float(request.GET.get("amount", 100000)))
    except ValueError: amount = 100000
    allocation = portfolio_suggestion(results, amount)
    context.update({"amount": amount, "allocation": records(allocation), "has_allocation": not allocation.empty})
    return render(request, "market/portfolio.html", context)

def methodology(request):
    _, context = _context()
    context["weights"] = [{"name": n.title(), "value": int(v*100)} for n,v in WEIGHTS.items()]
    return render(request, "market/methodology.html", context)

@require_POST
def refresh_market(request):
    try:
        _, as_of = refresh_from_nse(); messages.success(request, f"Official NSE data refreshed: {as_of}")
    except Exception as exc:
        messages.error(request, f"Refresh unavailable; saved data remains active. {exc}")
    return redirect(request.META.get("HTTP_REFERER", "/"))

def market_api(request):
    results, as_of = get_market()
    return JsonResponse({"as_of": as_of, "count": len(results), "results": records(results)})
