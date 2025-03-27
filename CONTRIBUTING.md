# Contributing to pystatelite

First off, thank you for considering contributing to `pystatelite`! Your help is appreciated.

Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open-source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

## Code of Conduct

This project and everyone participating in it is governed by a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior. (Note: You'll need to add a `CODE_OF_CONDUCT.md` file, perhaps based on the Contributor Covenant).

## How Can I Contribute?

### Reporting Bugs

*   **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/your_username/pystatelite/issues). <!-- Placeholder: Update username/repo -->
*   If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/your_username/pystatelite/issues/new). Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements

*   Open a new issue on GitHub under [Issues](https://github.com/your_username/pystatelite/issues). <!-- Placeholder: Update username/repo -->
*   Clearly describe the enhancement and the motivation for it. Explain why this enhancement would be useful.
*   Provide code examples if possible to illustrate the use case.

### Pull Requests

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally (`git clone git@github.com:your_username/pystatelite.git`). <!-- Placeholder: Update username/repo -->
3.  **Create a new branch** for your changes (`git checkout -b feature/my-new-feature` or `bugfix/fix-that-bug`).
4.  **Make your changes**. Ensure you adhere to the existing code style.
5.  **Add tests** for your changes. This is important so we don't break it in a future version unintentionally.
6.  **Run tests** locally (`pytest`) to ensure everything passes.
7.  **Commit your changes**. Use clear and descriptive commit messages. Consider using [Conventional Commits](https://www.conventionalcommits.org/).
8.  **Push your branch** to your fork (`git push origin feature/my-new-feature`).
9.  **Open a Pull Request** on the `pystatelite` repository. <!-- Placeholder: Update username/repo -->
10. Clearly describe the problem and solution. Include the relevant issue number if applicable.

## Development Setup

1.  Clone the repository.
2.  It's recommended to use a virtual environment.
3.  Install the package in editable mode with test dependencies:
    ```bash
    pip install -e .[test] # Or install pytest/pytest-asyncio separately
    ```
4.  Run tests using `pytest`.

## Coding Style

*   Please follow the existing code style.
*   We use `ruff` for linting (see CI configuration). Try to ensure your code passes linting checks.
*   Use type hints where appropriate.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE) that covers the project. 