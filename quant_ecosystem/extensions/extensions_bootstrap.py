"""
quant_ecosystem/extensions/extensions_bootstrap.py
===================================================
Extensions Bootstrap — Quant Ecosystem 3.0

Wires the four new extension modules into an existing SystemRouter
WITHOUT modifying any existing engine or factory file.

Call ``bootstrap_extensions(router, config)`` once after the
SystemFactory has built and returned the router.  Each extension
is attached to the router as a new attribute and then started.

Extensions attached
-------------------
    router.telegram_control_center  → TelegramControlCenter
    router.feature_lab              → FeatureLab
    router.mutation_extension       → StrategyMutationExtension
    router.research_status_api      → ResearchStatusAPI

Startup order
-------------
1. FeatureLab              — stateless, no I/O, safe first
2. StrategyMutationExtension — wraps existing mutation engine
3. ResearchStatusAPI       — HTTP server thread (daemon)
4. TelegramControlCenter   — Telegram polling thread (daemon)

Shutdown
--------
Call ``shutdown_extensions(router)`` for a clean teardown in reverse
startup order.  Safe to call even if bootstrap was never called.

Usage
-----
    # After SystemFactory.build():
    from quant_ecosystem.extensions.extensions_bootstrap import (
        bootstrap_extensions,
        shutdown_extensions,
    )

    bootstrap_extensions(router, config)

    # ... trading loop ...

    shutdown_extensions(router)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TAG = "[ext_bootstrap]"


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_extensions(router: Any, config: Any = None) -> None:
    """
    Attach and start all four extension modules on *router*.

    Parameters
    ----------
    router  : SystemRouter  (or any object with the subsystem attributes)
    config  : system config object — read for Telegram token, API port, etc.
              May expose any of:
                  telegram_token
                  telegram_chat_ids
                  api_host / api_port / api_pretty_json
              All settings have safe defaults; passing None is fine.
    """
    logger.info("%s Bootstrapping extensions…", _TAG)

    _bootstrap_feature_lab(router, config)
    _bootstrap_mutation_extension(router, config)
    _bootstrap_research_api(router, config)
    _bootstrap_telegram(router, config)

    logger.info("%s All extensions bootstrapped.", _TAG)


def shutdown_extensions(router: Any) -> None:
    """
    Gracefully stop all extension modules attached to *router*.
    Safe to call multiple times.
    """
    logger.info("%s Shutting down extensions…", _TAG)

    for attr, method in [
        ("telegram_control_center", "stop"),
        ("research_status_api",     "stop"),
    ]:
        obj = getattr(router, attr, None)
        if obj and hasattr(obj, method):
            try:
                getattr(obj, method)()
                logger.info("%s %s stopped.", _TAG, attr)
            except Exception as exc:
                logger.warning("%s Error stopping %s: %s", _TAG, attr, exc)

    logger.info("%s Extension shutdown complete.", _TAG)


# ─────────────────────────────────────────────────────────────────────────────
# Individual bootstrappers
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_feature_lab(router: Any, config: Any) -> None:
    try:
        from quant_ecosystem.feature_lab.feature_lab import FeatureLab, FeatureLabConfig

        cfg = FeatureLabConfig(
            enable_cache      = True,
            default_extractors= True,
        )
        lab = FeatureLab(cfg=cfg)
        router.feature_lab = lab
        logger.info("%s FeatureLab attached (extractors=%s).", _TAG, lab.extractor_names())

    except ImportError:
        # Development fallback: try loading from same directory
        try:
            import importlib.util, os, sys
            here = os.path.dirname(__file__)
            spec = importlib.util.spec_from_file_location(
                "feature_lab",
                os.path.join(here, "..", "feature_lab", "feature_lab.py"),
            )
            if spec:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                lab = mod.FeatureLab()
                router.feature_lab = lab
                logger.info("%s FeatureLab attached (fallback import).", _TAG)
                return
        except Exception:
            pass
        logger.warning("%s FeatureLab not available (import failed).", _TAG)
        router.feature_lab = None

    except Exception as exc:
        logger.error("%s FeatureLab bootstrap failed: %s", _TAG, exc)
        router.feature_lab = None


def _bootstrap_mutation_extension(router: Any, config: Any) -> None:
    try:
        from quant_ecosystem.mutation.strategy_mutation_extension import (
            StrategyMutationExtension,
            MutationExtensionConfig,
        )

        ext_cfg = MutationExtensionConfig(
            enable_regime_bias   = True,
            enable_adaptive_rate = True,
        )
        ext = StrategyMutationExtension(
            base_mutation_engine = getattr(router, "mutation_engine", None),
            regime_engine        = (
                getattr(router, "regime_intelligence", None)
                or getattr(router, "regime_ai_engine",  None)
            ),
            cfg = ext_cfg,
        )
        router.mutation_extension = ext
        logger.info("%s StrategyMutationExtension attached.", _TAG)

    except ImportError:
        logger.warning("%s StrategyMutationExtension not available.", _TAG)
        router.mutation_extension = None
    except Exception as exc:
        logger.error("%s MutationExtension bootstrap failed: %s", _TAG, exc)
        router.mutation_extension = None


def _bootstrap_research_api(router: Any, config: Any) -> None:
    try:
        from quant_ecosystem.api.research_status_api import ResearchStatusAPI, APIConfig

        if config:
            api_cfg = APIConfig(
                host        = str(getattr(config, "api_host",        "127.0.0.1")),
                port        = int(getattr(config, "api_port",        7075)),
                pretty_json = bool(getattr(config, "api_pretty_json", False)),
            )
        else:
            api_cfg = APIConfig()

        api = ResearchStatusAPI(router=router, cfg=api_cfg)
        started = api.start()

        router.research_status_api = api
        if started:
            logger.info("%s ResearchStatusAPI started on %s.", _TAG, api.url)
        else:
            logger.warning("%s ResearchStatusAPI failed to start.", _TAG)

    except ImportError:
        logger.warning("%s ResearchStatusAPI not available.", _TAG)
        router.research_status_api = None
    except Exception as exc:
        logger.error("%s ResearchStatusAPI bootstrap failed: %s", _TAG, exc)
        router.research_status_api = None


def _bootstrap_telegram(router: Any, config: Any) -> None:
    try:
        from quant_ecosystem.telegram.telegram_control_center import (
            TelegramControlCenter,
            TelegramConfig,
        )

        token    = str(getattr(config, "telegram_token",    "") if config else "")
        chat_ids = list(getattr(config, "telegram_chat_ids", []) if config else [])

        if not token:
            logger.info(
                "%s Telegram token not configured — TelegramControlCenter disabled.", _TAG
            )
            router.telegram_control_center = None
            return

        tg_cfg = TelegramConfig(
            bot_token        = token,
            allowed_chat_ids = {int(c) for c in chat_ids},
        )
        center = TelegramControlCenter(cfg=tg_cfg, router=router)
        center.start()

        router.telegram_control_center = center
        # Also wire legacy alias
        if getattr(router, "telegram", None) is None:
            router.telegram = center

        logger.info(
            "%s TelegramControlCenter started (chat_ids=%s).",
            _TAG, chat_ids or "ALL",
        )

    except ImportError:
        logger.warning("%s TelegramControlCenter not available.", _TAG)
        router.telegram_control_center = None
    except Exception as exc:
        logger.error("%s Telegram bootstrap failed: %s", _TAG, exc)
        router.telegram_control_center = None
