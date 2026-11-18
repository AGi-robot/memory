from setuptools import find_packages, setup

setup(
    name="agi-memory",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    zip_safe=True,
    maintainer="OppaAI",
    maintainer_email="oppa.ai.org@gmail.com",
    description="Reusable memory APIs and SQLite conversation storage for AGi agents",
    license="GPL-3.0-only",
)
