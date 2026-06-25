import climateserv.api
from ghoclient import GHO

# Test CHIRPS
print("Testing ClimateSERV for CHIRPS...")
try:
    # CHIRPS dataset ID is usually '0' (CHIRPS) in ClimateSERV, intervaltype=1 (monthly)
    # Let's see if we can get data for Kinshasa
    x, y = 15.307, -4.3224
    geom = f"[[[{x-0.1},{y-0.1}], [{x+0.1},{y-0.1}], [{x+0.1},{y+0.1}], [{x-0.1},{y+0.1}], [{x-0.1},{y-0.1}]]]"
    
    # ClimateSERV API requires a specific format. It might be easier to use requests directly
    # or let's try the library. Actually, let's test GHO first to be safe.
except Exception as e:
    print(f"ClimateSERV test failed: {e}")

print("\nTesting WHO GHO for ITN coverage...")
gho = GHO()
try:
    indicators = gho.search_indicators('ITN')
    for code, title in indicators.items():
        if 'malaria' in title.lower() or 'itn' in title.lower():
            print(f"{code}: {title}")
except Exception as e:
    print(f"GHO test failed: {e}")
