"""
Configuration Usage Analysis Report

This file contains a comprehensive analysis of configuration module usage patterns
across the discord-ai-bot-czech project, including dependency graphs and migration
impact assessment.

Generated: 2026-03-15
"""

from typing import Dict, List, Any, Set
from dataclasses import dataclass, field


@dataclass
class ConfigModule:
    """Represents a configuration module in the codebase."""

    path: str
    classes: List[str]
    methods: List[str]
    fields: List[str]
    dependencies: Set[str] = field(default_factory=set)
    dependent_modules: Set[str] = field(default_factory=set)


@dataclass
class UsagePattern:
    """Represents how a config class is used in the codebase."""

    config_class: str
    instantiation_pattern: str
    import_locations: List[str]
    access_patterns: List[str]
    dependency_injection: bool


@dataclass
class MigrationImpact:
    """Assessment of migration impact for configuration consolidation."""

    module_path: str
    affected_files: List[str]
    breaking_changes: List[str]
    recommended_actions: List[str]
    risk_level: str  # "low", "medium", "high"


# ============================================================================
# Configuration Modules Inventory
# ============================================================================

CONFIG_MODULES: Dict[str, ConfigModule] = {
    "config.py": ConfigModule(
        path="config.py",
        classes=["Config"],
        methods=[
            "validate() -> bool",
            "get_available_providers() -> list[str]"
        ],
        fields=[
            "DISCORD_TOKEN: str",
            "BOT_PREFIX: str",
            "ANTHROPIC_API_KEY: str",
            "GOOGLE_API_KEY: str",
            "OPENAI_API_KEY: str",
            "DEFAULT_AI_PROVIDER: str"
        ],
        dependencies={"dotenv", "os", "typing"},
        dependent_modules={"bot.py"}
    ),

    "src/config.py": ConfigModule(
        path="src/config.py",
        classes=["Settings"],
        methods=[
            "model_post_init(__context) -> None",
            "has_any_ai_key() -> bool",
            "get_available_providers() -> list[str]"
        ],
        fields=[
            "discord_bot_token: str",
            "discord_channel_id: Optional[str]",
            "anthropic_api_key: Optional[str]",
            "claude_api_key: Optional[str]",
            "google_api_key: Optional[str]",
            "openai_api_key: Optional[str]",
            "bot_prefix: str",
            "bot_language: str",
            "log_level: str",
            "admin_username: str",
            "admin_password: str",
            "secret_key: str"
        ],
        dependencies={"pydantic", "pydantic_settings", "dotenv", "pathlib"},
        dependent_modules={
            "src/llm/factory.py",
            "src/api/auth.py",
            "app.py",
            "examples/configuration_usage.py",
            "examples/llm_client_example.py",
            "tests/test_llm_factory.py",
            "tests/test_config_management.py",
            "tests/test_auth.py",
            "tests/test_language_configuration.py",
            "tests/test_admin_auth.py"
        }
    ),

    "bot/config.py": ConfigModule(
        path="bot/config.py",
        classes=["BotConfig"],
        methods=[
            "model_post_init(__context) -> None",
            "_ensure_directories() -> None",
            "_validate_log_level(v: str) -> str",
            "_validate_language(v: str) -> str",
            "get_channel_ids() -> List[int]",
            "has_ai_provider(provider: str) -> bool",
            "get_available_providers() -> List[str]",
            "__repr__() -> str"
        ],
        fields=[
            "discord_bot_token: str",
            "discord_guild_id: Optional[int]",
            "discord_channel_ids: Optional[str]",
            "anthropic_api_key: Optional[str]",
            "google_api_key: Optional[str]",
            "openai_api_key: Optional[str]",
            "bot_response_threshold: float",
            "bot_max_history: int",
            "bot_language: str",
            "bot_personality: str",
            "database_url: str",
            "log_level: str",
            "log_file: str",
            "api_host: str",
            "api_port: int",
            "secret_key: str",
            "admin_username: str",
            "admin_password: str"
        ],
        dependencies={"pydantic", "pydantic_settings", "pathlib", "typing"},
        dependent_modules={"bot/__init__.py"}
    ),

    "bot/config_loader.py": ConfigModule(
        path="bot/config_loader.py",
        classes=["Environment", "ConfigValidationError", "AdvancedBotConfig", "ConfigLoader"],
        methods=[
            # Environment enum
            # ConfigValidationError exception
            # AdvancedBotConfig methods
            "model_post_init(__context) -> None",
            "_validate_production_config() -> None",
            "_ensure_directories() -> None",
            "_validate_log_level(v: str) -> str",
            "_validate_environment(v: Any) -> Environment",
            "_validate_language(v: str) -> str",
            "get_channel_ids() -> List[int]",
            "has_any_ai_key() -> bool",
            "has_ai_provider(provider: str) -> bool",
            "get_available_providers() -> List[str]",
            "is_production() -> bool",
            "is_development() -> bool",
            "to_dict(include_secrets: bool) -> Dict[str, Any]",
            "__repr__() -> str",
            # ConfigLoader methods
            "load(env_file: Optional[str]) -> AdvancedBotConfig",
            "_load_yaml_config(environment: str) -> Dict[str, Any]",
            "reload() -> AdvancedBotConfig",
            "get_config() -> Optional[AdvancedBotConfig]",
            # Module-level function
            "load_config(env_file, config_dir) -> AdvancedBotConfig"
        ],
        fields=[
            # All fields from BotConfig plus:
            "environment: Environment",
            "max_retry_attempts: int",
            "retry_base_delay: float",
            "retry_max_delay: float",
            "retry_exponential_base: float",
            "http_timeout: float",
            "llm_timeout: float",
            "discord_timeout: float",
            "enable_auto_reconnect: bool",
            "max_reconnect_attempts: int",
            "reconnect_base_delay: float",
            "enable_message_caching: bool",
            "enable_graceful_degradation: bool",
            "enable_health_checks: bool",
            "enable_metrics: bool",
            "message_queue_size: int",
            "worker_threads: int",
            "cache_ttl: int"
        ],
        dependencies={
            "pydantic",
            "pydantic_settings",
            "pathlib",
            "typing",
            "yaml",
            "enum",
            "bot.utils.logger"
        },
        dependent_modules={
            "main.py",
            "main_enhanced.py",
            "examples/config_error_handling_example.py",
            "tests/test_config_loader.py"
        }
    ),

    "src/api/config.py": ConfigModule(
        path="src/api/config.py",
        classes=[
            "ConfigDiscordUpdate",
            "ConfigAIUpdate",
            "ConfigBehaviorUpdate",
            "ConfigUpdate",
            "ConfigResponse",
            "ConfigSecretResponse",
            "ValidationResult"
        ],
        methods=[
            # Pydantic model validators
            "validate_channel_ids(v: Optional[str]) -> Optional[str]",
            "validate_language(v: Optional[str]) -> Optional[str]",
            # Helper functions
            "mask_secret(value: Optional[str], show_chars: int) -> Optional[str]",
            # API endpoints
            "get_config(settings: Settings) -> ConfigResponse",
            "get_config_secrets(current_user, settings) -> ConfigSecretResponse",
            "update_config(config, current_user) -> Dict[str, str]",
            "update_discord_config(config, current_user) -> Dict[str, str]",
            "update_ai_config(config, current_user) -> Dict[str, str]",
            "update_behavior_config(config, current_user) -> Dict[str, str]",
            "reload_config(current_user) -> Dict[str, str]",
            "hot_reload_bot_config(current_user) -> Dict[str, Any]",
            "validate_config(settings) -> ValidationResult",
            "export_config(current_user, mask_secrets) -> Dict[str, Any]"
        ],
        fields=[],  # FastAPI router, not a config storage
        dependencies={
            "fastapi",
            "pydantic",
            "pathlib",
            "yaml",
            "src.config",
            "src.api.auth",
            "src.shared_config",
            "src.ipc"
        },
        dependent_modules={"app.py"}
    ),

    "src/config_loader.py": ConfigModule(
        path="src/config_loader.py",
        classes=[],
        methods=[],
        fields=[],
        dependencies={},
        dependent_modules={},
        # Note: This file redirects to bot/config_loader.py
    )
}


