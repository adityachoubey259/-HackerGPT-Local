# Performance Baseline

Generated: `2026-08-11T02:48:59Z`

| Measurement | Min ms | Mean ms | Max ms |
| --- | ---: | ---: | ---: |
| `settings_load_ms` | 1.08 | 1.151 | 1.272 |
| `model_routing_ms` | 2.553 | 2.939 | 3.704 |
| `prompt_architect_ms` | 4.183 | 4.304 | 4.445 |
| `chunking_ms` | 0.687 | 0.953 | 1.481 |
| `local_embedding_ms` | 0.694 | 5.9 | 15.56 |
| `evaluation_ms` | 7.115 | 7.92 | 8.945 |

## Frontend Bundle

- `AgentsPage-CsI02qeB.js`: 6944 bytes
- `Card-kH9B_OoI.js`: 206 bytes
- `CodeBlockHighlighter-kJbFANpb.js`: 100891 bytes
- `CybersecurityPage-J0w0rko4.js`: 9451 bytes
- `icons-BzdA8xyX.js`: 22164 bytes
- `index-B061FJSK.css`: 38252 bytes
- `index-ClldaGLy.js`: 56564 bytes
- `IntelligencePage-vW5Eu01j.js`: 5057 bytes
- `KnowledgePage-CJQ1_ZhF.js`: 8875 bytes
- `LearningStudioPage-Bkek06zp.js`: 23777 bytes
- `markdown-BURH9OKG.js`: 162975 bytes
- `MemoryPage-B0lWFelm.js`: 6628 bytes
- `ModelsPage-BTktRPPN.js`: 9117 bytes
- `PromptLabPage-BjpZvnwF.js`: 5138 bytes
- `react-BWCxGbmR.js`: 163746 bytes
- `ResearchPage-B8eszAC1.js`: 6980 bytes
- `SettingsPage-CUcXoxLk.js`: 7913 bytes
- `SystemStatusPage-CkuOYNjL.js`: 8039 bytes
- `ToolsPage-DR09wnYz.js`: 10407 bytes

## Notes

- Measurements are local code-path timings, not model inference benchmarks.
- No internet, Ollama, Qdrant, Docker, or host-local UI process is required.
