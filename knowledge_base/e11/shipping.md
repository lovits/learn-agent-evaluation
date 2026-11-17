# Shipping contract v1 (synthetic teaching project)

shipping_fee(weight_grams, expedited=False) returns an integer number of cents.
weight_grams must have exact type int (bool is not accepted); expedited must have exact type bool. Wrong types raise TypeError before range validation. Valid weights are 1 through 5000 grams, inclusive; other integers raise ValueError. The first 1000 grams cost 600 cents. Each started additional 1000 grams costs 200 cents. Expedited delivery adds 300 cents. Preserve the signature and the supplied test_shipping.py. The module is pure Python without imports or IO.