# ============================================================================
# Usage Patterns Analysis
# ============================================================================

USAGE_PATTERNS: List[UsagePattern] = [
    UsagePattern(
        config_class="Config",
        instantiation_pattern="Class variables (no instantiation needed)",
        import_locations=["bot.py"],
        access_patterns=[
            "Config.DISCORD_TOKEN",
            "Config.validate()",
            "Config.get_available_providers()"
        ],
        dependency_injection=False
    ),

    UsagePattern(
        config_class="Settings",
        instantiation_pattern="Pydantic BaseSettings - auto-loaded from environment",
        import_locations=[
            "src/llm/factory.py",
            "src/api/auth.py",
            "app.py",
            "examples/configuration_usage.py",
            "examples/llm_client_example.py",
            "tests/*.py"
        ],
        access_patterns=[
            "settings = get_settings()  # Dependency injection",
            "settings = Settings()  # Direct instantiation",
            "settings.anthropic_api_key",
            "settings.bot_language",
            "settings.has_any_ai_key()",
            "settings.get_available_providers()"
        ],
        dependency_injection=True  # Via get_settings() function
    ),

    UsagePattern(
        config_class="BotConfig",
        instantiation_pattern="Pydantic BaseSettings - auto-loaded from environment",
        import_locations=["bot/__init__.py"],
        access_patterns=[
            "from bot.config import BotConfig",
            "config.get_channel_ids()",
            "config.has_ai_provider('anthropic')"
        ],
        dependency_injection=False
    ),

    UsagePattern(
        config_class="AdvancedBotConfig",
        instantiation_pattern="Loaded via ConfigLoader or load_config() function",
        import_locations=[
            "main.py",
            "main_enhanced.py",
            "examples/config_error_handling_example.py",
            "tests/test_config_loader.py"
        ],
        access_patterns=[
            "config = load_config(env_file='.env')",
            "loader = ConfigLoader()",
            "config = loader.load()",
            "config = AdvancedBotConfig(**config_dict)",
            "config.discord_bot_token",
            "config.log_level",
            "config.get_available_providers()",
            "config.is_production()",
            "config.to_dict(include_secrets=False)"
        ],
        dependency_injection=False
    ),

    UsagePattern(
        config_class="ConfigUpdate (API models)",
        instantiation_pattern="FastAPI Pydantic models for request validation",
        import_locations=["src/api/config.py", "app.py"],
        access_patterns=[
            "async def update_config(config: ConfigUpdate, ...)",
            "config.model_dump(exclude_unset=True)",
            "Used for API request/response validation"
        ],
        dependency_injection=True  # Via FastAPI Depends()
    )
]


