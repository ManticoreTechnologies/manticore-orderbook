#!/bin/bash
# This script updates all documentation formats when changes are made to the primary MkDocs documentation

# Exit on error
set -e

echo "Updating all documentation formats from mkdocs-docs/docs..."

# Build MkDocs documentation
cd mkdocs-docs
mkdocs build
cd ..

# Update Docusaurus docs
echo "Updating Docusaurus documentation..."
cp -r mkdocs-docs/docs/* docusaurus-docs/docs/

# Update Docsify docs
echo "Updating Docsify documentation..."
cp -r mkdocs-docs/docs/* docsify-docs/

# Update GitHub Wiki docs
echo "Updating GitHub Wiki documentation..."
cp -r mkdocs-docs/docs/* wiki/
# Rename index.md to Home.md for GitHub Wiki
if [ -f wiki/index.md ]; then
  mv wiki/index.md wiki/Home.md
fi

# Convert Markdown files to RST for Sphinx
echo "Updating Sphinx documentation..."
mkdir -p sphinx-docs/source/_static
for file in mkdocs-docs/docs/*.md; do
  basename=$(basename "$file" .md)
  if [ "$basename" = "index" ]; then
    basename="introduction"
  fi
  # Handle special characters
  basename=$(echo "$basename" | tr '-' '_')
  
  # Copy the content but convert to RST format (simplified approach)
  echo "Converting $file to sphinx-docs/source/${basename}.rst"
  echo "$(basename "$file" .md) Documentation" > "sphinx-docs/source/${basename}.rst"
  echo "=================================" >> "sphinx-docs/source/${basename}.rst"
  echo "" >> "sphinx-docs/source/${basename}.rst"
  echo ".. include:: ../../mkdocs-docs/docs/$(basename "$file")" >> "sphinx-docs/source/${basename}.rst"
  echo "   :parser: myst_parser.sphinx_" >> "sphinx-docs/source/${basename}.rst"
done

echo "All documentation formats have been updated!"
echo "Remember to build and deploy your documentation to your preferred platforms." 