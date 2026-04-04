#interpreting questions into better answer

def interpret_price_comparison(results):
    if not results:
        return "No valid price data found."

    best = results[0]
    worst = results[-1]

    return (
        f"{best['region'].title()} offers the highest price at ${best['avg_price']} per bushel. "
        f"In comparison, {worst['region'].title()} offers ${worst['avg_price']}."
    )
