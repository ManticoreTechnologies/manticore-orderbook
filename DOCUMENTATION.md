# Manticore OrderBook Documentation

## Documentation Summary

We have created comprehensive documentation for the Manticore OrderBook library:

1. **Set up MkDocs project** with the Material theme for beautiful, responsive documentation
2. **Created detailed documentation pages**:
   - Home page with project overview
   - User Guide with detailed usage instructions
   - API Reference with class and method documentation
   - Integration Guide for connecting with other systems
   - Events System documentation for the event-driven architecture
   - Changelog with version history
3. **Built the documentation site** which is available in `mkdocs-docs/site/`
4. **Committed all documentation** to the Git repository
5. **Corrected visualizer documentation** to reference the proper module path

## Accessing the Documentation

The documentation is accessible locally at http://127.0.0.1:8000 when running the MkDocs server:

```bash
cd mkdocs-docs
mkdocs serve
```

## Running the Visualizer

The documentation mentions the OrderBook visualizer, which can be run with:

```bash
python3 -m tests.visual.orderbook_visualizer
```

Or using the provided shell script:

```bash
chmod +x manticore_orderbook/examples/start_visualizer.sh
./manticore_orderbook/examples/start_visualizer.sh
```

## Publishing Options

### 1. GitHub Pages Deployment

To deploy the documentation to GitHub Pages, run:

```bash
cd mkdocs-docs
mkdocs gh-deploy
```

This will build and deploy the site to the gh-pages branch of your GitHub repository.

### 2. Read the Docs Integration

To publish on Read the Docs:

1. Create a `.readthedocs.yml` file in your repository root:
   ```yaml
   version: 2
   
   mkdocs:
     configuration: mkdocs-docs/mkdocs.yml
     
   python:
     version: 3.8
     install:
       - requirements: docs/requirements.txt
   ```

2. Create `docs/requirements.txt` with:
   ```
   mkdocs>=1.4.0
   mkdocs-material>=8.5.0
   pymdown-extensions>=9.0
   ```

3. Connect your GitHub repository to Read the Docs at: https://readthedocs.org/dashboard/import/

### 3. PyPI Documentation

The documentation is also available on PyPI when users install or browse the package:

```bash
pip3 install manticore-orderbook
```

The README.md and long_description are displayed on the PyPI project page.

### 4. Self-Hosted Web Server

To host on your own web server:

1. Build the documentation: `cd mkdocs-docs && mkdocs build`
2. Copy the `site` directory to your web server's document root
3. Configure your web server (Apache, Nginx, etc.) to serve the files

## Updating Documentation

To update the documentation in the future:

1. Edit the Markdown files in `mkdocs-docs/docs/`
2. Rebuild the site with `mkdocs build`
3. Deploy using one of the methods above
