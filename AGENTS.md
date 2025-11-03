# Repository Guidelines

## target
目标：通过数据分析与模型构建，识别影响Zomato配送效率的关键因素，并提出优化策略。

## Project Structure & Module Organization
The repository currently contains `Untitled.ipynb` for exploratory work, `Zomato Dataset.csv` as the raw source, and a brief task checklist in `README.md`. When expanding the project, move notebooks into `notebooks/` (create if absent) and keep raw data in `data/raw/` with derived outputs in `data/processed/`. Group shared utilities in `src/` modules and reference them from notebooks to keep logic reusable.

## Build, Test, and Development Commands
Create an isolated Python environment before modifying notebooks: `python3 -m venv .venv` followed by `source .venv/bin/activate`. Capture libraries in `requirements.txt` and sync with `pip install -r requirements.txt`. Launch the analysis stack with `jupyter lab` for development or `jupyter nbclassic` when a lightweight client is preferred. Use `python -m nbconvert --to notebook --execute notebooks/<file>.ipynb` to confirm notebooks execute start to finish after edits.

## Coding Style & Naming Conventions
Follow PEP 8 conventions: 4-space indentation, `snake_case` for variables and functions, and descriptive notebook section headings. Keep notebook cells focused; factor reusable code into modules and import them. Run `black notebooks/ src/` before committing; `isort` helps maintain deterministic imports. Use meaningful filenames such as `cleaning_zomato_20240518.ipynb` and avoid spaces.

## Testing Guidelines
Prefer extracting critical transformations into Python modules and cover them with `pytest` suites stored under `tests/`. Name test files `test_<feature>.py` and mirror the module path. For contributions that remain notebook-only, rely on the nbconvert execution check and review data diffs to ensure deterministic outputs. Track coverage goals informally at ≥80% for shared utilities.

## Commit & Pull Request Guidelines
Commits should be small, focused, and use the imperative mood, e.g., `refine-cleaning-pipeline`. If multiple logical changes are needed, split them. Pull requests must summarize the analysis goal, list key code or data updates, and attach before/after visuals when plots change. Reference any task list items from `README.md` and note dataset version bumps in the description.

## Data Handling & Security Tips
Version large datasets via external storage whenever possible and check licenses before committing replacements for `Zomato Dataset.csv`. Avoid storing credentials in notebooks; load secrets through environment variables or `.env` files listed in `.gitignore`. When sharing outputs, strip notebook metadata that might leak local paths or tokens using `jupyter nbconvert --ClearMetadataPreprocessor.enabled=True`.
