# ABW - Quick Start

ABW is meant to be used without learning its internals. Most of the time, you only need one command.

## Windows Terminal

Run commands from the repository folder:

```powershell
cd d:\Sandbox\skill-Anti-brain-wiki_note
```

Use this for 90% of tasks:

```powershell
.\abw.bat ask "what you want to do"
```

## Start

See what ABW currently has:

```powershell
.\abw.bat ask "dashboard"
```

## Ask

Use natural language:

```powershell
.\abw.bat ask "explain this error"
.\abw.bat ask "write code to read an Excel file"
.\abw.bat ask "summarize the documents"
```

## Ingest A File

Put the file in `raw/`, then run:

```powershell
.\abw.bat ask "ingest raw/<file>"
```

Or use the shorter command:

```powershell
.\abw.bat ingest raw/<file>
```

## Help

If you do not know what to do next:

```powershell
.\abw.bat ask "help"
.\abw.bat ask "what should I do next?"
```

## Menu

If you do not want to type commands:

```powershell
.\abw.bat
```

Then choose a number from the menu.

## Antigravity IDE

If your IDE supports slash commands, you can use:

```text
/abw-ask "what you want to do"
```

Examples:

```text
/abw-ask "dashboard"
/abw-ask "explain this error"
/abw-ask "ingest raw/file.pdf"
```

Do not assume slash commands exist in a normal terminal. In Windows Terminal, use `.\abw.bat ask "..."`.

## Simple Mental Model

```text
ABW = ChatGPT + your local knowledge + fewer guesses
```

You do not need to understand runner logic, validation proofs, binding status, lanes, dispatchers, or internal state to use ABW.

## Common Commands

```powershell
.\abw.bat ask "dashboard"
.\abw.bat ask "help"
.\abw.bat ask "explain this error"
.\abw.bat ingest raw/my_document.pdf
.\abw.bat review
.\abw.bat health
```

## Developer Notes

This section is for maintainers and contributors. Normal users can ignore it.

ABW is a CLI-first execution boundary for AI work. The user-facing command is `.\abw.bat`, which calls `scripts/abw_cli.py`. The CLI then routes normal requests through the canonical ABW entry path.

### Architecture

The high-level flow is:

```text
User / CLI -> abw_cli.py -> abw_entry.py -> abw_runner.py -> abw_output.py
```

The runner handles request routing, execution, acceptance checks, and output shaping. User-facing output should stay clean and must not expose internal fields unless debug output is explicitly requested.

### Proof System

ABW uses internal validation proof metadata to distinguish trusted runner output from untrusted or malformed output. This metadata is part of the internal contract and should not appear in normal help, dashboard, query, or menu output.

### Health And Repair

Health commands are for inspection:

```powershell
.\abw.bat health
```

Repair/update behavior should remain separate from normal user help so that new users see only actionable commands.
