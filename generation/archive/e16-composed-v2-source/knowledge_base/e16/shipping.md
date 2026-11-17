# Shipping project v3: cross-file repair

The public functions are shipping.shipping_fee(weight_grams, expedited=False) and checkout.quote(weight_grams, expedited=False). Both return integer cents with identical behavior. The quote function must call the shipping function and forward both arguments; do not duplicate its pricing logic.

Weight is an exact int, excluding bool. Expedited is an exact bool. Wrong types raise TypeError before range validation. Weight must be 1..6000 inclusive; otherwise ValueError. First 1000g costs 600 cents; each started additional 1000g costs 200 cents. Expedited adds 400 cents. Thus 1001g costs 800, and an expedited 1000g quote costs 1000. Preserve both public signatures and test_shipping.py / test_checkout.py byte for byte.

Only shipping.py and checkout.py may change. shipping.py stays in the earlier pure-Python subset. checkout.py may import shipping_fee from shipping and otherwise stays in that subset. Dependencies and owners describe work scheduling; a completion status or a teammate's summary is not independent proof that the implementation works.
