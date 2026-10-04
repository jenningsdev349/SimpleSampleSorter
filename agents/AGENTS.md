# AGENTS.md

Guidance for AI coding agents (and human contributors) working on this repository.

## Project overview

**Sample Sorter** is a cross-platform desktop app (macOS, Windows, Linux) built with Python and PySide6. It scans a folder of audio one-shots (kicks, snares, hats, etc.), classifies each one with a scikit-learn model, and presents the results in a browser where samples can be auditioned and dragged straight into a DAW such as Ableton Live.

**This is a learning project.** The owner is an experienced Android developer (MVVM background) who is new to Python, PySide6/Qt, and machine learning. When making changes:

- Prefer clear, idiomatic, well-commented code over clever code.
- Briefly explain Qt- or ML-specific concepts in comments or PR notes when introducing them (signals/slots, `Property`, `Pipeline`, cross-validation, etc.).
- Draw parallels to Android concepts where helpful (ViewModel, LiveData, Worker), but do not force Android patterns where Qt has its own idiom.
- Do not add dependencies or abstractions without a stated reason.

## User flow

1. **Splash screen**
2. **Export folder selection**, asked on first launch only. The choice is persisted, and changeable later in a settings screen.
3. **Import screen**: pick a folder or drag and drop one onto the window.
4. **Sorting screen**: scan, extract features, classify. It shows progress and supports cancel.
5. **Browser screen**: a split view. Categories are on the left and a scrollable sample list is on the right. Samples can be auditioned, re-categorized by the user, and dragged out to other applications.

## Architecture

MVVM, adapted to Qt's vocabulary.

| Layer | Responsibility | May import Qt? |
|---|---|---|
| **domain** | Plain dataclasses and enums (`Sample`, `Category`, `SortResult`). | No |
| **services** | Business logic and infrastructure: file scanning, audio analysis, classification, database, settings. | `QtCore` only where unavoidable (e.g. `QSettings`), isolated to one file |
| **ml** | Training-time code: dataset building, feature experiments, model training and evaluation. Not shipped in the app bundle. | No |
| **workers** | `QObject`/`QRunnable` wrappers that run long tasks off the UI thread and report via signals. | `QtCore` only |
| **viewmodels** | `QObject` subclasses exposing state (`Property`), signals, and slots. Includes Qt item models (`QAbstractListModel`). | `QtCore` only |
| **views** | `QWidget`/`QMainWindow` subclasses. Layout, styling, and event wiring only. | Yes |

### Terminology warning

Qt's "Model/View" means something narrower than MVVM's "Model". A `QAbstractListModel` is a data adapter feeding a list view. It belongs next to the ViewModels and must stay a thin wrapper over domain data. MVVM's "Model" here is the `domain` + `services` layers.

### Dependency rules (enforce these)

- `domain`, `services`, and `ml` must be testable with plain `pytest`, with no `QApplication` required.
- Views never call services directly. They talk to ViewModels only.
- ViewModels never import anything from `views` or `QtWidgets`.
- Views observe ViewModels via `signal.connect(slot)`. There is no automatic data binding with widgets, so wire it explicitly and keep the wiring in one place per view.
- Dependency wiring (creating services, ViewModels, and views) happens in `app/bootstrap.py`, not scattered across modules.

### Threading rules

- **Never block the UI thread.** Folder scanning, feature extraction, classification, and database bulk writes run in workers.
- Workers communicate with ViewModels exclusively through signals (progress, per-sample result, finished, error). Never touch widgets from a worker.
- Every long-running worker must support cancellation and report errors via a signal rather than raising silently.
- A single failed or corrupt audio file must not abort the whole sort. Record the failure and continue.

## Project structure

