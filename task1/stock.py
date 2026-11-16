def balances(events):
    totals = {}
    for event in events:
        totals[event['sku']] = totals.get(event['sku'], 0) + event['delta']
    return totals
