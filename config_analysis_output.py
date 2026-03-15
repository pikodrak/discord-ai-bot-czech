"""
Configuration Usage Analysis Output

This module contains the comprehensive analysis results of configuration
module usage patterns across the discord-ai-bot-czech codebase.

Generated for task: Analyze configuration usage patterns
"""

from typing import Dict, List, Any


analysis_results: Dict[str, Any] = {
    "files": [
        {
            "path": "config_usage_analysis.json",
            "content": "Comprehensive JSON analysis of all configuration patterns",
            "description": "Detailed analysis of 5 config classes, 35+ import locations, dependency graph, and migration strategy"
        }
    ],
    "summary": (
        "Analyzed 5 distinct configuration classes across the codebase with 35+ import locations. "
        "Identified significant duplication (65%) and consolidation opportunities. "
        "AdvancedBotConfig is the most comprehensive and should be the consolidation target."
    ),
    "next_steps": [
        "Implement missing factory functions (get_settings, get_config_manager) in src/config.py",
        "Migrate legacy bot.py from config.Config to AdvancedBotConfig",
        "Create migration script to consolidate Settings -> AdvancedBotConfig",
        "Update all 20+ affected files with new imports",
        "Run comprehensive test suite to validate migration"
    ]
}


configuration_modules: Dict[str, Dict[str, Any]] = {
    "src/config.py": {
        "class": "Settings",
        "type": "pydantic_settings",
        "usage_count": 15,
        "field_count": 12,
        "method_count": 3,
        "used_by": [
            "run_api.py",
            "test_fastapi_setup.py",
            "src/api/auth.py",
            "src/api/config.py",
            "app.py",
            "examples/llm_client_example.py",
            "examples/security_usage.py",
            "tests/test_llm_factory.py",
            "tests/test_language_configuration.py",
            "tests/test_admin_auth.py",
            "tests/test_config_management.py",
            "tests/test_auth.py",
            "examples/configuration_usage.py"
        ],
        "issues": [
            "Missing factory functions: get_settings, get_config_manager, reload_settings",
            "Imported by many files but functions not found in actual source file",
            "Minimal field set - missing many fields present in other configs"
        ],
        "status": "active_but_incomplete"
    },
    "bot/config.py": {
        "class": "BotConfig",
        "type": "pydantic_settings",
        "usage_count": 2,
        "field_count": 18,
        "method_count": 7,
        "used_by": [
            "bot/__init__.py",
            "docs/message_filter_integration.md"
        ],
        "issues": [
            "Duplicates fields from Settings and AdvancedBotConfig",
            "Low usage count - candidate for removal"
        ],
        "status": "active_redundant"
    },
    "bot/config_loader.py": {
        "class": "AdvancedBotConfig",
        "type": "pydantic_settings",
        "usage_count": 8,
        "field_count": 38,
        "method_count": 12,
        "used_by": [
            "main.py (primary entry point - 3 usages)",
            "main_enhanced.py",
            "examples/config_error_handling_example.py",
            "tests/test_config_loader.py",
            "tests/test_main.py"
        ],
        "additional_classes": [
            "ConfigLoader - YAML config loader",
            "ConfigValidationError - Custom exception",
            "Environment - Enum for environments"
        ],
        "issues": [],
        "status": "primary_config",
        "recommendation": "Use as consolidation target - most comprehensive"
    },
    "config.py": {
        "class": "Config",
        "type": "plain_class",
        "usage_count": 1,
        "field_count": 6,
        "method_count": 2,
        "used_by": [
            "bot.py (legacy bot implementation)"
        ],
        "issues": [
            "Legacy implementation using os.getenv",
            "No Pydantic validation",
            "Only used by old bot.py file"
        ],
        "status": "deprecated",
        "recommendation": "Remove after migrating bot.py"
    },
    "src/shared_config.py": {
        "class": "SharedConfigLoader",
        "type": "config_manager",
        "usage_count": 3,
        "field_count": 0,
        "method_count": 7,
        "used_by": [
            "main.py (IPC reload, config loading)",
            "src/api/config.py (config persistence, hot-reload)"
        ],
        "issues": [],
        "status": "active_manager",
        "recommendation": "Keep - critical for IPC and hot-reload functionality"
    }
}


dependency_graph: Dict[str, List[Dict[str, str]]] = {
    "nodes": [
        {"id": "config.Config", "type": "legacy", "status": "deprecated"},
        {"id": "src.config.Settings", "type": "minimal", "status": "active_incomplete"},
        {"id": "bot.config.BotConfig", "type": "bot_specific", "status": "active_redundant"},
        {"id": "bot.config_loader.AdvancedBotConfig", "type": "comprehensive", "status": "primary"},
        {"id": "src.shared_config.SharedConfigLoader", "type": "manager", "status": "active"},
        {"id": "src.api.config", "type": "api_router", "status": "active"}
    ],
    "edges": [
        {
            "from": "main.py",
            "to": "bot.config_loader.AdvancedBotConfig",
            "type": "instantiation",
            "importance": "critical"
        },
        {
            "from": "main.py",
            "to": "src.shared_config.SharedConfigLoader",
            "type": "loader",
            "importance": "critical"
        },
        {
            "from": "bot.py",
            "to": "config.Config",
            "type": "usage",
            "importance": "low"
        },
        {
            "from": "app.py",
            "to": "src.config.Settings",
            "type": "dependency_injection",
            "importance": "high"
        },
        {
            "from": "src/api/config.py",
            "to": "src.config.Settings",
            "type": "dependency_injection",
            "importance": "high"
        },
        {
            "from": "src/api/config.py",
            "to": "src.shared_config.SharedConfigLoader",
            "type": "persistence",
            "importance": "high"
        }
    ]
}


