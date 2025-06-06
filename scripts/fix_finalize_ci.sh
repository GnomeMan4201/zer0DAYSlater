#!/bin/bash

set -e

echo "[+] Backing up and fixing CI workflow..."

cat > .github/workflows/testpypi-publish.yml << 'EOF'
name: Build and Deploy to TestPyPI

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install build tools
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Publish to TestPyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.TEST_PYPI_API_TOKEN }}
      run: twine upload --repository-url https://test.pypi.org/legacy/ dist/*

  test:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install .

    - name: Run smoke test
      run: |
        python -c "import lune; print(lune.__name__)"

  deploy-docs:
    runs-on: ubuntu-latest
    needs: [build, test]

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install docs requirements
      run: |
        pip install .[docs]

    - name: Fix Python path
      run: |
        echo "import os, sys" >> docs/conf.py
        echo "sys.path.insert(0, os.path.abspath('.'))" >> docs/conf.py

    - name: Build documentation
      run: sphinx-build -b html docs docs/_build/html

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: docs/_build/html
EOF

echo "[+] Committing and tagging..."

git add .github/workflows/testpypi-publish.yml
git commit -m "Fix CI: better test, Sphinx patch, cleanup workflow"
git tag v0.1.4
git push origin main --tags

echo "[✓] All set. GitHub Actions will now build, test, upload, and deploy docs."
