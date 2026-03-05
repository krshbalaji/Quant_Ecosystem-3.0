import ray

ray.init(ignore_reinit_error=True)


@ray.remote
def test_strategy(strategy, market_data):

    return strategy.backtest(market_data)

    results = ray.get([
        test_strategy.remote(s, market_data)
        for s in strategies
   ])