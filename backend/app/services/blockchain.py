class BlockchainService:
    def __init__(self):
        # Simulated price data; replace with Coingecko client in prod
        self._prices = {"bitcoin": 50000.0, "ethereum": 3000.0}

    def get_price(self, coin: str) -> float:
        return float(self._prices.get(coin.lower(), 0.0))

    def simulate_update(self, coin: str, price: float) -> bool:
        self._prices[coin.lower()] = float(price)
        return True
