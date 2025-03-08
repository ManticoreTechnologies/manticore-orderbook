# Publishing Manticore OrderBook Documentation

We've set up a comprehensive documentation system for the Manticore OrderBook library with multiple publishing options. This document provides instructions for publishing and maintaining the documentation.

## Documentation Structure

The documentation is organized as follows:

- `mkdocs-docs/`: Main documentation directory
  - `mkdocs.yml`: MkDocs configuration
  - `docs/`: Documentation source files
    - `index.md`: Home page
    - `user-guide.md`: User guide
    - `api-reference.md`: API reference
    - `integration.md`: Integration guide
    - `events.md`: Events system documentation
    - `changelog.md`: Version history
  - `site/`: Generated static site (after building)

- `.readthedocs.yml`: Read the Docs configuration
- `docs/requirements.txt`: Python dependencies for Read the Docs

## Publishing Options

### 1. GitHub Pages (Recommended)

GitHub Pages is the easiest way to publish the documentation online.

1. Push your repository to GitHub
2. Run the following command:
   ```bash
   cd mkdocs-docs
   mkdocs gh-deploy
   ```
3. Access the documentation at `https://[username].github.io/manticore-orderbook/`

GitHub Pages automatically serves the content from the `gh-pages` branch, which is created by the `mkdocs gh-deploy` command.

### 2. Read the Docs

Read the Docs provides free documentation hosting with automatic builds.

1. Push your repository to GitHub
2. Create an account at [Read the Docs](https://readthedocs.org/)
3. Import your GitHub repository
4. The documentation will be automatically built and published

The configuration is already set up with:
- `.readthedocs.yml` - Read the Docs configuration
- `docs/requirements.txt` - Python dependencies

### 3. Self-Hosted Web Server

To host on your own web server:

1. Build the documentation:
   ```bash
   cd mkdocs-docs
   mkdocs build
   ```
2. Copy the `site` directory to your web server
3. Configure your web server to serve the files

### 4. PyPI Documentation

The README.md and long_description are displayed on the PyPI project page.

1. Make sure your setup.py has:
   ```python
   long_description=open("README.md").read(),
   long_description_content_type="text/markdown",
   ```

2. Upload to PyPI:
   ```bash
   python3 -m build
   python3 -m twine upload dist/*
   ```

## Maintaining Documentation

To update the documentation:

1. Edit the Markdown files in `mkdocs-docs/docs/`
2. Preview changes locally:
   ```bash
   cd mkdocs-docs
   mkdocs serve
   ```
3. Build the documentation:
   ```bash
   mkdocs build
   ```
4. Publish using one of the methods above

## Important Notes

- The visualizer tool is located at `tests/visual/orderbook_visualizer.py` and can be run with:
  ```bash
  python3 -m tests.visual.orderbook_visualizer
  ```

- The documentation has been configured with the Material theme, which provides a modern, responsive interface

- All documentation pages are written in Markdown, making them easy to update and maintain 