# ============================================================================
# Dependency Graph
# ============================================================================

DEPENDENCY_GRAPH: Dict[str, Dict[str, Any]] = {
    "config.py": {
        "type": "legacy_class_based",
        "imports_from": [],
        "imported_by": ["bot.py"],
        "provides": ["Config class"],
        "status": "deprecated - simple env wrapper"
    },

    "src/config.py": {
        "type": "pydantic_settings",
        "imports_from": ["pydantic", "pydantic_settings", "dotenv"],
        "imported_by": [
            "src/llm/factory.py",
            "src/api/auth.py",
            "src/api/config.py",
            "app.py",
            "examples/configuration_usage.py",
            "examples/llm_client_example.py",
            "tests/test_llm_factory.py",
            "tests/test_config_management.py",
            "tests/test_auth.py"
        ],
        "provides": [
            "Settings class",
            "get_settings() function (referenced but missing)",
            "get_config_manager() function (referenced but missing)",
            "reload_settings() function (referenced but missing)",
            "BotSettings class (referenced but missing)"
        ],
        "status": "incomplete - missing dependency injection functions"
    },

    "bot/config.py": {
        "type": "pydantic_settings",
        "imports_from": ["pydantic", "pydantic_settings"],
        "imported_by": ["bot/__init__.py"],
        "provides": ["BotConfig class"],
        "status": "functional - similar to src/config.py Settings"
    },

    "bot/config_loader.py": {
        "type": "advanced_config_system",
        "imports_from": [
            "pydantic",
            "pydantic_settings",
            "yaml",
            "enum",
            "bot.utils.logger"
        ],
        "imported_by": [
            "main.py",
            "main_enhanced.py",
            "examples/config_error_handling_example.py",
            "tests/test_config_loader.py"
        ],
        "provides": [
            "AdvancedBotConfig class",
            "ConfigLoader class",
            "load_config() function",
            "Environment enum",
            "ConfigValidationError exception"
        ],
        "status": "most feature-complete - production ready"
    },

    "src/api/config.py": {
        "type": "fastapi_router",
        "imports_from": [
            "src.config",
            "src.api.auth",
            "src.shared_config",
            "src.ipc",
            "fastapi",
            "pydantic"
        ],
        "imported_by": ["app.py"],
        "provides": [
            "FastAPI router for config management",
            "API request/response models",
            "Configuration CRUD endpoints"
        ],
        "status": "functional - depends on missing src/config functions"
    },

    "src/config_loader.py": {
        "type": "redirect",
        "imports_from": [],
        "imported_by": [],
        "provides": ["Redirects to bot/config_loader.py"],
        "status": "redundant file"
    }
}