```
simple-sample-sorter/
├── agents/AGENTS.md
├── README.md
├── pyproject.toml              # Dependencies, tool config (ruff, pytest), project metadata
├── .gitignore
│
├── src/                       # Each folder below is a top-level package with an __init__.py
│   ├── simple_sample_sorter/   # App package: entry point, wiring, bundled resources
│   │   ├── __init__.py
│   │   ├── __main__.py         # Entry point: python -m simple_sample_sorter
│   │   ├── app/
│   │   │   ├── bootstrap.py    # Builds QApplication and wires services -> viewmodels -> views
│   │   │   └── navigation.py   # Screen routing for the QStackedWidget
│   │   └── resources/
│   │       ├── icons/
│   │       ├── styles.qss
│   │       └── models/
│   │           └── classifier.joblib        # Trained model shipped with the app
│   │
│   ├── domain/
│   │   ├── sample.py       # Sample dataclass (path, category, confidence, duration, user_override)
│   │   ├── category.py     # Category enum and display names
│   │   └── sort_result.py
│   │
│   ├── services/
│   │   ├── file_scanner.py       # Walks folders, finds audio files
│   │   ├── audio_loader.py       # Loads and validates audio, handles corrupt files
│   │   ├── feature_extractor.py  # Audio -> fixed-length numeric feature vector (librosa)
│   │   ├── classifier.py         # Loads the trained model, exposes predict + confidence
│   │   ├── filename_hints.py     # Keyword-based secondary signal (e.g. "kick", "hat")
│   │   ├── library_repository.py # SQLite persistence for samples and user corrections
│   │   └── settings_service.py   # QSettings wrapper (export folder, window state)
│   │
│   ├── workers/
│   │   ├── sorting_worker.py     # Scan + extract + classify, with progress and cancel
│   │   └── preview_player.py     # Audio audition playback
│   │
│   ├── viewmodels/
│   │   ├── import_viewmodel.py
│   │   ├── sorting_viewmodel.py
│   │   ├── browser_viewmodel.py
│   │   ├── settings_viewmodel.py
│   │   └── models/
│   │       ├── category_list_model.py   # QAbstractListModel for the left pane
│   │       └── sample_list_model.py     # QAbstractListModel for the right pane
│   │
│   └── views/
│       ├── main_window.py
│       ├── splash_view.py
│       ├── import_view.py
│       ├── sorting_view.py
│       ├── browser_view.py
│       ├── settings_view.py
│       └── widgets/
│           ├── drop_zone.py             # Folder drag-and-drop target
│           ├── draggable_sample_list.py # Starts outbound drags with file URLs
│           └── sample_delegate.py       # Custom row rendering (name, duration, waveform)
│
├── ml/                          # Offline training workspace (NOT bundled into the app)
│   ├── README.md                # How to build the dataset and retrain
│   ├── notebooks/               # Exploration: feature analysis, confusion matrices
│   ├── data/                    # Labeled samples. Gitignored; document how to obtain
│   ├── train.py                 # Trains and evaluates models, writes classifier.joblib
│   └── evaluate.py              # Cross-validation, confusion matrix, feature importances
│
└── tests/
    ├── domain/
    ├── services/
    ├── viewmodels/
    └── fixtures/                # Tiny synthetic audio files for tests
```

### Changes from earlier design discussions

- **`src/` layout.** This avoids import-path surprises and makes packaging with PyInstaller cleaner. `simple_sample_sorter` holds the entry point, wiring, and resources; each architecture layer (`domain`, `services`, `workers`, `viewmodels`, `views`) is its own top-level package directly under `src/`, imported as e.g. `from domain.sample import Sample`. Every package folder has an `__init__.py`, and each one must be listed in `pyproject.toml`.
- **`models/` renamed to `domain/`.** This removes the clash between Qt's "model" and MVVM's "model". Qt item models now live under `viewmodels/models/`.
- **`ml/` moved to the repo root.** Training code, notebooks, and datasets are not part of the shipped app. Only the trained artifact (`classifier.joblib`) and the runtime `feature_extractor.py` ship.
- **Single source of truth for features.** Training and runtime must use the same `services/feature_extractor.py`. Do not duplicate feature logic in notebooks or training scripts. Import it. A mismatch between training-time and inference-time features is the most common silent ML bug.
- **Added `app/`** for bootstrap and navigation so `__main__.py` stays tiny.
- **Added `filename_hints.py`** as a cheap secondary signal combined with the audio model.
- **`joblib` instead of `pickle`** for the model artifact (the scikit-learn recommendation).

## Machine learning guidelines

### Approach

Staged, simplest first:

1. **Heuristic baseline** (thresholds on duration, spectral centroid, band-energy ratios). This gives an end-to-end pipeline early and a baseline to beat.
2. **Random Forest** on hand-crafted features (primary model). Inspect `feature_importances_`.
3. **SVM** in a `Pipeline` with `StandardScaler`, compared against the Random Forest.
4. Optional later: gradient boosting, or pretrained audio embeddings (e.g. YAMNet or OpenL3) plus a lightweight classifier.

### Conventions

