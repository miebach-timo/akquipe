AUDIT_TOOLS = [
    {
        "name": "record_finding",
        "description": "Erfasse einen konkreten Audit-Befund mit Schweregrad und Empfehlung.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["accessibility", "seo", "ux_ui", "usability"],
                    "description": "Audit-Kategorie",
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Schweregrad des Befunds",
                },
                "title": {
                    "type": "string",
                    "description": "Kurzer Titel des Befunds (max. 80 Zeichen)",
                },
                "description": {
                    "type": "string",
                    "description": "Detaillierte Beschreibung des Problems mit konkreten Werten",
                },
                "wcag_criterion": {
                    "type": "string",
                    "description": "WCAG-Kriterium z.B. '1.4.3 Contrast (Minimum)' — nur für accessibility",
                },
                "current_value": {
                    "type": "string",
                    "description": "Aktueller Wert/Zustand (z.B. '2.1:1 Kontrastverhältnis')",
                },
                "recommended_value": {
                    "type": "string",
                    "description": "Empfohlener Wert/Zustand (z.B. 'mindestens 4.5:1')",
                },
                "impact": {
                    "type": "string",
                    "description": "Auswirkung auf Nutzer oder Suchmaschinen",
                },
            },
            "required": ["category", "severity", "title", "description"],
        },
    },
    {
        "name": "set_category_score",
        "description": "Setze den Gesamt-Score für eine Audit-Kategorie (0–100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["accessibility", "seo", "ux_ui", "usability"],
                },
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Score 0–100 (100 = perfekt, 0 = komplett unbrauchbar)",
                },
                "rationale": {
                    "type": "string",
                    "description": "Kurze Begründung für den Score",
                },
            },
            "required": ["category", "score", "rationale"],
        },
    },
    {
        "name": "generate_report",
        "description": "Signalisiert, dass alle Befunde erfasst sind — generiert dann den abschließenden Report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": "3–5 Sätze Executive Summary für den Kunden",
                },
                "top_priority": {
                    "type": "string",
                    "description": "Die eine wichtigste Maßnahme, die sofort umgesetzt werden sollte",
                },
            },
            "required": ["executive_summary", "top_priority"],
        },
    },
]