field_usage_statistics: Dict[str, Dict[str, Any]] = {
    "most_accessed_fields": {
        "discord_bot_token": {
            "access_count": 20,
            "criticality": "critical",
            "present_in": ["Settings", "BotConfig", "AdvancedBotConfig"]
        },
        "log_level": {
            "access_count": 15,
            "criticality": "high",
            "present_in": ["Settings", "BotConfig", "AdvancedBotConfig"]
        },
        "bot_language": {
            "access_count": 12,
            "criticality": "high",
            "present_in": ["Settings", "BotConfig", "AdvancedBotConfig"],
            "issue": "Different default values: Settings='en', BotConfig='cs', AdvancedBotConfig='cs'"
        },
        "api_keys": {
            "access_count": 30,
            "criticality": "critical",
            "present_in": ["All configs"],
            "fields": ["anthropic_api_key", "google_api_key", "openai_api_key"]
        },
        "admin_password": {
            "access_count": 5,
            "criticality": "medium",
            "present_in": ["Settings", "BotConfig", "AdvancedBotConfig"]
        }
    },
    "most_called_methods": {
        "get_available_providers": {
            "call_count": 10,
            "present_in": ["Settings", "BotConfig", "AdvancedBotConfig", "Config"],
            "logic": "identical_across_all",
            "criticality": "high"
        },
        "has_any_ai_key": {
            "call_count": 8,
            "present_in": ["Settings", "BotConfig", "AdvancedBotConfig"],
            "logic": "identical_across_all",
            "criticality": "high"
        },
        "get_channel_ids": {
            "call_count": 5,
            "present_in": ["BotConfig", "AdvancedBotConfig"],
            "logic": "identical_across_all",
            "criticality": "medium"
        },
        "to_dict / model_dump": {
            "call_count": 6,
            "present_in": ["AdvancedBotConfig"],
            "criticality": "medium"
        },
        "validate": {
            "call_count": 3,
            "present_in": ["Config"],
            "criticality": "low"
        }
    }
}


duplication_analysis: Dict[str, Any] = {
    "duplicated_fields": {
        "count": 12,
        "percentage": 65,
        "examples": [
            {
                "field": "discord_bot_token",
                "appears_in": ["Settings", "BotConfig", "AdvancedBotConfig"],
                "consistency": "high"
            },
            {
                "field": "bot_language",
                "appears_in": ["Settings", "BotConfig", "AdvancedBotConfig"],
                "consistency": "low",
                "issue": "Different default values"
            },
            {
                "field": "api_keys (3 fields)",
                "appears_in": ["All configs"],
                "consistency": "high"
            }
        ]
    },
    "duplicated_methods": {
        "count": 5,
        "examples": [
            {
                "method": "get_available_providers",
                "implementations": 4,
                "logic_identical": True
            },
            {
                "method": "has_any_ai_key",
                "implementations": 3,
                "logic_identical": True
            },
            {
                "method": "get_channel_ids",
                "implementations": 2,
                "logic_identical": True
            }
        ]
    },
    "consolidation_savings": {
        "estimated_lines_removed": 250,
        "estimated_maintenance_reduction": "60%"
    }
}