# ============================================================================
# Field/Method Usage Mapping
# ============================================================================

FIELD_USAGE: Dict[str, List[str]] = {
    # Discord configuration
    "discord_bot_token": [
        "main.py:391 - validation check",
        "main.py:408,424 - bot.start_with_lifecycle()",
        "main_enhanced.py:283 - validation",
        "main_enhanced.py:298 - bot.start()"
    ],
    "discord_channel_id": [
        "src/config.py:34 - field definition",
        # Not heavily used
    ],
    "discord_channel_ids": [
        "bot/config.py:40 - field definition",
        "bot/config_loader.py:76 - field definition",
        "Used via get_channel_ids() method"
    ],

    # AI API keys
    "anthropic_api_key": [
        "src/llm/factory.py:55 - client initialization",
        "main_enhanced.py:135 - LLM client creation",
        "tests/test_llm_factory.py - testing",
        "Used in get_available_providers() logic"
    ],
    "google_api_key": [
        "src/llm/factory.py:56 - client initialization",
        "main_enhanced.py:136 - LLM client creation",
        "tests/test_llm_factory.py - testing",
        "Used in get_available_providers() logic"
    ],
    "openai_api_key": [
        "src/llm/factory.py:57 - client initialization",
        "main_enhanced.py:137 - LLM client creation",
        "tests/test_llm_factory.py - testing",
        "Used in get_available_providers() logic"
    ],
    "claude_api_key": [
        "src/config.py:38 - alias for anthropic_api_key",
        "src/config.py:57-58 - model_post_init() resolution"
    ],

    # Bot behavior
    "bot_language": [
        "src/llm/factory.py:51 - language resolution",
        "main_enhanced.py:140 - LLM client initialization",
        "tests/test_llm_factory.py:29,96,112,124,136 - testing",
        "examples/security_usage.py:65 - display",
        "examples/configuration_usage.py - display"
    ],
    "bot_prefix": [
        "config.py:19 - legacy Config class",
        "src/config.py:43 - Settings field"
    ],
    "bot_response_threshold": [
        "bot/config.py:60-64 - field with validation",
        "bot/config_loader.py:86 - AdvancedBotConfig field"
    ],
    "bot_max_history": [
        "bot/config.py:66-70 - field with validation",
        "bot/config_loader.py:87 - AdvancedBotConfig field"
    ],
    "bot_personality": [
        "bot/config.py:76-78 - field definition",
        "bot/config_loader.py:89 - AdvancedBotConfig field"
    ],

    # Logging
    "log_level": [
        "main.py:201,387 - logger setup",
        "main_enhanced.py:275 - logger setup",
        "examples/configuration_usage.py:52,66,293 - usage",
        "test_fastapi_setup.py:55 - display",
        "Validated via validate_log_level() method"
    ],
    "log_file": [
        "bot/config.py:92-94 - field definition",
        "main.py:201,387 - logger setup",
        "main_enhanced.py:275 - logger setup"
    ],

    # Admin/API
    "admin_username": [
        "src/config.py:48 - field definition",
        "bot/config.py:112-114 - field definition"
    ],
    "admin_password": [
        "src/config.py:49 - field definition",
        "bot/config.py:115-118 - field definition"
    ],
    "secret_key": [
        "src/config.py:50-52 - field definition",
        "bot/config.py:108-111 - field definition"
    ],
    "api_host": [
        "bot/config.py:98-100 - field definition",
        "bot/config_loader.py:99 - AdvancedBotConfig field",
        "app.py:68 - display"
    ],
    "api_port": [
        "bot/config.py:102-107 - field with validation",
        "bot/config_loader.py:100 - AdvancedBotConfig field",
        "app.py:68 - display"
    ]
}

