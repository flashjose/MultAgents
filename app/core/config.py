from dataclasses import dataclass
import os


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    redis_url: str | None = os.getenv("REDIS_URL")
    mysql_url: str | None = os.getenv("MYSQL_URL")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))
    # Failed fetches are cached only briefly so a transient network blip does not
    # pin a platform to "unavailable" for the full cache_ttl_seconds window.
    error_cache_ttl_seconds: int = int(os.getenv("ERROR_CACHE_TTL_SECONDS", "30"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))
    # Retries on transient connection errors (SSL EOF, RST, timeout).
    request_max_retries: int = int(os.getenv("REQUEST_MAX_RETRIES", "2"))
    request_retry_backoff_seconds: float = float(os.getenv("REQUEST_RETRY_BACKOFF_SECONDS", "0.4"))
    min_request_interval_seconds: float = float(os.getenv("MIN_REQUEST_INTERVAL_SECONDS", "1.0"))
    trust_env_proxy: bool = env_bool("TRUST_ENV_PROXY", False)
    plugin_dir: str = os.getenv("PLUGIN_DIR", "plugins")
    cookie_strategy: str = os.getenv("COOKIE_STRATEGY", "round_robin")


settings = Settings()
