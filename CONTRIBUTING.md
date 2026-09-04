# Contributing to Solathon
Thank you for your interest in contributing to Solathon! We welcome contributions from the community to help make this project better.

## Getting Started
Before you start contributing, please take a moment to review the following guidelines.

### Code of Conduct
We expect all contributors to act professionally and respectfully, and we expect our social channels to be a safe and enjoyable environment for all.

### How Can I Contribute?

1. Fork the repository and create your branch from `master`:

    ```bash
    git checkout -b feature/your-feature-branch
    ```

2. Make your changes and ensure that they follow the project coding standards.

3. Write tests for your changes to ensure the functionality is correct.

4. Ensure your code passes linting and tests:

    ```bash
    poetry run pytest
    ```

5. Commit your changes with a clear and concise commit message:

    ```bash
    git commit -m "Add a brief summary of your changes"
    ```

6. Push to your branch:

    ```bash
    git push origin feature/your-feature-branch
    ```

7. Create a pull request to the `master` branch.

### Setting Up the Development Environment

To set up your development environment, follow these steps:

1. Install the Poetry version used by CI (the project uses Poetry 2's
   PEP 621 metadata support):

    ```bash
    pip install poetry==2.4.2
    ```

2. Clone the repository:

    ```bash
    git clone https://github.com/GitBolt/solathon.git
    cd solathon
    ```

3. Install the project, development tools, and optional QR dependencies:

    ```bash
    poetry install --with dev --all-extras
    ```

4. Run the complete local quality gate:

    ```bash
    poetry run ruff format --check .
    poetry run ruff check .
    poetry run pytest
    poetry run pip-audit
    poetry check --lock
    poetry build
    ```
