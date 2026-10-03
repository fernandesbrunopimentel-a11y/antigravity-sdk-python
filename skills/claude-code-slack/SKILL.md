---
name: claude-code-slack
description: "Orchestrate Claude Code in Slack: automate coding tasks from Slack threads, manage Code only vs Code + Chat routing modes, trigger local/cloud Claude Code CLI and bridge Slack pull requests."
---
# /claude-code-slack — Claude Code in Slack Orchestration

Integração oficial e autônoma do Claude Code com o workspace Slack (conforme https://code.claude.com/docs/en/slack).

## Modos de Roteamento (Routing Modes):
1. **Code only**: Todas as menções `@Claude` e comandos são roteados para sessões de desenvolvimento e codificação do Claude Code.
2. **Code + Chat**: Analisa inteligentemente a mensagem. Tarefas de código vão para Claude Code (cloud sessions ou CLI local), e conversas/análises gerais recebem resposta de chat assistencial.

## Casos de Uso:
- Investigação e correção de bugs reportados nos canais do Slack.
- Code review e refatoração assistida em threads.
- Execução paralela de tarefas de desenvolvimento com notificação de conclusão.
- Geração de PRs diretamente pelo Slack.

## Como Usar via Terminal / CLI:
- Verificar status: `claude-slack status`
- Alternar modo: `claude-slack mode "Code only"` ou `claude-slack mode "Code + Chat"`
- Disparar tarefa para o Slack: `claude-slack dispatch "<tarefa de desenvolvimento>"`
- Executar Claude Code CLI: `claude-slack exec "<prompt>"`

## Slash Command no Slack:
- `/claude <tarefa de código>`: Executa a tarefa no cluster local/cloud e retorna o código no canal/thread.