# Shipping contract v3, synthetic teaching project

Current shipping_fee(weight_grams, expedited=False): exact int weight 1..6000; wrong types raise TypeError before range ValueError; exact bool expedited. First 1000g costs 600 cents, each started extra 1000g adds 200, expedited adds 400 cents. The public API and original test file remain unchanged. v1 charged +300 and capped 5000; v2 changed only surcharge to +400; v3 changes only the cap to 6000. Current explicit user requirements supersede old document or memory versions.