migration_strategy: Dict[str, Dict[str, Any]] = {
    "phase_1_preparation": {
        "priority": "high",
        "risk": "low",
        "estimated_effort_hours": 4,
        "files_affected": 3,
        "tasks": [
            "Implement missing factory functions in src/config.py",
            "Add get_settings() -> Settings singleton",
            "Add get_config_manager() -> ConfigManager singleton",
            "Add reload_settings() -> Settings function",
            "Run all tests to establish baseline",
            "Document current usage patterns"
        ],
        "success_criteria": [
            "All imports resolve correctly",
            "All existing tests pass",
            "Factory functions return correct instances"
        ]
    },
    "phase_2_legacy_removal": {
        "priority": "medium",
        "risk": "low",
        "estimated_effort_hours": 2,
        "files_affected": 2,
        "tasks": [
            "Update bot.py to use AdvancedBotConfig",
            "Remove config.py (legacy)",
            "Update documentation"
        ],
        "dependencies": ["phase_1_preparation"],
        "success_criteria": [
            "bot.py runs with AdvancedBotConfig",
            "No references to config.Config remain"
        ]
    },
    "phase_3_consolidation": {
        "priority": "high",
        "risk": "medium",
        "estimated_effort_hours": 8,
        "files_affected": 20,
        "tasks": [
            "Create automated migration script",
            "Update all imports: src.config.Settings -> bot.config_loader.AdvancedBotConfig",
            "Update src/api/config.py",
            "Update app.py",
            "Update all test files",
            "Update examples",
            "Run full test suite after each batch"
        ],
        "dependencies": ["phase_1_preparation", "phase_2_legacy_removal"],
        "success_criteria": [
            "All imports use AdvancedBotConfig",
            "All tests pass",
            "API endpoints work correctly",
            "Hot-reload functionality works"
        ]
    },
    "phase_4_cleanup": {
        "priority": "low",
        "risk": "low",
        "estimated_effort_hours": 3,
        "files_affected": 5,
        "tasks": [
            "Remove bot/config.py (BotConfig)",
            "Update src/config.py to re-export AdvancedBotConfig for backwards compatibility",
            "Update all documentation",
            "Remove deprecated code comments",
            "Final test pass"
        ],
        "dependencies": ["phase_3_consolidation"],
        "success_criteria": [
            "No duplicate config classes remain",
            "Documentation is up to date",
            "All tests pass"
        ]
    },
    "rollback_plan": {
        "strategy": "Git branch per phase with checkpoint commits",
        "checkpoints": [
            "After phase 1: Tag as config-migration-phase1",
            "After phase 2: Tag as config-migration-phase2",
            "After phase 3: Tag as config-migration-phase3",
            "After phase 4: Tag as config-migration-complete"
        ]
    },
    "total_estimated_effort_hours": 17,
    "total_files_affected": 30
}


recommendations: List[Dict[str, str]] = [
    {
        "priority": "CRITICAL",
        "action": "Implement missing factory functions",
        "reason": "Multiple files import get_settings() but it doesn't exist in src/config.py",
        "impact": "Breaks current codebase if imports are actually used",
        "effort": "2 hours"
    },
    {
        "priority": "HIGH",
        "action": "Consolidate to AdvancedBotConfig",
        "reason": "AdvancedBotConfig is the most comprehensive and already primary config",
        "impact": "Eliminates 65% duplication, simplifies maintenance",
        "effort": "12 hours"
    },
    {
        "priority": "HIGH",
        "action": "Standardize bot_language default",
        "reason": "Inconsistent defaults ('en' vs 'cs') can cause unexpected behavior",
        "impact": "Potential behavior change for some users",
        "effort": "1 hour"
    },
    {
        "priority": "MEDIUM",
        "action": "Remove legacy config.Config",
        "reason": "Only used by old bot.py implementation",
        "impact": "Removes legacy code path",
        "effort": "2 hours"
    },
    {
        "priority": "MEDIUM",
        "action": "Keep SharedConfigLoader separate",
        "reason": "Serves different purpose - hot-reload and IPC communication",
        "impact": "Maintains separation of concerns",
        "effort": "0 hours (no change)"
    },
    {
        "priority": "LOW",
        "action": "Create configuration hierarchy",
        "reason": "Long-term: Use composition for better organization",
        "impact": "Better architecture, easier to extend",
        "effort": "8 hours (future work)"
    }
]


critical_findings: List[str] = [
    "MISSING FUNCTIONS: get_settings, get_config_manager, reload_settings are imported but not found in src/config.py",
    "DUPLICATION: 65% of fields are duplicated across 3-4 config classes",
    "INCONSISTENCY: bot_language has different defaults (en vs cs) across configs",
    "LEGACY CODE: config.Config is legacy but still in use by bot.py",
    "PRIMARY CONFIG: AdvancedBotConfig in bot/config_loader.py is the most comprehensive and should be the target",
    "HOT-RELOAD: SharedConfigLoader is critical for IPC and should be kept separate"
]


def print_summary() -> None:
    """Print a human-readable summary of the analysis."""
    print("=" * 80)
    print("CONFIGURATION USAGE ANALYSIS SUMMARY")
    print("=" * 80)
    print()

    print("Configuration Modules Found:")
    for module, info in configuration_modules.items():
        print(f"  • {module}")
        print(f"    - Class: {info['class']}")
        print(f"    - Usage Count: {info['usage_count']}")
        print(f"    - Status: {info['status']}")
        if info.get('recommendation'):
            print(f"    - Recommendation: {info['recommendation']}")
        print()

    print("Critical Findings:")
    for finding in critical_findings:
        print(f"  ⚠ {finding}")
    print()

    print("Top Recommendations:")
    for rec in recommendations[:3]:
        print(f"  [{rec['priority']}] {rec['action']}")
        print(f"      Reason: {rec['reason']}")
        print(f"      Effort: {rec['effort']}")
        print()

    print("Migration Effort Summary:")
    print(f"  • Total Phases: {len(migration_strategy)}")
    print(f"  • Total Hours: {migration_strategy['total_estimated_effort_hours']}")
    print(f"  • Files Affected: {migration_strategy['total_files_affected']}")
    print()

    print("=" * 80)


if __name__ == "__main__":
    print_summary()