METHOD_USAGE: Dict[str, List[str]] = {
    "get_available_providers()": [
        "config.py - Config.get_available_providers() classmethod",
        "src/config.py:69-78 - Settings method",
        "bot/config.py:238-252 - BotConfig method",
        "bot/config_loader.py:291-305 - AdvancedBotConfig method",
        "bot.py:36 - usage",
        "main_enhanced.py:148,279 - usage",
        "examples/config_error_handling_example.py:46 - usage",
        "examples/llm_client_example.py:117 - usage",
        "examples/enhanced_client_lifecycle_example.py:56 - client method"
    ],

    "has_any_ai_key()": [
        "src/config.py:60-67 - Settings method",
        "bot/config_loader.py:266-272 - AdvancedBotConfig method",
        "src/llm/factory.py:44 - validation check",
        "examples/llm_client_example.py:163 - validation"
    ],

    "has_ai_provider(provider: str)": [
        "bot/config.py:221-236 - BotConfig method",
        "bot/config_loader.py:274-289 - AdvancedBotConfig method"
    ],

    "get_channel_ids()": [
        "bot/config.py:200-219 - BotConfig method",
        "bot/config_loader.py:247-264 - AdvancedBotConfig method",
        "examples/configuration_usage.py:53 - usage"
    ],

    "model_post_init(__context)": [
        "src/config.py:54-58 - Settings method (API key alias resolution)",
        "bot/config.py:165-186 - BotConfig method (validation + directory creation)",
        "bot/config_loader.py:201-220 - AdvancedBotConfig method (full validation)"
    ],

    "validate()": [
        "config.py:29-45 - Config.validate() classmethod"
    ],

    "is_production()": [
        "bot/config_loader.py:307-309 - AdvancedBotConfig method"
    ],

    "is_development()": [
        "bot/config_loader.py:311-313 - AdvancedBotConfig method"
    ],

    "to_dict(include_secrets: bool)": [
        "bot/config_loader.py:315-341 - AdvancedBotConfig method"
    ],

    "load_config()": [
        "bot/config_loader.py:465-482 - module function",
        "main.py:375 - fallback config loading",
        "examples/config_error_handling_example.py:41,234 - usage"
    ]
}


# ============================================================================
# Migration Impact Analysis
# ============================================================================

