# NEW: AI INDICATOR CREATOR - Division Variable Registry
# This file contains division-specific variable mappings for AI-powered indicator creation

DIVISION_VARIABLE_REGISTRY = {
    "IT": {
        "division_name": "IT Operations",
        "division_code": "IT",
        "variables": {
            "core": [
                {
                    "name": "complexity_sp",
                    "description": "Total complexity story points from Jira issues",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "jira"
                },
                {
                    "name": "jira_sp",
                    "description": "Total Jira story points completed",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "jira"
                },
                {
                    "name": "gitlab_commits",
                    "description": "Total GitLab commits made",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "gitlab"
                },
                {
                    "name": "gitlab_mr",
                    "description": "Total GitLab merge requests completed",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "gitlab"
                },
                {
                    "name": "code_reviews",
                    "description": "Total code reviews performed",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "gitlab"
                }
            ],
            "advanced": [
                {
                    "name": "code_review_time",
                    "description": "Average time taken for code review completion",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "gitlab",
                    "unit": "hours"
                },
                {
                    "name": "bug_fix_rate",
                    "description": "Percentage of bugs fixed within SLA",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "jira",
                    "unit": "percentage"
                },
                {
                    "name": "test_coverage",
                    "description": "Code test coverage percentage",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "gitlab",
                    "unit": "percentage"
                }
            ],
            "ai_suggested": [
                {
                    "name": "feature_velocity",
                    "description": "Average number of features completed per sprint",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "features_completed / sprints_count",
                    "ai_generated": True
                },
                {
                    "name": "technical_debt_ratio",
                    "description": "Ratio of technical debt items to total issues",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(technical_debt_items / total_issues) * 100",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Hitung performa berdasarkan complexity story points dengan target 300 dan max score 100",
            "Kombinasi Jira SP dan GitLab commits dengan bobot 70% Jira, 30% GitLab",
            "Code quality score berdasarkan test coverage dan bug fix rate"
        ],
        "common_targets": {
            "complexity_sp": 300,
            "jira_sp": 20,
            "gitlab_commits": 50,
            "test_coverage": 80
        }
    },
    
    "TRAVEL_OPS": {
        "division_name": "Travel Operations",
        "division_code": "TRAVEL_OPS",
        "variables": {
            "core": [
                {
                    "name": "tickets_processed",
                    "description": "Total number of tickets successfully processed",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "custom",
                    "unit": "count"
                },
                {
                    "name": "tickets_resolved",
                    "description": "Total number of tickets resolved",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "custom",
                    "unit": "count"
                },
                {
                    "name": "customer_satisfaction",
                    "description": "Average customer satisfaction score (1-5)",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "custom",
                    "unit": "score"
                },
                {
                    "name": "response_time_minutes",
                    "description": "Average response time in minutes",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "custom",
                    "unit": "minutes"
                }
            ],
            "advanced": [
                {
                    "name": "first_contact_resolution",
                    "description": "Percentage of tickets resolved on first contact",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "custom",
                    "unit": "percentage"
                },
                {
                    "name": "customer_retention_rate",
                    "description": "Percentage of customers retained",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "custom",
                    "unit": "percentage"
                }
            ],
            "ai_suggested": [
                {
                    "name": "ticket_efficiency_score",
                    "description": "Combined score of processing speed and quality",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(tickets_processed / target_tickets * 0.6) + (customer_satisfaction / 5 * 0.4) * 100",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Hitung performa berdasarkan jumlah tiket yang diproses dengan target 500 tiket per bulan",
            "Persentase tiket yang diselesaikan tepat waktu dari total tiket",
            "Kombinasi tiket diproses dan kepuasan pelanggan dengan bobot 70/30"
        ],
        "common_targets": {
            "tickets_processed": 500,
            "tickets_resolved": 450,
            "customer_satisfaction": 4.5,
            "response_time_minutes": 30
        }
    },
    
    "IT_OPS": {
        "division_name": "IT Operations",
        "division_code": "IT_OPS",
        "variables": {
            "core": [
                {
                    "name": "uptime_percentage",
                    "description": "Server/system uptime percentage",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "monitoring",
                    "unit": "percentage"
                },
                {
                    "name": "incident_count",
                    "description": "Total number of incidents reported",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "incident_management",
                    "unit": "count"
                },
                {
                    "name": "incident_resolution_rate",
                    "description": "Percentage of incidents resolved",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "incident_management",
                    "unit": "percentage"
                },
                {
                    "name": "sla_compliance",
                    "description": "Percentage of SLA requirements met",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "sla_monitoring",
                    "unit": "percentage"
                }
            ],
            "advanced": [
                {
                    "name": "system_availability",
                    "description": "Overall system availability score",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "monitoring",
                    "unit": "percentage"
                },
                {
                    "name": "mean_time_to_resolution",
                    "description": "Average time to resolve incidents",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "incident_management",
                    "unit": "hours"
                }
            ],
            "ai_suggested": [
                {
                    "name": "reliability_score",
                    "description": "Combined reliability metric based on uptime and incidents",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(uptime_percentage * 0.8) + ((100 - incident_count * 2) * 0.2)",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Kombinasi uptime server dan incident resolution dengan bobot 70% uptime, 30% incident",
            "Persentase SLA compliance untuk bulan ini dengan target 95%",
            "System availability score dengan minimum 99% uptime"
        ],
        "common_targets": {
            "uptime_percentage": 99.9,
            "incident_count": 5,
            "incident_resolution_rate": 95,
            "sla_compliance": 95
        }
    },
    
    "FARE_FILING": {
        "division_name": "Fare Filing",
        "division_code": "FARE_FILING",
        "variables": {
            "core": [
                {
                    "name": "fares_filed",
                    "description": "Total number of fares successfully filed",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "count"
                },
                {
                    "name": "fares_filed_on_time",
                    "description": "Number of fares filed before deadline",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "count"
                },
                {
                    "name": "filing_accuracy",
                    "description": "Percentage of accurately filed fares",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "percentage"
                },
                {
                    "name": "regulatory_compliance",
                    "description": "Percentage of regulatory requirements met",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "compliance_system",
                    "unit": "percentage"
                }
            ],
            "advanced": [
                {
                    "name": "filing_timeliness",
                    "description": "Average time taken to file fares",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "hours"
                },
                {
                    "name": "error_rate",
                    "description": "Percentage of filing errors",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "percentage"
                }
            ],
            "ai_suggested": [
                {
                    "name": "filing_performance_score",
                    "description": "Comprehensive filing performance metric",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(filing_accuracy * 0.4) + (regulatory_compliance * 0.4) + ((fares_filed_on_time / fares_filed) * 100 * 0.2)",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Persentase fare yang berhasil difile tepat waktu dari total fare yang harus difile",
            "Filing accuracy score dengan target 98% akurasi",
            "Regulatory compliance rate untuk fare filing"
        ],
        "common_targets": {
            "fares_filed": 1000,
            "fares_filed_on_time": 950,
            "filing_accuracy": 98,
            "regulatory_compliance": 100
        }
    },
    
    "FARE_LOADING": {
        "division_name": "Fare Loading",
        "division_code": "FARE_LOADING",
        "variables": {
            "core": [
                {
                    "name": "fares_loaded",
                    "description": "Total number of fares successfully loaded",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "count"
                },
                {
                    "name": "loading_speed",
                    "description": "Fares loaded per hour",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "fares/hour"
                },
                {
                    "name": "load_success_rate",
                    "description": "Percentage of successful fare loads",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "percentage"
                },
                {
                    "name": "data_quality_score",
                    "description": "Quality score of loaded fare data",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "data_quality",
                    "unit": "score"
                }
            ],
            "advanced": [
                {
                    "name": "load_efficiency",
                    "description": "Efficiency metric for loading process",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "percentage"
                },
                {
                    "name": "error_recovery_rate",
                    "description": "Percentage of loading errors successfully recovered",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "fare_system",
                    "unit": "percentage"
                }
            ],
            "ai_suggested": [
                {
                    "name": "loading_performance_index",
                    "description": "Comprehensive loading performance metric",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(load_success_rate * 0.5) + (data_quality_score / 5 * 100 * 0.3) + (min(loading_speed / target_loading_speed * 100, 100) * 0.2)",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Hitung kecepatan loading fare dengan target 100 fare per jam dan maksimal score 150",
            "Persentase keberhasilan loading fare dengan target 95%",
            "Kombinasi loading speed dan data quality dengan bobot 60/40"
        ],
        "common_targets": {
            "fares_loaded": 100,
            "loading_speed": 100,
            "load_success_rate": 95,
            "data_quality_score": 4.5
        }
    },
    
    "HR": {
        "division_name": "Human Resources",
        "division_code": "HR",
        "variables": {
            "core": [
                {
                    "name": "attendance_days",
                    "description": "Total days attended",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "attendance",
                    "unit": "days"
                },
                {
                    "name": "target_days",
                    "description": "Target working days (default: 261)",
                    "type": "standard",
                    "default_value": 261,
                    "data_source": "attendance",
                    "unit": "days"
                },
                {
                    "name": "late_percentage",
                    "description": "Percentage of late arrivals",
                    "type": "standard",
                    "default_value": None,
                    "data_source": "attendance",
                    "unit": "percentage"
                }
            ],
            "advanced": [
                {
                    "name": "training_hours",
                    "description": "Total training hours completed",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "training",
                    "unit": "hours"
                },
                {
                    "name": "recruitment_time",
                    "description": "Average time to fill positions",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "recruitment",
                    "unit": "days"
                },
                {
                    "name": "employee_satisfaction",
                    "description": "Employee satisfaction score",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "surveys",
                    "unit": "score"
                }
            ],
            "ai_suggested": [
                {
                    "name": "attendance_performance_score",
                    "description": "Combined attendance and punctuality score",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(attendance_days / target_days * 100) - (late_percentage * 0.5)",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Persentase kehadiran dengan target 261 hari kerja",
            "Kombinasi kehadiran dan pelatihan dengan bobot 70/30",
            "Employee engagement score berdasarkan kehadiran dan satisfaksi"
        ],
        "common_targets": {
            "attendance_days": 261,
            "target_days": 261,
            "late_percentage": 5,
            "training_hours": 40
        }
    },
    
    "SALES": {
        "division_name": "Sales",
        "division_code": "SALES",
        "variables": {
            "core": [
                {
                    "name": "deals_closed",
                    "description": "Total number of deals closed",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "crm",
                    "unit": "count"
                },
                {
                    "name": "revenue_generated",
                    "description": "Total revenue generated",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "crm",
                    "unit": "currency"
                },
                {
                    "name": "client_meetings",
                    "description": "Total client meetings conducted",
                    "type": "division_specific",
                    "default_value": None,
                    "data_source": "crm",
                    "unit": "count"
                }
            ],
            "advanced": [
                {
                    "name": "conversion_rate",
                    "description": "Percentage of leads converted to deals",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "crm",
                    "unit": "percentage"
                },
                {
                    "name": "deal_size_avg",
                    "description": "Average deal size",
                    "type": "advanced",
                    "default_value": None,
                    "data_source": "crm",
                    "unit": "currency"
                }
            ],
            "ai_suggested": [
                {
                    "name": "sales_performance_index",
                    "description": "Comprehensive sales performance metric",
                    "type": "ai_suggested",
                    "default_value": None,
                    "suggested_formula": "(deals_closed / target_deals * 40) + (revenue_generated / target_revenue * 40) + (conversion_rate * 20)",
                    "ai_generated": True
                }
            ]
        },
        "example_prompts": [
            "Persentase pencapaian target penjualan berdasarkan revenue",
            "Kombinasi deals closed dan conversion rate dengan bobot 60/40",
            "Sales velocity berdasarkan deals closed dan client meetings"
        ],
        "common_targets": {
            "deals_closed": 10,
            "revenue_generated": 100000,
            "client_meetings": 20,
            "conversion_rate": 25
        }
    }
}

def _normalize_division_code(division_code: str) -> str:
    """Normalize HRIS division names/codes to registry codes."""
    if not division_code:
        return "IT"
    code = division_code.strip().upper()
    if code in DIVISION_VARIABLE_REGISTRY:
        return code
    aliases = {
        "TECHNOLOGY": "IT",
        "IT & ENGINEERING": "IT",
        "IT OPERATIONS": "IT_OPS",
        "IT OPS": "IT_OPS",
        "OPERATIONS": "IT_OPS",
        "FARE FILING": "FARE_FILING",
        "FARE LOADING": "FARE_LOADING",
        "TRAVEL OPS": "TRAVEL_OPS",
        "TRAVEL OPERATIONS": "TRAVEL_OPS",
        "HUMAN RESOURCES": "HR",
        "SALES & MARKETING": "SALES",
    }
    for alias, registry_key in aliases.items():
        if alias in code:
            return registry_key
    return code

def get_division_variables(division_code: str) -> dict:
    """
    Get variables for a specific division
    
    Args:
        division_code: Division code (e.g., "IT", "TRAVEL_OPS")
    
    Returns:
        Dictionary containing division variables or empty dict if not found
    """
    division_data = DIVISION_VARIABLE_REGISTRY.get(_normalize_division_code(division_code))
    if division_data:
        return division_data["variables"]
    return {"core": [], "advanced": [], "ai_suggested": []}

def get_division_example_prompts(division_code: str) -> list:
    """
    Get example prompts for a specific division
    
    Args:
        division_code: Division code
    
    Returns:
        List of example prompts or empty list if not found
    """
    division_data = DIVISION_VARIABLE_REGISTRY.get(_normalize_division_code(division_code))
    if division_data:
        return division_data.get("example_prompts", [])
    return []

def get_division_common_targets(division_code: str) -> dict:
    """
    Get common target values for a specific division
    
    Args:
        division_code: Division code
    
    Returns:
        Dictionary of common targets or empty dict if not found
    """
    division_data = DIVISION_VARIABLE_REGISTRY.get(_normalize_division_code(division_code))
    if division_data:
        return division_data.get("common_targets", {})
    return {}

def get_all_divisions() -> list:
    """
    Get list of all available divisions
    
    Returns:
        List of division codes and names
    """
    return [
        {
            "code": code,
            "name": data["division_name"]
        }
        for code, data in DIVISION_VARIABLE_REGISTRY.items()
    ]

def get_available_variables_by_type(division_code: str, variable_type: str, user_role: str = "EMPLOYEE") -> list:
    """
    Get available variables filtered by type and user role
    
    Args:
        division_code: Division code
        variable_type: Type of variables ("core", "advanced", "ai_suggested")
        user_role: User role for permission filtering
    
    Returns:
        List of available variables
    """
    division_vars = get_division_variables(division_code)
    
    if variable_type not in division_vars:
        return []
    
    variables = division_vars[variable_type]
    
    # Filter AI-suggested variables for non-admin users
    if variable_type == "ai_suggested" and user_role != "ROLE_ADMIN":
        return []
    
    return variables