- Every model is wrapped in a scikit-learn `Pipeline` (preprocessing and classifier together) so the saved artifact is self-contained.
- Evaluate with a held-out test set **and** cross-validation. Always produce a confusion matrix, not just accuracy.
- Split by **source pack**, not purely at random, where possible. Near-duplicate samples from the same pack leaking into both train and test sets inflates accuracy.
- Fix random seeds for reproducibility.
- Features: a fixed-length vector per sample. Candidates are MFCC statistics, spectral centroid, bandwidth, rolloff, band-energy ratios, zero-crossing rate, RMS and decay-envelope measures, and duration. Document each feature and its rationale in `ml/README.md`.
- Normalize loading: consistent sample rate, mono downmix, and a cap on analysis length for very long files.
- The classifier service must return a **confidence score** as well as a label. Low-confidence results should be surfaced to the user (e.g. "Unsorted / Needs review") rather than guessed.
- Include an explicit **Unknown / Other** category.

### Learning loop

User corrections are stored in the SQLite library (`library_repository.py`) and can be exported as labeled data for retraining. Treat corrections as ground truth when rebuilding the training set.

### Categories (initial taxonomy)

Kick, Snare, Clap, Closed Hat, Open Hat, Cymbal/Crash, Tom, Percussion, Bass/808, FX, Vocal, Other. Start with fewer (Kick, Snare, Hat, Clap, Other) and expand once accuracy is acceptable. Taxonomy lives in `domain/category.py` only.

## Product decisions

- **Reference-based by default.** The library stores original file locations in SQLite and does not move the user's files. The "export folder" is where copies go when the user explicitly exports or organizes a sorted set. Be explicit in the UI about whether an action copies, moves, or only indexes files.
- **Never delete or overwrite user audio files.**
- **Manual correction is first-class.** Users can drag a sample to another category or use a context menu, and corrections persist.
- **Drag-out** uses file URLs in the MIME data pointing at real files on disk, which is what DAWs and file managers expect. Test with Ableton Live, Finder, and Explorer.
- **Audition on click**, with stop-on-new-selection behavior.
- **Persisted state** via `QSettings`: export folder, last import folder, window geometry.

## Tooling and conventions

- **Python**: 3.11+.
- **Environment/deps**: use a virtual environment, with dependencies declared in `pyproject.toml`. Separate optional groups for `dev` (pytest, ruff) and `ml` (notebooks, plotting). Keep training-only libraries out of the runtime dependencies.
- **Formatting and linting**: ruff (lint and format). Type hints on all public functions. Run a type checker (mypy or pyright) on `domain/` and `services/` at minimum.
- **Tests**: pytest. `domain`, `services`, and `viewmodels` have unit tests. ViewModel tests may use `pytest-qt` but must not need a visible window. Use small synthetic audio fixtures (generated sine bursts and noise bursts), never copyrighted samples.
- **Naming**: `snake_case` modules and functions, `PascalCase` classes. Suffix ViewModels with `ViewModel`, views with `View`, workers with `Worker`.
- **Signals**: name them by event (`progress_changed`, `sort_finished`, `error_occurred`). Slots are verbs.
- **Resources**: load assets via `importlib.resources` or the Qt resource system, never via paths relative to the working directory, so a packaged build still works.
- **Logging**: use the standard `logging` module. No bare `print` in app code.
- **Packaging**: PyInstaller targets for macOS, Windows, and Linux. Verify file dialogs, drag-and-drop (inbound and outbound), and audio playback on each OS. macOS may require file-access permission handling.

## Suggested build order

1. `ml/` workspace: assemble a small labeled dataset, then write the feature extractor. Run it from a plain script over a folder and print predictions.
2. Heuristic baseline, then Random Forest, then SVM comparison. Record results (confusion matrices, feature importances) in `ml/README.md`.
3. Rough UI skeleton with fake data (navigation, split view) to start learning Qt early.
4. Wire in the real services: `file_scanner`, `feature_extractor`, `classifier`, `library_repository`.
5. Add `SortingWorker` with progress and cancel, then ViewModels and real views.
6. Add audition, outbound drag-and-drop, and manual correction.
7. Cross-platform testing and packaging.

## Rules for agents

- Do not introduce Qt imports into `domain/`, `services/` (beyond the settings wrapper), or `ml/`.
- Do not perform blocking work on the UI thread.
- Do not duplicate feature-extraction logic. Reuse `services/feature_extractor.py`.
- Do not commit audio datasets, trained artifacts other than the shipped `classifier.joblib`, or large binaries.
- Keep changes small and focused, and add or update tests alongside logic changes.
- When a design choice is non-obvious, leave a short comment explaining *why*. This is a learning project and the reasoning matters as much as the result.
- If a request conflicts with the architecture above, flag it rather than silently working around it.