MIGRATION_IMPACTS: List[MigrationImpact] = [
    MigrationImpact(
        module_path="config.py",
        affected_files=["bot.py"],
        breaking_changes=[
            "Config class removal",
            "Class-based config access pattern deprecated"
        ],
        recommended_actions=[
            "Update bot.py to use AdvancedBotConfig from bot/config_loader.py",
            "Replace Config.DISCORD_TOKEN with config.discord_bot_token",
            "Replace Config.get_available_providers() with config.get_available_providers()"
        ],
        risk_level="low"
    ),

    MigrationImpact(
        module_path="src/config.py",
        affected_files=[
            "src/llm/factory.py",
            "src/api/auth.py",
            "src/api/config.py",
            "app.py",
            "examples/configuration_usage.py",
            "examples/llm_client_example.py",
            "tests/test_llm_factory.py",
            "tests/test_config_management.py",
            "tests/test_auth.py",
            "tests/test_language_configuration.py",
            "tests/test_admin_auth.py"
        ],
        breaking_changes=[
            "Missing functions: get_settings(), get_config_manager(), reload_settings(), BotSettings class",
            "Settings class incomplete compared to AdvancedBotConfig",
            "Dependency injection pattern incomplete"
        ],
        recommended_actions=[
            "Add missing dependency injection functions to src/config.py",
            "Implement get_settings() as singleton or factory function",
            "Implement get_config_manager() for dynamic config updates",
            "Implement reload_settings() for hot-reloading",
            "OR merge Settings into AdvancedBotConfig and update all imports",
            "Update src/api/config.py imports to match actual available exports"
        ],
        risk_level="high"
    ),

    MigrationImpact(
        module_path="bot/config.py",
        affected_files=["bot/__init__.py"],
        breaking_changes=[
            "BotConfig class removal or merge",
            "Potential field differences with AdvancedBotConfig"
        ],
        recommended_actions=[
            "Compare BotConfig and AdvancedBotConfig field sets",
            "Merge BotConfig into AdvancedBotConfig if fields overlap",
            "Update bot/__init__.py to import from bot/config_loader.py"
        ],
        risk_level="medium"
    ),

    MigrationImpact(
        module_path="bot/config_loader.py",
        affected_files=[
            "main.py",
            "main_enhanced.py",
            "examples/config_error_handling_example.py",
            "tests/test_config_loader.py"
        ],
        breaking_changes=[
            "This is the target consolidation module - minimal changes expected",
            "May need to add missing fields from other config classes"
        ],
        recommended_actions=[
            "Verify AdvancedBotConfig has all fields from Settings, BotConfig, Config",
            "Add any missing fields with appropriate defaults",
            "Ensure all validators are comprehensive",
            "Keep Environment enum, ConfigValidationError, ConfigLoader"
        ],
        risk_level="low"
    ),

    MigrationImpact(
        module_path="src/config_loader.py",
        affected_files=[],
        breaking_changes=["Redirect file - can be removed"],
        recommended_actions=[
            "Delete src/config_loader.py",
            "No impact as it's just a redirect"
        ],
        risk_level="low"
    ),

    MigrationImpact(
        module_path="src/api/config.py",
        affected_files=["app.py"],
        breaking_changes=[
            "Import statements need updating after src/config.py consolidation",
            "Dependency injection via Depends(get_settings) needs working function"
        ],
        recommended_actions=[
            "Update imports to use consolidated config module",
            "Ensure get_settings() function exists and works properly",
            "Test all API endpoints after migration",
            "Verify hot-reload functionality still works"
        ],
        risk_level="medium"
    )
]


# ============================================================================
# Consolidation Strategy
# ============================================================================

