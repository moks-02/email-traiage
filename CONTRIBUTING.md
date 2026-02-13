# Contributing to Email Triage Assistant

Thank you for your interest in contributing to Email Triage Assistant! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

## Getting Started

### Prerequisites

- Python 3.13 or higher
- Git
- A GitHub account
- Basic understanding of FastAPI and async Python

### Setting Up Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork locally**:
```bash
git clone https://github.com/YOUR-USERNAME/email-traiage.git
cd email-traiage
```

3. **Add upstream remote**:
```bash
git remote add upstream https://github.com/moks-02/email-traiage.git
```

4. **Create virtual environment**:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

5. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available
```

6. **Verify installation**:
```bash
python src/api/main.py
# Server should start on http://localhost:8000
```

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- 🐛 **Bug Reports**: Find and report bugs
- 🆕 **Feature Requests**: Suggest new features
- 📝 **Documentation**: Improve or add documentation
- 💻 **Code**: Fix bugs or implement features
- 🧪 **Tests**: Add or improve test coverage
- 🎨 **UI/UX**: Improve the dashboard design
- 🌐 **Translations**: Add internationalization support

### Good First Issues

Look for issues labeled `good-first-issue` for beginner-friendly tasks:
- Documentation improvements
- Simple bug fixes
- Adding tests for existing code
- Code refactoring

### Priority Areas

Current priority areas where contributions are especially welcome:

1. **Database Integration**: Replace in-memory storage with PostgreSQL/MongoDB
2. **Authentication**: Add user authentication and multi-tenancy
3. **Testing**: Increase test coverage to 90%+
4. **ML Models**: Improve classification with machine learning
5. **Performance**: Optimize processing speed and memory usage

## Development Workflow

### Branch Naming Convention

Use descriptive branch names:
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Adding tests

Examples:
```bash
feature/add-gmail-oauth
bugfix/fix-imap-connection
docs/update-api-reference
```

### Workflow Steps

1. **Sync with upstream**:
```bash
git checkout main
git pull upstream main
```

2. **Create feature branch**:
```bash
git checkout -b feature/your-feature-name
```

3. **Make changes** and commit regularly:
```bash
git add .
git commit -m "feat: add new feature"
```

4. **Keep branch updated**:
```bash
git fetch upstream
git rebase upstream/main
```

5. **Push to your fork**:
```bash
git push origin feature/your-feature-name
```

6. **Create Pull Request** on GitHub

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Organize alphabetically within groups
- **Docstrings**: Google style docstrings

### Code Formatting

Use these tools to maintain consistent formatting:

```bash
# Install formatters
pip install black isort flake8 mypy

# Format code
black src/
isort src/

# Check style
flake8 src/

# Type checking
mypy src/
```

### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import List, Optional, Dict
from src.models import Email

def process_emails(
    emails: List[Email],
    max_count: Optional[int] = None
) -> Dict[str, int]:
    """Process a list of emails.
    
    Args:
        emails: List of Email objects to process
        max_count: Optional maximum number to process
        
    Returns:
        Dictionary with processing statistics
    """
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_priority(email: Email) -> float:
    """Calculate priority score for an email.
    
    Uses a multi-factor algorithm considering sender importance,
    keyword urgency, deadline proximity, thread context, and recency.
    
    Args:
        email: Email object to score
        
    Returns:
        Priority score between 0 and 100
        
    Examples:
        >>> email = Email(subject="URGENT", ...)
        >>> score = calculate_priority(email)
        >>> print(f"{score:.1f}/100")
        92.5/100
    """
    # Implementation
    pass
```

### Naming Conventions

- **Classes**: PascalCase (`EmailClassifier`, `PriorityScorer`)
- **Functions**: snake_case (`calculate_priority`, `classify_email`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_THREAD_SIZE`, `DEFAULT_PORT`)
- **Private**: Prefix with underscore (`_internal_method`)

### Import Organization

```python
# Standard library
import os
import sys
from datetime import datetime
from typing import List, Optional

# Third-party
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local
from src.models import Email, EmailThread
from src.triage import TriageAgent
```

## Testing Guidelines

### Writing Tests

- Place tests in `tests/` directory
- Mirror source structure: `src/triage/classifier.py` → `tests/test_triage_classifier.py`
- Use descriptive test names: `test_urgent_email_classified_correctly`
- Include docstrings explaining what is being tested

### Test Structure

```python
import pytest
from src.models import Email, EmailAddress
from src.triage import TriageAgent

class TestTriageAgent:
    """Test suite for TriageAgent classification."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        self.agent = TriageAgent()
        
    def test_urgent_keyword_classification(self):
        """Test that emails with URGENT keyword are classified as URGENT."""
        # Arrange
        email = Email(
            id="test-1",
            subject="URGENT: Server Down",
            sender=EmailAddress(email="test@example.com"),
            body_text="Production server is down"
        )
        
        # Act
        result = self.agent.classify_email(email)
        
        # Assert
        assert result.category == EmailCategory.URGENT
        assert result.requires_response is True
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_triage_classifier.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### Coverage Requirements

- Aim for 80%+ code coverage
- 100% coverage for critical components (classification, priority scoring)
- Include edge cases and error conditions

## Pull Request Process

### Before Submitting

**Checklist:**
- [ ] Code follows style guidelines (run `black` and `isort`)
- [ ] Type hints added for all functions
- [ ] Docstrings added for public APIs
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] Documentation updated if needed
- [ ] Commit messages follow convention
- [ ] Branch is up-to-date with main

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): brief description

Detailed explanation if needed

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(imap): add support for Yahoo Mail
fix(priority): correct deadline detection for formats
docs(readme): update IMAP setup instructions
test(compression): add tests for edge cases
```

### Pull Request Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Related Issues
Fixes #123
Closes #456

## Testing
Describe how you tested the changes

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
```

### Review Process

1. **Automated checks**: CI/CD runs tests and linting
2. **Code review**: Maintainers review code quality and design
3. **Feedback**: Address reviewer comments
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer will merge after approval

### After Merge

- Delete your feature branch
- Pull latest main
- Update your fork

## Issue Guidelines

### Creating Issues

**Bug Reports:**
```markdown
### Bug Description
Clear description of the bug

### Steps to Reproduce
1. Step one
2. Step two
3. Step three

### Expected Behavior
What should happen

### Actual Behavior
What actually happens

### Environment
- OS: Windows 11 / Ubuntu 22.04 / macOS 13
- Python version: 3.13
- Package versions: (from pip list)

### Screenshots
If applicable
```

**Feature Requests:**
```markdown
### Feature Description
Clear description of proposed feature

### Use Case
Why is this feature needed?

### Proposed Solution
How should it work?

### Alternatives Considered
Other approaches you've thought about

### Additional Context
Any other relevant information
```

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Documentation improvements
- `good-first-issue`: Good for newcomers
- `help-wanted`: Extra attention needed
- `priority-high`: High priority items
- `wontfix`: This will not be worked on

## Questions?

- Check existing [documentation](docs/)
- Search [existing issues](https://github.com/moks-02/email-traiage/issues)
- Join discussions in [GitHub Discussions](https://github.com/moks-02/email-traiage/discussions)
- Email: support@emailtriage.ai

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Acknowledged in project documentation

Thank you for contributing to Email Triage Assistant! 🎉
