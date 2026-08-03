# Project Memory

## 2026-08-03 — Architecture Freeze v2.1

Статус: принято.

Решение:

- Объявить Architecture Freeze v2.1.
- Tool Registry пока остается только контрактом.
- Error Logger и Audit Log не выделяются в отдельные компоненты на MVP; используется единый LoggingService.
- Session Manager и Conversation Manager могут иметь одну MVP-реализацию ConversationStateService при сохранении двух интерфейсов.
- Decision Router остается тонким маршрутизатором готового ProcessingResult.
- Source Selector только выбирает источники и не содержит AI-ranking, RAG, validation или бизнес-решений.

Правило:

Новые архитектурные изменения запрещены до появления реальной причины в коде. Исключение допускается только для устранения критической проблемы или значительного упрощения системы без нарушения существующих контрактов.