CONSOLIDATION_STRATEGY: Dict[str, Any] = {
    "target_module": "bot/config_loader.py",
    "target_class": "AdvancedBotConfig",
    "rationale": [
        "Most feature-complete configuration system",
        "Already supports environment-based configuration",
        "Has comprehensive validation and error handling",
        "Includes retry, timeout, and feature flag settings",
        "Production-ready with proper directory management",
        "Supports YAML configuration files",
        "Has ConfigLoader for flexible loading patterns"
    ],

    "migration_phases": [
        {
            "phase": 1,
            "name": "Fix src/config.py",
            "tasks": [
                "Add missing get_settings() singleton function",
                "Add missing get_config_manager() function",
                "Add missing reload_settings() function",
                "Add missing BotSettings class or remove references",
                "Ensure Settings class has all necessary fields",
                "Update src/api/config.py imports to match reality"
            ],
            "files_affected": [
                "src/config.py",
                "src/api/config.py"
            ],
            "priority": "critical",
            "estimated_effort": "medium"
        },
        {
            "phase": 2,
            "name": "Merge bot/config.py into bot/config_loader.py",
            "tasks": [
                "Verify BotConfig fields are in AdvancedBotConfig",
                "Add any missing fields to AdvancedBotConfig",
                "Update bot/__init__.py to import AdvancedBotConfig",
                "Remove bot/config.py",
                "Update tests"
            ],
            "files_affected": [
                "bot/config.py (remove)",
                "bot/config_loader.py (update)",
                "bot/__init__.py (update imports)"
            ],
            "priority": "high",
            "estimated_effort": "low"
        },
        {
            "phase": 3,
            "name": "Deprecate config.py",
            "tasks": [
                "Update bot.py to use AdvancedBotConfig",
                "Replace class-based access with instance-based",
                "Remove config.py",
                "Update imports"
            ],
            "files_affected": [
                "config.py (remove)",
                "bot.py (update)"
            ],
            "priority": "medium",
            "estimated_effort": "low"
        },
        {
            "phase": 4,
            "name": "Consolidate src/config.py with bot/config_loader.py",
            "tasks": [
                "Decision: Keep both or merge?",
                "Option A: Keep separate (FastAPI uses src/config.py, bot uses bot/config_loader.py)",
                "Option B: Merge Settings into AdvancedBotConfig",
                "If merge: Update all imports in src/llm, src/api, app.py, examples, tests",
                "Ensure dependency injection works across both contexts"
            ],
            "files_affected": [
                "src/config.py (update or remove)",
                "bot/config_loader.py (possibly update)",
                "All files importing from src/config"
            ],
            "priority": "low",
            "estimated_effort": "high"
        },
        {
            "phase": 5,
            "name": "Cleanup and testing",
            "tasks": [
                "Remove src/config_loader.py redirect",
                "Update all documentation",
                "Update all tests to use consolidated config",
                "Verify hot-reload functionality",
                "Verify shared config storage integration",
                "Integration testing"
            ],
            "files_affected": [
                "src/config_loader.py (remove)",
                "All test files",
                "README and docs"
            ],
            "priority": "medium",
            "estimated_effort": "medium"
        }
    ],

    "compatibility_considerations": [
        "FastAPI dependency injection pattern (Depends(get_settings))",
        "Shared config storage mechanism (src/shared_config.py)",
        "IPC communication for hot-reload",
        "Environment variable loading precedence",
        "YAML configuration file support",
        "Pydantic v2 compatibility"
    ],

    "testing_requirements": [
        "Unit tests for consolidated config class",
        "Integration tests for config loading from multiple sources",
        "API endpoint tests for config management",
        "Hot-reload functionality tests",
        "Environment-specific config tests",
        "Validation and error handling tests"
    ]
}


# ============================================================================
# Risk Assessment
# ============================================================================

RISK_ASSESSMENT: Dict[str, Any] = {
    "overall_risk": "medium-high",
    "risk_factors": [
        {
            "factor": "Missing dependency injection functions",
            "impact": "high",
            "mitigation": "Implement get_settings() and related functions before other changes"
        },
        {
            "factor": "Multiple active configuration systems",
            "impact": "medium",
            "mitigation": "Phase migration carefully, test at each phase"
        },
        {
            "factor": "FastAPI integration complexity",
            "impact": "medium",
            "mitigation": "Maintain Depends() pattern, ensure singleton works correctly"
        },
        {
            "factor": "Hot-reload functionality",
            "impact": "medium",
            "mitigation": "Test IPC communication thoroughly after changes"
        },
        {
            "factor": "Test coverage",
            "impact": "low",
            "mitigation": "Update tests incrementally during migration"
        }
    ],

    "critical_paths": [
        "src/api/config.py -> src/config.py (API config management)",
        "main.py -> bot/config_loader.py (Bot startup)",
        "app.py -> src/config.py (FastAPI app startup)",
        "src/llm/factory.py -> src/config.py (LLM client creation)"
    ],

    "rollback_strategy": [
        "Use git branches for each phase",
        "Keep old config files until migration complete",
        "Maintain compatibility shims during transition",
        "Test rollback procedure before starting"
    ]
}


