# Theme Framework Agent Prompts

## 🤖 Agent 1 Prompt - Core Theme Engine

```
You are Agent 1 working on the Theme Framework Core Engine for TORE Matrix Labs V3.

REQUIRED READING (Read these files first):
- /home/insulto/torematrix_labs2/AGENT_1_THEME_FRAMEWORK.md
- /home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md
- /home/insulto/torematrix_labs2/CLAUDE.md

YOUR GITHUB ISSUE: #120
URL: https://github.com/insult0o/torematrix_labs2/issues/120

YOUR MISSION:
Implement the core theme engine foundation with theme loading, management, and basic switching capabilities. Focus on creating a solid architectural foundation that Agents 2, 3, and 4 can build upon.

KEY DELIVERABLES:
- src/torematrix/ui/themes/engine.py (YOUR MAIN FOCUS)
- src/torematrix/ui/themes/base.py
- tests/unit/ui/themes/test_engine.py

INTEGRATION REQUIREMENTS:
Your ThemeEngine class MUST provide these interfaces for other agents:
- load_theme(theme_name: str) -> Theme (for Agent 2)
- get_current_theme() -> Theme (for Agent 2)
- apply_theme(theme: Theme, target: QWidget) (for Agent 3)
- register_theme_provider(provider) (for Agent 2)

DEPENDENCIES AVAILABLE:
- Configuration Management (#5) ✅
- Event Bus System (#1) ✅

SUCCESS CRITERIA:
- ThemeEngine loads themes correctly
- Basic theme switching functional
- >95% test coverage
- Ready for Agent 2 & 3 to build upon

START IMPLEMENTING NOW. Read the required files first, then begin development.
```

## 🤖 Agent 2 Prompt - Color Palettes & Typography

```
You are Agent 2 working on the Theme Framework Color Palettes & Typography for TORE Matrix Labs V3.

REQUIRED READING (Read these files first):
- /home/insulto/torematrix_labs2/AGENT_2_THEME_FRAMEWORK.md
- /home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md
- /home/insulto/torematrix_labs2/CLAUDE.md

YOUR GITHUB ISSUE: #121
URL: https://github.com/insult0o/torematrix_labs2/issues/121

YOUR MISSION:
Implement comprehensive color palette management and typography system with WCAG accessibility compliance. Build upon Agent 1's foundation to create beautiful, accessible color and font systems.

KEY DELIVERABLES:
- src/torematrix/ui/themes/palettes.py (YOUR MAIN FOCUS)
- src/torematrix/ui/themes/typography.py
- resources/themes/palettes/ (built-in color schemes)

DEPENDENCIES:
- WAIT for Agent 1 completion (Day 1) before starting
- Use Agent 1's ThemeEngine foundation
- Configuration system for palette settings

INTEGRATION REQUIREMENTS:
Your systems will be used by Agent 3 for stylesheet generation, so ensure:
- Color palettes are easily accessible
- Typography scales are well-defined
- WCAG compliance tools are available

SUCCESS CRITERIA:
- Dark and light palettes fully functional
- Typography system with proper scaling
- WCAG AA/AAA compliance validated
- Built-in professional color schemes
- >95% test coverage

START IMPLEMENTING AFTER AGENT 1 COMPLETES. Read the required files first.
```

## 🤖 Agent 3 Prompt - StyleSheet Generation & Performance

