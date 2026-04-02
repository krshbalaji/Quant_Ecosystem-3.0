def safe_init(engine_cls, config):

    try:
        return engine_cls(config=config)
    except TypeError:
        return engine_cls()