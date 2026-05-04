# Release Guide

Maintainer steps to cut a new TokenSqueeze release.

## 1. Bump versions

Update the version in all three places so they match:

- `pyproject.toml` — `[project] version = "X.Y.Z"`
- `vscode-extension/package.json` — `"version": "X.Y.Z"`
- `browser-extension/manifest.json` — `"version": "X.Y.Z"`

## 2. Commit the bump

```sh
git add pyproject.toml vscode-extension/package.json browser-extension/manifest.json
git commit -m "chore: bump version to X.Y.Z"
git push
```

## 3. Tag and push

```sh
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 4. Wait for GitHub Actions

The `release` workflow runs on the tag push. It will:

- Build and publish the Python package to PyPI
- Package the VS Code extension as a `.vsix`
- Package the browser extension as a `.zip`
- Create a GitHub Release with the VSIX and ZIP attached

Watch the run under the **Actions** tab and confirm it completes successfully.

## 5. Upload to extension marketplaces

Marketplace publishing is manual. Download the artifacts from the GitHub Release page:

- `tokensqueeze-vX.Y.Z.vsix` → upload to the [VS Code Marketplace](https://marketplace.visualstudio.com/manage)
- `tokensqueeze-chrome-vX.Y.Z.zip` → upload to the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