```
You are Agent 3 working on the Theme Framework StyleSheet Generation & Performance for TORE Matrix Labs V3.

REQUIRED READING (Read these files first):
- /home/insulto/torematrix_labs2/AGENT_3_THEME_FRAMEWORK.md
- /home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md
- /home/insulto/torematrix_labs2/CLAUDE.md

YOUR GITHUB ISSUE: #122
URL: https://github.com/insult0o/torematrix_labs2/issues/122

YOUR MISSION:
Implement Qt StyleSheet generation, hot reload capabilities, and performance optimization for the theme system. Focus on creating fast, efficient theme application with developer-friendly tools.

KEY DELIVERABLES:
- src/torematrix/ui/themes/styles.py (YOUR MAIN FOCUS)
- src/torematrix/ui/themes/hot_reload.py
- src/torematrix/ui/themes/performance.py

DEPENDENCIES:
- WAIT for Agent 1 foundation (Day 1) AND Agent 2 colors/fonts (Day 2)
- Use Agent 1's ThemeEngine and Agent 2's palette/typography systems

INTEGRATION REQUIREMENTS:
Your stylesheet system will be used by Agent 4 for UI integration, so ensure:
- Fast stylesheet generation (< 100ms target)
- Hot reload working for development
- Performance optimization ready

SUCCESS CRITERIA:
- Qt StyleSheet generation working perfectly
- Hot reload functional for development workflow
- Performance benchmarks met
- CSS preprocessing features operational
- >95% test coverage

START IMPLEMENTING AFTER AGENTS 1 & 2 COMPLETE. Read the required files first.
```

## 🤖 Agent 4 Prompt - Integration & Production Features

```
You are Agent 4 working on the Theme Framework Integration & Production Features for TORE Matrix Labs V3.

REQUIRED READING (Read these files first):
- /home/insulto/torematrix_labs2/AGENT_4_THEME_FRAMEWORK.md
- /home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md
- /home/insulto/torematrix_labs2/CLAUDE.md

YOUR GITHUB ISSUE: #123
URL: https://github.com/insult0o/torematrix_labs2/issues/123

YOUR MISSION:
Implement icon theming system, integrate all components from Agents 1-3, and ensure production readiness with accessibility features and custom theme creation tools.

KEY DELIVERABLES:
- src/torematrix/ui/themes/icons.py (YOUR MAIN FOCUS)
- src/torematrix/ui/themes/accessibility.py
- src/torematrix/ui/dialogs/theme_customizer.py
- resources/themes/built_in/ (production themes)
- Complete documentation

DEPENDENCIES:
- WAIT for ALL Agents 1, 2, & 3 to complete (Day 1-3)
- Integrate Agent 1's engine, Agent 2's colors/fonts, Agent 3's stylesheets
- Main Window (#11) for theme application

INTEGRATION REQUIREMENTS:
You must ensure ALL components work together:
- Agent 1's engine + Agent 2's palettes + Agent 3's stylesheets
- Icon theming across all UI components
- Production-ready with enterprise features

SUCCESS CRITERIA:
- All theme components integrated seamlessly
- Icon theming working across all widgets
- Accessibility features (high contrast, color blindness) functional
- Custom theme creation tools operational
- Built-in production themes ready
- Complete documentation delivered

START IMPLEMENTING AFTER AGENTS 1, 2 & 3 COMPLETE. Read the required files first.
```

## 📋 Quick Reference for Each Agent

### Agent 1 Files to Read:
1. `/home/insulto/torematrix_labs2/AGENT_1_THEME_FRAMEWORK.md`
2. `/home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md` 
3. `https://github.com/insult0o/torematrix_labs2/issues/120`

### Agent 2 Files to Read:
1. `/home/insulto/torematrix_labs2/AGENT_2_THEME_FRAMEWORK.md`
2. `/home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md`
3. `https://github.com/insult0o/torematrix_labs2/issues/121`

### Agent 3 Files to Read:
1. `/home/insulto/torematrix_labs2/AGENT_3_THEME_FRAMEWORK.md`
2. `/home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md`
3. `https://github.com/insult0o/torematrix_labs2/issues/122`

### Agent 4 Files to Read:
1. `/home/insulto/torematrix_labs2/AGENT_4_THEME_FRAMEWORK.md`
2. `/home/insulto/torematrix_labs2/THEME_FRAMEWORK_COORDINATION.md`
3. `https://github.com/insult0o/torematrix_labs2/issues/123`

## 🚀 Usage Instructions

Copy the specific agent prompt above and provide the agent with the exact file paths to read. Each agent has everything they need to understand their role, dependencies, and deliverables for creating a beautiful, accessible, and production-ready theme framework.