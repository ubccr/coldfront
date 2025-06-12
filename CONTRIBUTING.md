# Contributing to ColdFront

Before we start, thank you for considering contributing to ColdFront! 

Every contribution no matter how small is welcome here! Whether you are adding a whole new feature, improving the aesthetics of the webpage, adding some tests cases, or just fixing a typo your contributions are appreciated. 

In this document you will find a set a guidelines for contributing to the ColdFront project, not hard rules. However, sticking to the advice contained in this document will help you to make better contributions, save time, and increase the chances of your contributions getting accepted. 

This project abides by a [Code of Conduct](CODE_OF_CONDUCT.md) that all contributors are required to uphold. Please read this document before interacting with the project.

In addition, you must sign off on all commits using `git commit -s`, acknowledging you agree to the Developer Certificate of Origin.

## Contributor's Agreement

You are under no obligation whatsoever to provide any bug fixes, patches, or upgrades to the features, functionality or performance of the source code ("Enhancements") to anyone; however, if you choose to make your Enhancements available either publicly, or directly to the project, without imposing a separate written license agreement for such Enhancements, then you hereby grant the following license: a non-exclusive, royalty-free perpetual license to install, use, modify, prepare derivative works, incorporate into other computer software, distribute, and sublicense such enhancements or derivative works thereof, in binary and source code form.

## Contribution Workflow

For most contributions, you will start by opening up an issue, discussing changes with maintainers and the community, and then opening a pull request. It is perfectly acceptable to provide a pull request without opening an issue first. However, we recommend you open an issue if the changes you suggest are significant to ensure your changes can be successfully merged.

### Issues

We track requested changes using GitHub issues. These include bugs, feature requests, and general concerns. 

Before making an issue, please look at current and previous issues to make sure that your concern has not already been raised by someone else. It is also advised to read through the [current documentation](https://coldfront.readthedocs.io/en/stable/). If an issue with your concern is already opened you are encouraged to comment further on it. The `Search Issues` feature is great to check to see if someone has already raised your issue before. 

If, after searching pre-existing issues, your concern has not been raised (or you are unsure if a previous issue covers your concern) please open a new issue with any labels you believe are relevant. Please include any relevant images, links, and syntax-highlighted text snippets to help maintainers understand your concerns better. It is also helpful to include any debugging steps you have attempted or ideas on how to fix your issue. 

### Pull Requests

To create a pull request:

1. Fork this repository.
2. Create a branch off the `main` branch.
3. Make commits to your branch. Make sure your additions include [testing](#testing) for any new functionality. Make sure that you run the full test suite on your PR before submitting. If your changes necessitate removing or changing previous tests, please state this explicitly in your PR. Also ensure that your changes pass the [linter and formatter](#formatting-and-linting).
4. Create a pull request back to this main repository.
5. Wait for a maintainer to review your code and request any changes. Don't worry if the maintainer asks for changes! This feedback is perfectly normal and ensures a more maintainable project for everyone. 

## Conventions and Style Guide

#### Spelling and Naming

Please use a spell-checker when modifying the codebase to reduce the prevalence of typos. You should avoid writing names in code that use jargon or abbreviations that are not directly relevant to ColdFront or tools used in its development.

#### Annotations

You are encouraged to use Python's type annotations to improve code readability and maintainability. Whenever possible, use the most recent annotation syntax available for the minimum version of Python supported by ColdFront. 

> The minimum Python version supported can be found in the `pyproject.toml` file.

#### Testing

All new and changed features must include unit tests to verify that they work correctly. Every non-trivial function should have at least as many test cases as its cyclomatic complexity to verify all independent code paths in the function operate correctly.

When using [uv](https://docs.astral.sh/uv/), the full test suite can be run using the command `uv run coldfront test`. 

#### Formatting and Linting

This project is formatted and linted using [ruff](https://docs.astral.sh/ruff/). 

You can use Ruff to check for any linting errors in proposed Python code using `uv run ruff check`. Ruff can also fix many linting errors automatically with `uv run ruff check --fix` when using [uv](https://docs.astral.sh/uv/).

If your code is failing linting checks but you you have a valid reason to leave it unchanged, you can suppress warnings using a `# noqa: <warning-error-code>` comment on the line(s) in question

You can also use Ruff to check formatting using `uv run ruff format --check` and automatically fix formatting errors with `uv run ruff format`.

If your code is failing formatting checks but you have a valid reason to leave it unchanged, you can suppress warnings for a specific block of code by enclosing it with the comments `# fmt: off` and `# fmt: on`. These comments work at the statement level so placing them inside of expressions will not have any effect. 