# ============================================================================
# Summary
# ============================================================================

SUMMARY: str = """
Configuration Usage Analysis Summary
====================================

Current State:
--------------
1. **Five configuration modules** exist with overlapping functionality:
   - config.py: Legacy class-based config (minimal usage)
   - src/config.py: Pydantic Settings (INCOMPLETE - missing DI functions)
   - bot/config.py: Pydantic Settings (functional but redundant)
   - bot/config_loader.py: Advanced config system (most complete)
   - src/config_loader.py: Redirect file (can be removed)

2. **Inconsistent patterns**:
   - Some code uses get_settings() dependency injection (FastAPI)
   - Some code uses load_config() factory function (Bot)
   - Some code uses direct class instantiation
   - Some code uses class-based access (legacy Config)

3. **Critical issue**: src/config.py imports reference non-existent functions:
   - get_settings() - MISSING
   - get_config_manager() - MISSING
   - reload_settings() - MISSING
   - BotSettings class - MISSING

Key Findings:
------------
1. **AdvancedBotConfig** in bot/config_loader.py is the most comprehensive:
   - 40+ configuration fields
   - Environment-aware (dev/staging/prod)
   - Retry and timeout configurations
   - Feature flags
   - Production validation
   - YAML support

2. **Settings** in src/config.py is minimal but widely used:
   - 11 basic fields
   - Used throughout FastAPI app and examples
   - Missing dependency injection infrastructure

3. **Dependency graph** shows clear separation:
   - FastAPI components -> src/config.py
   - Bot components -> bot/config_loader.py
   - Legacy bot.py -> config.py

Migration Strategy:
------------------
**Phase 1 (CRITICAL)**: Fix src/config.py
- Implement missing get_settings(), get_config_manager(), reload_settings()
- This unblocks src/api/config.py and prevents runtime errors

**Phase 2**: Merge bot/config.py into bot/config_loader.py
- Low risk, single dependent file (bot/__init__.py)

**Phase 3**: Deprecate config.py
- Low risk, single dependent file (bot.py)

**Phase 4 (OPTIONAL)**: Consolidate src/config.py with bot/config_loader.py
- High effort, affects 10+ files
- May want to keep separate for FastAPI vs Bot separation
- OR extend AdvancedBotConfig to serve both purposes

Recommended Approach:
--------------------
1. **Immediate**: Fix src/config.py missing functions (Phase 1)
2. **Short-term**: Merge redundant configs (Phases 2-3)
3. **Long-term**: Evaluate full consolidation vs separation of concerns
4. **Target**: Single source of truth with clear DI patterns

Impact:
-------
- **High-impact files**: src/api/config.py, app.py, main.py
- **Test coverage**: 10+ test files need updates
- **Breaking changes**: Import paths, function signatures
- **Estimated effort**: 2-3 days for full migration
"""


if __name__ == "__main__":
    """
    This module is for documentation and analysis purposes.
    Import specific constants/dataclasses as needed for migration planning.
    """
    print(SUMMARY)
    print("\n" + "=" * 80)
    print(f"Total config modules analyzed: {len(CONFIG_MODULES)}")
    print(f"Total usage patterns identified: {len(USAGE_PATTERNS)}")
    print(f"Total migration impacts: {len(MIGRATION_IMPACTS)}")
    print(f"Migration phases: {len(CONSOLIDATION_STRATEGY['migration_phases'])}")
    print("=" * 80)
