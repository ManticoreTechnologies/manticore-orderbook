# Manticore OrderBook Documentation

This directory contains the documentation for the Manticore OrderBook project, built using MkDocs with the Material theme.

## Local Development

To work on the documentation locally:

1. Install MkDocs and the Material theme:
   ```bash
   pip3 install mkdocs mkdocs-material
   ```

2. Start the development server:
   ```bash
   mkdocs serve
   ```

3. Open your browser at http://127.0.0.1:8000 to preview the documentation

## Building the Documentation

To build the static site:

```bash
mkdocs build
```

This will create a `site` directory with the built HTML documentation.

## Publishing to GitHub Pages

To deploy the documentation to GitHub Pages:

```bash
mkdocs gh-deploy
```

This command builds the documentation and pushes it to the `gh-pages` branch of your repository.

## Documentation Structure

- `docs/`: Contains all the Markdown files that make up the documentation
  - `index.md`: The home page
  - `user-guide.md`: User guide
  - `api-reference.md`: API reference documentation
  - `integration.md`: Integration guide
  - `events.md`: Event system documentation
  - `changelog.md`: Version history

- `mkdocs.yml`: Configuration file for MkDocs

## Customizing the Documentation

To customize the documentation:

1. Edit the Markdown files in the `docs/` directory
2. Modify the `mkdocs.yml` file to change the site configuration
3. Add new pages by creating new Markdown files and updating the `nav` section in `mkdocs.yml` 