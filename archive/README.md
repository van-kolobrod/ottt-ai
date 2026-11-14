# Архив ОТТТ

Материалы, которые не определяют текущую работу, но сохранены для истории. Документы архива не редактируются.

## Тексты

- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — исходный контекст проекта от 21 октября 2026 года и дополнения.
- [`ARCHITECTURE_REVIEW.md`](ARCHITECTURE_REVIEW.md) — обзор предшественников: Soar, OpenNARS, Hyperon, BACON и другие.
- [`OPENNARS_CAUSAL_BENCHMARK.md`](OPENNARS_CAUSAL_BENCHMARK.md) — план причинного бенчмарка; не выполнялся.
- [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md) — сводка состояния на 14 ноября 2026 года.
- [`DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md) — журнал работ.

## Код ранних экспериментов

Перенесён 15 ноября 2026 года. Эксперименты были начаты до того, как сложилась целостная система, и ОТТТ не проверяют: это отдельные механизмы на синтетических задачах.

- [`code/experiments/`](code/experiments/) — поиск формул, перенос отношений, событийная память, ASCII-восприятие, внимание, числовой цикл, идентичность во времени.
- [`code/tests/`](code/tests/), [`code/data/`](code/data/) — тесты и JSON-словари.

Описания: [внимание](RESEARCH_ATTENTION.md), [числовой цикл](RESEARCH_CYCLE.md), [идентичность](ENTITY_IDENTITY.md), [подбор критериев идентичности](IDENTITY_LEARNING.md).

Запуск из каталога `archive/code`:

```bash
python -m unittest discover -s tests -v
```
