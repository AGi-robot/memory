from setuptools import find_packages, setup

package_name = "agi_memory"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OppaAI",
    maintainer_email="oppa.ai.org@gmail.com",
    description="Reusable memory APIs and SQLite conversation storage for AGi agents",
    license="GPL-3.0-only",
)
